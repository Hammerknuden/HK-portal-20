import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd


BC_COLUMNS = {
    "Bookingnummer": "reference",
    "Gæstens navn": "name",
    "Indtjekning": "checkin",
    "Udtjekning": "checkout",
    "Booket den": "booked",
    "Status": "status",
    "Værelser": "rooms",
    "Personer": "guests",
}

DB_COLUMNS = {
    "booking_number": "reference",
    "navn": "name",
    "checkin_date": "checkin",
    "checkout_date": "checkout",
    "booking_date": "booked",
    "numb_rooms": "rooms",
    "numb_guests": "guests",
}

DISPLAY_COLUMNS = [
    "Kilde",
    "Navn",
    "Indtjekning",
    "Udtjekning",
    "Bookingdato",
    "Værelser",
    "Personer",
    "Reference",
    "Forskel",
]


def _normalize_name(value):
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    words = re.findall(r"[a-z0-9]+", text.casefold())
    return " ".join(sorted(words))


def _canonicalize(frame, column_map, source):
    missing = [column for column in column_map if column not in frame.columns]
    if missing:
        raise ValueError(
            "Filen/databasen mangler følgende kolonner: " + ", ".join(missing)
        )

    result = frame[list(column_map)].rename(columns=column_map).copy()
    result["source"] = source
    result["name"] = result["name"].fillna("").astype(str).str.strip()
    result["name_key"] = result["name"].map(_normalize_name)

    for column in ("checkin", "checkout", "booked"):
        result[column] = pd.to_datetime(result[column], errors="coerce").dt.date

    for column in ("rooms", "guests"):
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")

    result["reference"] = result["reference"].fillna("").astype(str).str.strip()
    return result.reset_index(drop=True)


def prepare_booking_com(frame):
    """Convert a Booking.com export to the common comparison format."""
    active = frame.copy()
    if "Status" in active.columns:
        status = active["Status"].fillna("").astype(str).str.strip().str.casefold()
        active = active[status.isin({"ok", "active", "aktiv"})]
    return _canonicalize(active, BC_COLUMNS, "Booking.com")


def prepare_database(frame):
    """Convert hk_dtb rows and combine all room rows for the same booking."""
    database = _canonicalize(frame, DB_COLUMNS, "hk_dtb")
    if database.empty:
        return database

    grouped_bookings = []
    database = database.copy()
    database["_group_key"] = [
        f"reference:{reference}" if reference else f"row:{index}"
        for index, reference in zip(database.index, database["reference"])
    ]

    for _, room_rows in database.groupby("_group_key", sort=False):
        has_master_data = bool(
            (
                room_rows["booked"].notna()
                | room_rows["rooms"].notna()
                | room_rows["guests"].notna()
            ).any()
        )

        # The master row normally contains booking date, guest count, and name.
        # Sorting puts that row first while still supporting older/manual rows.
        master_candidates = room_rows.assign(
            _master_score=(
                room_rows[["name", "checkin", "checkout", "booked", "guests"]]
                .notna()
                .sum(axis=1)
                + room_rows["name"].ne("").astype(int)
            )
        ).sort_values("_master_score", ascending=False)
        booking = master_candidates.iloc[0].copy()

        for column in ("name", "name_key", "checkin", "checkout", "booked", "guests"):
            values = room_rows[column].dropna()
            if column in ("name", "name_key"):
                values = values[values.ne("")]
            if not values.empty:
                booking[column] = values.iloc[0]

        # Booking.com has one row per booking. In hk_dtb, every assigned room
        # has its own row, so the row count is the comparable room quantity.
        booking["rooms"] = len(room_rows)
        booking["is_master_booking"] = has_master_data
        output_columns = [
            *database.columns.drop("_group_key"),
            "is_master_booking",
        ]
        grouped_bookings.append(booking[output_columns])

    if not grouped_bookings:
        result = database.drop(columns="_group_key").iloc[0:0].copy()
        result["is_master_booking"] = pd.Series(dtype=bool)
        return result

    return pd.DataFrame(grouped_bookings).reset_index(drop=True)


def _unique_pairs(left, right, key_columns):
    left_keys = left.groupby(key_columns, dropna=False).size()
    right_keys = right.groupby(key_columns, dropna=False).size()
    common_keys = set(left_keys[left_keys == 1].index) & set(
        right_keys[right_keys == 1].index
    )

    pairs = []
    used_left = set()
    used_right = set()
    for key in common_keys:
        key = key if isinstance(key, tuple) else (key,)
        left_mask = pd.Series(True, index=left.index)
        right_mask = pd.Series(True, index=right.index)
        for column, value in zip(key_columns, key):
            left_mask &= left[column].eq(value)
            right_mask &= right[column].eq(value)
        left_index = left[left_mask].index[0]
        right_index = right[right_mask].index[0]
        pairs.append((left_index, right_index))
        used_left.add(left_index)
        used_right.add(right_index)
    return pairs, used_left, used_right


def _differences(bc_row, db_row):
    labels = {
        "name_key": "navn",
        "checkin": "indtjekning",
        "checkout": "udtjekning",
        "booked": "bookingdato",
        "rooms": "værelser",
        "guests": "personer",
    }
    differences = []
    for column, label in labels.items():
        left = bc_row[column]
        right = db_row[column]
        if pd.isna(left) and pd.isna(right):
            continue
        if pd.isna(left) or pd.isna(right):
            differences.append(label)
            continue
        if left != right:
            if column == "rooms":
                differences.append(
                    f"værelser (Booking.com: {int(left)}, hk_dtb: {int(right)})"
                )
            else:
                differences.append(label)
    return differences


