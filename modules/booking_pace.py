"""Season-based pace: legacy totals, frozen history, or current bookings."""
from datetime import date

import pandas as pd

from common import exclude_cancelled_bookings


def fetch_pace_rows(client, table, columns, **filters):
    rows = []
    while True:
        query = client.table(table).select(columns).order("id")
        for column, value in filters.items():
            query = query.eq(column, value)
        page = query.range(len(rows), len(rows) + 999).execute().data or []
        rows.extend(page)
        if len(page) < 1000:
            return rows


def build_booking_pace(legacy, history, live, seasons, today=None):
    """Return cumulative room nights and data-quality messages.

    Week 0 is the balance before January 1. ISO week numbers are bounded
    within the calendar year (January belongs to week 1, late December to 53).
    Open curves stop today; future seasons show their current opening balance.
    """
    today = today or date.today()
    messages, frames = [], []
    old = pd.DataFrame(legacy)
    if not old.empty:
        for col in ("season_year", "week_number", "sold_nights"):
            old[col] = pd.to_numeric(old[col], errors="coerce")
        old = old.dropna(subset=["season_year", "week_number", "sold_nights"])
        old = old[old.season_year.le(2025)].copy()
        if "id" in old:
            old["id"] = pd.to_numeric(old["id"], errors="coerce")
            old = old.sort_values("id", na_position="first")
        frames.append(old.drop_duplicates(["season_year", "week_number"], keep="last"))

    status = {int(row["season"]): bool(row["pace_archived"]) for row in seasons}
    discovered = {
        int(row["season"]) for row in history + live
        if row.get("season") is not None and int(row["season"]) >= 2026
    }
    for year in sorted(discovered | {y for y in status if y >= 2026}):
        archived = status.get(year, False)
        if year not in status:
            messages.append(f"{year}: sæsonstatus mangler i Setup; vises som åben sæson.")
        source = history if archived else live
        rows = pd.DataFrame([r for r in source if int(r["season"]) == year])
        if archived and rows.empty:
            messages.append(f"{year}: sæsonen er afsluttet, men historikken mangler.")
            continue
        values = pd.Series(dtype=float)
        if not rows.empty:
            key = "booking_nr" if archived else "booking_number"
            rows = exclude_cancelled_bookings(rows, booking_column=key)
            dates = pd.to_datetime(rows["booking_date"], errors="coerce", utc=True)
            # Companion room rows can lack the booking date stored on the master.
            if not archived:
                keys = rows[key].astype("string").str.replace(r"\.0+$", "", regex=True)
                dates = dates.fillna(dates.groupby(keys).transform("min"))
            dates = dates.dt.tz_convert("Europe/Copenhagen").dt.tz_localize(None).dt.normalize()
            if archived:
                nights = pd.to_numeric(rows["room_nights"], errors="coerce")
            else:
                start = pd.to_datetime(rows["checkin_date"], errors="coerce")
                end = pd.to_datetime(rows["checkout_date"], errors="coerce")
                nights = (end - start).dt.days
            invalid = dates.isna() | nights.isna() | nights.lt(0)
            if invalid.any():
                messages.append(f"{year}: {int(invalid.sum())} rækker mangler gyldig bookingdato eller værelsesnætter og er udeladt.")
            valid = ~invalid
            if not archived:
                valid &= dates.le(pd.Timestamp(today))
            values = pd.Series(nights[valid].to_numpy(), index=dates[valid])

        start, end = pd.Timestamp(year, 1, 1), pd.Timestamp(year, 12, 31)
        cutoff = end if archived else min(end, pd.Timestamp(today))
        points = [{"season_year": year, "week_number": 0,
                   "sold_nights": values[values.index < start].sum()}]
        if cutoff >= start:
            checkpoints = list(pd.date_range(start, cutoff, freq="W-SUN"))
            if not checkpoints or checkpoints[-1] != cutoff:
                checkpoints.append(cutoff)
            for day in checkpoints:
                iso_year, week, _ = day.isocalendar()
                week = 1 if iso_year < year else 53 if iso_year > year else week
                points.append({"season_year": year, "week_number": week,
                               "sold_nights": values[values.index <= day].sum()})
        frames.append(pd.DataFrame(points).drop_duplicates("week_number", keep="last"))

    if not frames:
        return pd.DataFrame(columns=["season_year", "week_number", "sold_nights"]), messages
    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values(["season_year", "week_number"])
    result["season_year"] = result["season_year"].astype(int).astype(str)
    return result[["season_year", "week_number", "sold_nights"]], messages
