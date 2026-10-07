"""Calendar display, independent of database access and booking mutations."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from common import exclude_cancelled_bookings
from modules.timeline_colors import booking_color


ROOMS = {1: "Værelse 1", 2: "Værelse 2", 3: "Værelse 3", 4: "Værelse 4",
         5: "Værelse 5", 6: "Privat", 7: "Temporary"}


def prepare_bookings(bookings, season):
    result = exclude_cancelled_bookings(bookings).copy()
    if result.empty:
        return result
    for field in ("checkin_date", "checkout_date"):
        result[field] = pd.to_datetime(result[field], errors="coerce")
    return result[
        (result.checkin_date < pd.Timestamp(season + 1, 1, 1))
        & (result.checkout_date >= pd.Timestamp(season, 1, 1))
        & (result.checkout_date > result.checkin_date)
    ].copy()


def build_calendar(bookings, events, season, zoom_today=False, today=None):
    """Render the existing timeline layout without synthetic booking bars."""
    today = (pd.Timestamp(today) if today is not None
             else pd.Timestamp.now(tz="Europe/Copenhagen").tz_localize(None)).normalize()
    start, end = pd.Timestamp(season, 1, 1), pd.Timestamp(season + 1, 1, 1)
    frame = bookings.copy()
    fig = go.Figure()
    if not frame.empty:
        frame["room_number"] = pd.to_numeric(frame["room_number"], errors="coerce").map(ROOMS)
        frame = frame[frame.room_number.notna()].copy()
    if not frame.empty:
        start = max(start, frame.checkin_date.min())
        end = min(end, frame.checkout_date.max())
        if end <= start:
            end = start + pd.Timedelta(days=1)
        for field in ("web", "navn", "morgenmad", "movable"):
            if field not in frame:
                frame[field] = None
        frame["booking_number"] = frame.booking_number.astype(str)
        frame["calendar_id"] = frame["id"].astype(str) if "id" in frame else ""
        frame["booking_color"] = frame.apply(
            lambda row: booking_color(row.booking_number, row.web, row.movable), axis=1)
        fig = px.timeline(
            frame, x_start="checkin_date", x_end="checkout_date", y="room_number",
            color="booking_color", hover_name="booking_number", text="booking_number",
            custom_data=["calendar_id"],
            hover_data={"booking_color": False, "movable": True, "navn": True,
                        "morgenmad": True, "room_number": True, "web": True,
                        "checkin_date": "|%d-%m-%Y", "checkout_date": "|%d-%m-%Y"},
            color_discrete_map={color: color for color in frame.booking_color.unique()},
        )
    view_start, view_end = ((today - pd.Timedelta(days=7), today + pd.Timedelta(days=21))
                            if zoom_today else (start, end))
    for monday in pd.date_range(min(start, view_start), max(end, view_end), freq="W-MON"):
        fig.add_shape(type="line", x0=monday, x1=monday, y0=0, y1=1, yref="paper",
                      line=dict(color="gray", width=1, dash="dot"))
        fig.add_annotation(x=monday, y=0, yref="paper", text=str(monday.isocalendar().week),
                           showarrow=False, yshift=-18, font=dict(size=10, color="gray"))
    if view_start <= today <= view_end:
        fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper",
                      line=dict(color="red", width=1))
    for event in events.to_dict("records"):
        event_start = pd.to_datetime(event.get("start_date"), errors="coerce")
        event_end = pd.to_datetime(event.get("end_date"), errors="coerce")
        if pd.isna(event_start) or pd.isna(event_end) or event_end < event_start:
            continue
        opacity = event.get("opacity")
        fig.add_shape(type="rect", x0=event_start, x1=event_end, y0=0, y1=1, yref="paper",
                      fillcolor=event.get("color") or "lightgray",
                      opacity=float(opacity) if pd.notna(opacity) else 0.10, line_width=0)
        fig.add_annotation(x=event_start, y=-0.08, xref="x", yref="paper",
                           text=event.get("event", ""), showarrow=False, xanchor="left",
                           bgcolor="white", bordercolor="lightgray", borderwidth=1,
                           font=dict(size=8))
    # Explicit ticks keep empty rooms visible without dummy bookings or hover labels.
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=list(ROOMS.values()),
                     tickmode="array", tickvals=list(ROOMS.values()),
                     range=[len(ROOMS) - 0.5, -0.5], title="")
    fig.update_xaxes(type="date", rangeslider_visible=True, tickformat="%d-%m",
                     showgrid=True, gridcolor="lightgray", gridwidth=1, dtick="D7",
                     range=[view_start, view_end], title="Dato")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", showlegend=False, height=400)
    return fig
