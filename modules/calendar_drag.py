"""Session-only room moves. Database saving belongs to the next calendar step."""

from pathlib import Path

import pandas as pd
import streamlit as st

from modules.calendar_view import ROOMS
from modules.timeline_colors import booking_color


def is_locked(value):
    return str(value).strip().lower() in {"false", "0", "0.0"}


def preview_moves(bookings, moves):
    result = bookings.copy(deep=True)
    if "id" not in result or result.id.astype(str).duplicated().any():
        return result
    for index, row in result.iterrows():
        room = moves.get(str(row.id))
        if room in ROOMS and not is_locked(row.get("movable", True)):
            result.at[index, "room_number"] = room
    return result


def accept_move(bookings, moves, request):
    """Trust only row identity and destination; never accept dates from the UI."""
    if not isinstance(request, dict) or "id" not in bookings:
        raise ValueError("Flytningen kunne ikke identificeres.")
    room = request.get("room")
    if type(room) is not int or room not in ROOMS:
        raise ValueError("Ukendt værelse.")
    rows = bookings[bookings.id.astype(str) == str(request.get("id"))]
    if len(rows) != 1:
        raise ValueError("Bookingen findes ikke entydigt. Genindlæs kalenderen.")
    row = rows.iloc[0]
    if is_locked(row.get("movable", True)):
        raise ValueError("Bookingen er låst og kan ikke flyttes.")
    updated = dict(moves)
    if room == int(row.room_number):
        updated.pop(str(row.id), None)
    else:
        updated[str(row.id)] = room
    return updated


def drag_data(bookings, start, end):
    items = []
    unique = "id" in bookings and not bookings.id.astype(str).duplicated().any()
    for row in bookings.to_dict("records"):
        room = pd.to_numeric(row.get("room_number"), errors="coerce")
        if pd.isna(room) or room not in ROOMS:
            continue
        items.append(dict(
            id=str(row.get("id", "")), room=int(room),
            start=row["checkin_date"].strftime("%Y-%m-%d"),
            end=row["checkout_date"].strftime("%Y-%m-%d"),
            label=str(row["booking_number"]),
            name=str(row.get("navn") or ""),
            locked=not unique or row.get("id") is None or is_locked(row.get("movable", True)),
            color=booking_color(row["booking_number"], row.get("web"), row.get("movable", True)),
        ))
    return dict(items=items, rooms=ROOMS, start=pd.Timestamp(start).strftime("%Y-%m-%d"),
                end=pd.Timestamp(end).strftime("%Y-%m-%d"))


_drag_component = st.components.v2.component(
    "calendar_room_drag", html='<div id="calendar-drag"></div>',
    js=Path(__file__).with_name("calendar_drag.js").read_text(encoding="utf-8"),
    css="""
    svg {font: 12px sans-serif; background: white; color: #222;}
    .scroll {overflow-x:auto;}
    button {margin:4px;}
    [data-booking] {touch-action:none;}
    """,
)


def render_drag_calendar(bookings, start, end, key):
    return _drag_component(data=drag_data(bookings, start, end), key=key,
                           on_move_change=lambda: None)
