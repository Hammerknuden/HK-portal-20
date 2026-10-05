"""Validate timeline edits against current occupancy before saving."""
import re
from datetime import date

import pandas as pd

from common import exclude_cancelled_bookings


def validate_timeline_edit(client, booking_id, payload):
    start = date.fromisoformat(payload["checkin_date"])
    end = date.fromisoformat(payload["checkout_date"])
    if end <= start:
        raise ValueError("Afrejse skal være efter ankomst.")
    if re.sub(r"[^a-z0-9]", "", payload.get("web", "").lower()) == "cansl":
        return

    # Fetch all seasons and rooms: a cancellation can belong to another
    # row of the same booking, and stays can cross season boundaries.
    rows = []
    offset = 0
    while True:
        batch = (
            client.table("hk_dtb")
            .select("id,booking_number,room_number,checkin_date,checkout_date,web")
            .order("id").range(offset, offset + 999).execute().data or []
        )
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    # Include the proposed status when applying booking-wide cancellation.
    for row in rows:
        if str(row["id"]) == str(booking_id):
            row.update(web=payload.get("web", ""), booking_number=payload["booking_number"])
    active = exclude_cancelled_bookings(pd.DataFrame(rows))
    for row in active.to_dict("records"):
        if str(row["id"]) == str(booking_id) or pd.isna(row["room_number"]):
            continue
        if int(row["room_number"]) != int(payload["room_number"]):
            continue
        other_start = pd.to_datetime(row["checkin_date"]).date()
        other_end = pd.to_datetime(row["checkout_date"]).date()
        if other_start < end and other_end > start:
            raise ValueError(
                f"Værelse {payload['room_number']} er allerede booket af booking "
                f"{row['booking_number']} fra {other_start:%d-%m-%Y} "
                f"til {other_end:%d-%m-%Y}. Ændringerne er ikke gemt."
            )