def _display_row(row, difference="", source=None):
    def date_text(value):
        return value.strftime("%d-%m-%Y") if pd.notna(value) else ""

    def number(value):
        return int(value) if pd.notna(value) else None

    return {
        "Kilde": source or row["source"],
        "Navn": row["name"],
        "Indtjekning": date_text(row["checkin"]),
        "Udtjekning": date_text(row["checkout"]),
        "Bookingdato": date_text(row["booked"]),
        "Værelser": number(row["rooms"]),
        "Personer": number(row["guests"]),
        "Reference": row["reference"],
        "Forskel": difference,
    }


def compare_bookings(booking_com, database):
    """Compare canonical Booking.com and hk_dtb frames without using booking IDs."""
    bc_remaining = booking_com.copy()
    if "is_master_booking" in database.columns:
        db_auxiliary = database[~database["is_master_booking"]].copy()
        db_remaining = database[database["is_master_booking"]].copy()
    else:
        db_auxiliary = database.iloc[0:0].copy()
        db_remaining = database.copy()
    matched_pairs = []

    # The manually entered booking date is the strongest non-ID identity signal.
    for keys in (
        ["name_key", "booked"],
        ["name_key", "checkin", "checkout"],
    ):
        pairs, used_bc, used_db = _unique_pairs(bc_remaining, db_remaining, keys)
        matched_pairs.extend(
            (bc_remaining.loc[bc_index], db_remaining.loc[db_index])
            for bc_index, db_index in pairs
        )
        bc_remaining = bc_remaining.drop(index=list(used_bc))
        db_remaining = db_remaining.drop(index=list(used_db))

    exact = []
    changed = []
    for bc_row, db_row in matched_pairs:
        expected_rooms = int(bc_row["rooms"]) if pd.notna(bc_row["rooms"]) else 1
        registered_rooms = int(db_row["rooms"]) if pd.notna(db_row["rooms"]) else 1
        missing_rooms = max(0, expected_rooms - registered_rooms)

        if missing_rooms and not db_auxiliary.empty:
            same_stay = (
                db_auxiliary["checkin"].eq(bc_row["checkin"])
                & db_auxiliary["checkout"].eq(bc_row["checkout"])
            )
            room_rows = db_auxiliary[same_stay].head(missing_rooms)
            if not room_rows.empty:
                db_row = db_row.copy()
                db_row["rooms"] = registered_rooms + len(room_rows)
                db_auxiliary = db_auxiliary.drop(index=room_rows.index)

        differences = _differences(bc_row, db_row)
        display = _display_row(
            bc_row,
            difference=", ".join(differences),
            source="Booking.com ↔ hk_dtb",
        )
        if differences:
            changed.append(display)
        else:
            exact.append(display)

    possible = []
    for bc_index, bc_row in bc_remaining.iterrows():
        candidates = []
        for db_index, db_row in db_remaining.iterrows():
            name_score = SequenceMatcher(
                None, bc_row["name_key"], db_row["name_key"]
            ).ratio()
            same_booking_day = (
                pd.notna(bc_row["booked"])
                and pd.notna(db_row["booked"])
                and bc_row["booked"] == db_row["booked"]
            )
            same_stay = (
                bc_row["checkin"] == db_row["checkin"]
                and bc_row["checkout"] == db_row["checkout"]
            )
            if name_score >= 0.78 and (same_booking_day or same_stay):
                candidates.append((name_score, db_index, db_row))
        if candidates:
            best_score, db_index, db_row = max(candidates, key=lambda item: item[0])
            possible.append(
                {
                    "Booking.com-navn": bc_row["name"],
                    "hk_dtb-navn": db_row["name"],
                    "Indtjekning BC": _display_row(bc_row)["Indtjekning"],
                    "Indtjekning hk_dtb": _display_row(db_row)["Indtjekning"],
                    "Udtjekning BC": _display_row(bc_row)["Udtjekning"],
                    "Udtjekning hk_dtb": _display_row(db_row)["Udtjekning"],
                    "Navnelighed": f"{best_score:.0%}",
                    "Bemærkning": "Kontrollér manuelt",
                }
            )

    only_bc = [
        _display_row(row, "Mangler i hk_dtb")
        for _, row in bc_remaining.iterrows()
    ]
    only_db = [
        _display_row(row, "Findes ikke i den aktive Booking.com-fil")
        for _, row in db_remaining.iterrows()
    ]

    def frame(rows, columns=DISPLAY_COLUMNS):
        return pd.DataFrame(rows, columns=columns)

    return {
        "exact": frame(exact),
        "changed": frame(changed),
        "only_bc": frame(only_bc),
        "only_db": frame(only_db),
        "possible": pd.DataFrame(possible),
    }


def combined_differences(result):
    frames = []
    for category, key in (
        ("Ændret", "changed"),
        ("Kun Booking.com", "only_bc"),
        ("Kun hk_dtb", "only_db"),
    ):
        frame = result[key].copy()
        if not frame.empty:
            frame.insert(0, "Kategori", category)
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["Kategori", *DISPLAY_COLUMNS])
    return pd.concat(frames, ignore_index=True)
