"""Selection, in-memory preview and one atomic save request."""
from copy import deepcopy
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from modules.optimizer_search import prepare_bookings, validate_plan


def booking_today():
    return datetime.now(ZoneInfo("Europe/Copenhagen")).date()


def select_plan(plan, season):
    return {"plan": deepcopy(plan), "season": int(season), "request_id": str(uuid4())}


def build_preview(bookings, choice, today=None):
    """Include unchanged neighbours on affected rooms; never change input."""
    today = today or booking_today()
    rows = prepare_bookings(bookings)
    plan = choice["plan"]
    if not validate_plan(rows, plan, today):
        raise ValueError("Forslaget er ikke længere gyldigt. Kør analysen igen.")
    candidate = rows.loc[rows["id"] == plan["candidate_id"]].iloc[0]
    if candidate["season"] != choice["season"]:
        raise ValueError("Bookingen tilhører ikke længere den valgte sæson.")
    ids = {m["id"] for m in plan["moves"]}
    rooms = {m[k] for m in plan["moves"] for k in ("from_room", "to_room")}
    start = min(pd.Timestamp(m["checkin_date"]) for m in plan["moves"])
    end = max(pd.Timestamp(m["checkout_date"]) for m in plan["moves"])
    before = rows[
        rows["room_number"].isin(rooms)
        & (rows["checkin_date"] < end) & (rows["checkout_date"] > start)
    ].copy()
    after = before.copy(deep=True)
    for move in plan["moves"]:
        after.loc[after["id"] == move["id"], "room_number"] = move["to_room"]
    frames = []
    for label, frame in (("Før", before), ("Efter (forslag)", after)):
        frame = frame.copy()
        frame["Visning"] = label
        frame["Værelse"] = frame["room_number"].map(lambda r: f"Værelse {r}")
        frame["Ændring"] = frame["id"].map(lambda i: "Flyttes" if i in ids else "Uændret")
        frame["Booking"] = frame["booking_number"].astype(str)
        frames.append(frame)
    return {**deepcopy(choice), "timeline": pd.concat(frames, ignore_index=True),
            "preview_date": today.isoformat()}


def save_preview(client, preview, *, rpc_name="apply_optimizer_plan"):
    """Retry the same request ID after uncertain outcomes; never do row updates."""
    plan = preview["plan"]
    result = client.rpc(rpc_name, {
        "p_request_id": preview["request_id"],
        "p_season": preview["season"],
        "p_candidate_id": int(plan["candidate_id"]),
        "p_moves": [{
            "id": int(m["id"]), "from_room": int(m["from_room"]), "to_room": int(m["to_room"]),
            "checkin_date": m["checkin_date"], "checkout_date": m["checkout_date"],
        } for m in plan["moves"]],
    }).execute().data
    if (not isinstance(result, dict) or result.get("request_id") != preview["request_id"]
            or result.get("moved_count") != len(plan["moves"]) or result.get("status") != "saved"):
        raise RuntimeError("Gemningen blev ikke bekræftet. Prøv igen med samme forhåndsvisning.")
    return result
