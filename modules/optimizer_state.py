"""Expire cached analysis when its booking snapshot or calendar date changes."""
import hashlib
import json


def booking_signature(bookings, season, today):
    columns = ["id", "booking_number", "season", "room_number", "checkin_date",
               "checkout_date", "movable", "web"]
    values = bookings.reindex(columns=columns).astype("string").fillna("<null>")
    payload = [int(season), today.isoformat(), sorted(values.itertuples(index=False, name=None))]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def invalidate_analysis(state, signature):
    # An unconfirmed save may already have committed. Keep its request ID for retry.
    if state.get("optimizer_preview", {}).get("save_pending"):
        return False
    result = state.get("optimizer_suggestions")
    if result is None and not state.get("optimizer_choice"):
        return False
    if result is not None and signature is not None and result.get("data_signature") == signature:
        return False
    for key in ("optimizer_suggestions", "optimizer_choice", "optimizer_preview"):
        state.pop(key, None)
    return True
