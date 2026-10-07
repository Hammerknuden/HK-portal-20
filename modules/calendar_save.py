"""Build a fixed-date plan and save all room moves in one database transaction."""
from uuid import uuid4

import pandas as pd

from common import exclude_cancelled_bookings
from modules.calendar_view import ROOMS
from modules.optimizer_preview import booking_today


def load_calendar_rows(client):
    rows, offset = [], 0
    while True:
        batch = (client.table("hk_dtb").select("*").order("id")
                 .range(offset, offset + 999).execute().data or [])
        rows.extend(batch)
        if len(batch) < 1000:
            return pd.DataFrame(rows)
        offset += 1000


def active_rows(rows):
    if rows.empty:
        return rows.copy()
    result = pd.concat([exclude_cancelled_bookings(group)
                        for _, group in rows.groupby("season", dropna=False)])
    result = result.copy()
    for field in ("checkin_date", "checkout_date"):
        result[field] = pd.to_datetime(result[field], errors="coerce")
    return result


def build_move_request(rows, sources, moves, season, today=None):
    if season != 2027:
        raise ValueError("Lagring er kun aktiveret for testbookinger i 2027.")
    today = pd.Timestamp(today or booking_today())
    active = active_rows(rows)
    plan = []
    for identity, destination in moves.items():
        source = sources.get(identity)
        matches = active[active.id.astype(str) == identity] if "id" in active else active
        if source is None or len(matches) != 1:
            raise ValueError("En booking er slettet eller annulleret. Nulstil og prøv igen.")
        current = matches.iloc[0]
        if (current.season != 2027 or pd.isna(current.get("movable"))
                or current.get("movable") != True):
            raise ValueError("En booking er låst eller tilhører en anden sæson.")
        for field in ("room_number", "checkin_date", "checkout_date", "booking_number"):
            left, right = current[field], source[field]
            if field.endswith("date"):
                left, right = pd.Timestamp(left), pd.Timestamp(right)
            if pd.isna(left) or pd.isna(right) or left != right:
                raise ValueError("En booking er ændret siden flytningen. Nulstil og prøv igen.")
        if (type(destination) is not int or destination not in ROOMS
                or int(current.room_number) not in ROOMS
                or current.checkin_date <= today or current.checkout_date <= current.checkin_date):
            raise ValueError("Kun gyldige, fremtidige ophold kan flyttes.")
        if int(current.room_number) == destination:
            continue
        plan.append(dict(id=int(current.id), from_room=int(current.room_number),
                         to_room=destination, checkin_date=current.checkin_date.date().isoformat(),
                         checkout_date=current.checkout_date.date().isoformat()))
    if not plan:
        raise ValueError("Ingen flytninger at gemme.")
    final = active.copy()
    for move in plan:
        final.loc[final.id.astype(str) == str(move["id"]), "room_number"] = move["to_room"]
    for move in plan:
        neighbours = final[(pd.to_numeric(final.room_number, errors="coerce") == move["to_room"])
                           & (final.id.astype(str) != str(move["id"]))]
        if neighbours[["checkin_date", "checkout_date"]].isna().any().any():
            raise ValueError("Målværelset har en booking med ugyldige datoer.")
        overlap = neighbours[(neighbours.checkin_date < pd.Timestamp(move["checkout_date"]))
                             & (neighbours.checkout_date > pd.Timestamp(move["checkin_date"]))]
        if not overlap.empty:
            raise ValueError(f"Værelse {move['to_room']} overlapper booking "
                             f"{overlap.iloc[0].booking_number}. Ingen flytninger er gemt.")
    return dict(p_request_id=str(uuid4()), p_season=2027, p_moves=plan)


def save_move_request(client, request, *, authenticated=False):
    if request.get("p_season") != 2027:
        raise ValueError("Lagring er kun aktiveret for 2027.")
    name = "apply_calendar_moves_authenticated" if authenticated else "apply_calendar_moves"
    result = client.rpc(name, request).execute().data
    if (not isinstance(result, dict) or result.get("status") != "saved"
            or result.get("request_id") != request["p_request_id"]
            or result.get("moved_count") != len(request["p_moves"])):
        raise RuntimeError("Gemningen er ikke bekræftet. Prøv igen med samme gemme-ID.")
    # A separate read confirms actual persisted room assignments and fixed dates.
    rows = load_calendar_rows(client)
    for move in request["p_moves"]:
        matches = rows[rows.id.astype(str) == str(move["id"])] if "id" in rows else rows
        if len(matches) != 1:
            raise RuntimeError("Gemningen kunne ikke genlæses. Prøv samme gemning igen.")
        row = matches.iloc[0]
        if (row.season != 2027 or int(row.room_number) != move["to_room"]
                or any(pd.Timestamp(row[field]).date().isoformat() != move[field]
                       for field in ("checkin_date", "checkout_date"))):
            raise RuntimeError("Genlæsningen stemmer ikke med flytningen. Genkontrollér gemningen.")
    return result
