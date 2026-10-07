"""Drag fixed-date room moves directly on the shared Plotly calendar."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from plotly.offline import get_plotlyjs

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


def accept_move(bookings, moves, request, occupancy=None):
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
    if occupancy is not None:
        fresh = occupancy[occupancy.id.astype(str) == str(row.id)] if "id" in occupancy else occupancy
        if len(fresh) != 1 or is_locked(fresh.iloc[0].get("movable", True)):
            raise ValueError("Bookingen er låst, slettet eller annulleret. Flytningen er annulleret.")
        latest = fresh.iloc[0]
        if (latest.room_number != row.room_number
                or pd.Timestamp(latest.checkin_date) != pd.Timestamp(row.checkin_date)
                or pd.Timestamp(latest.checkout_date) != pd.Timestamp(row.checkout_date)):
            raise ValueError("Bookingen er ændret. Genindlæs kalenderen før næste flytning.")
    # Evaluate the destination against the current draft, including moves that
    # already freed a room. Use all seasons when supplied by the page.
    current = preview_moves(bookings if occupancy is None else occupancy, moves)
    neighbours = current[(current.id.astype(str) != str(row.id))
                         & (pd.to_numeric(current.room_number, errors="coerce") == room)]
    starts = pd.to_datetime(neighbours.checkin_date, errors="coerce")
    ends = pd.to_datetime(neighbours.checkout_date, errors="coerce")
    if starts.isna().any() or ends.isna().any() or (ends <= starts).any():
        raise ValueError("Målværelset har ugyldige bookingdatoer. Flytningen er annulleret.")
    overlaps = neighbours[(starts < pd.Timestamp(row.checkout_date))
                          & (ends > pd.Timestamp(row.checkin_date))]
    if not overlaps.empty:
        raise ValueError(f"Værelse {room} er optaget af booking "
                         f"{overlaps.iloc[0].booking_number}. Bookingen bliver på sin tidligere plads.")
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
    "calendar_room_drag", html='<div class="calendar-plot-wrap"><div class="calendar-plot"></div><div class="calendar-hit-layer"></div><div class="calendar-status" role="status"></div></div>',
    js=get_plotlyjs() + "\n" + Path(__file__).with_name("calendar_drag.js").read_text(encoding="utf-8"),
    isolate_styles=False,
    css="""
    .calendar-plot-wrap {position:relative; width:100%;}
    .calendar-hit-layer {position:absolute; inset:0; pointer-events:none;}
    .calendar-hit-layer [data-booking] {position:absolute; pointer-events:auto;
      touch-action:none; box-sizing:border-box; border:0; border-radius:2px;
      font:12px sans-serif; color:white; overflow:hidden; user-select:none;}
    .calendar-hit-layer [data-booking]:focus-visible {outline:2px solid #222;}
    .calendar-status {font:13px sans-serif; color:#555; min-height:20px;}
    """,
)


def render_drag_calendar(bookings, start, end, key, on_move=None, disabled=False, revision=0,
                         figure=None, view_key=None):
    if figure is None:
        raise ValueError("Den interaktive kalender kræver den fælles kalenderfigur.")
    data = drag_data(bookings, start, end)
    data["revision"] = revision
    data["figure"] = json.loads(figure.to_json())
    data["view_key"] = view_key
    state = st.session_state.get(key)
    viewport = getattr(state, "viewport", None)
    if isinstance(viewport, dict) and viewport.get("view_key") == view_key:
        view_range = viewport.get("range")
        if isinstance(view_range, list) and len(view_range) == 2:
            dates = pd.to_datetime(view_range, errors="coerce")
            if dates.notna().all() and dates[0] < dates[1]:
                data["figure"]["layout"]["xaxis"]["range"] = view_range
    data["figure"]["layout"]["yaxis"]["fixedrange"] = True
    if disabled:
        for item in data["items"]:
            item["locked"] = True
    return _drag_component(data=data, key=key,
                           on_move_change=on_move or (lambda: None),
                           on_viewport_change=lambda: None)
