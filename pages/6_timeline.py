import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
import plotly.express as px
from auth import require_login
from common import init_session
import re
import os
from dotenv import load_dotenv
from supabase import create_client
# -------------------------
# INIT
# -------------------------

st.set_page_config(page_title="Timeline2", layout="wide")
require_login()

#st.session_state

load_dotenv()

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

try:
    result = supabase.table("bookings").select("*").limit(1).execute()

    st.success("Forbindelse OK")
    #st.write(result.data)

except Exception as e:
    st.error(f"Fejl: {e}")


name = st.session_state.get("reservation_name")

if name:
    booking_number = st.session_state.get("reservation_number")
    name = st.session_state.get("reservation_name", "")
    checkin_date = st.session_state.get("reservation_checkin_date")
    checkout_date = st.session_state.get("reservation_checkout_date")

    st.write("BOOKING FUNDET")

    st.text(
        f"Booking nummer {booking_number} - "
        f"{name} - "
        f"{checkin_date} til {checkout_date}"
    )

else:
    st.text("Ingen bookinger i session")


def to_dt(x):
    return pd.to_datetime(x)

# -------------------------
# LOAD / SAVE
# -------------------------


def load_bookings():
    result = (
        supabase
        .table("bookings")
        .select("*")
        .execute()
    )

    df = pd.DataFrame(result.data)

    if not df.empty:
        df["checkin_date"] = pd.to_datetime(df["checkin_date"])
        df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    return df
# -------------------------
# RESERVATION INFO
# -------------------------
df = load_bookings()
#st.write(df.columns.tolist())

# -------------------------
# CREATE BOOKING
# -------------------------
with st.sidebar.form("booking_form"):

    room = st.selectbox(
        "room_number",
        [f"room_number {i}" for i in range(1, 8)]
    )

    start_date = st.date_input(
        "checkin_date",
        value=datetime.date.today()
    )

    end_date = st.date_input(
        "checkout_date",
        value=datetime.date.today() + datetime.timedelta(days=2)
    )

    name = st.text_input("booking_number")

    submitted = st.form_submit_button("Book nu")

    if submitted:

        if end_date < start_date:

            st.error("Slut dato skal være efter start dato")

        else:

            try:

                supabase.table("bookings").insert({
                    "room_number": room,
                    "checkin_date": start_date.isoformat(),
                    "checkout_date": end_date.isoformat(),
                    "booking_number": int(name)
                }).execute()

                st.success("Booking gemt")

                st.rerun()

            except Exception as e:

                st.error(f"Fejl ved gemning: {e}")

# -------------------------
# TIMELINE
# -------------------------
st.subheader("Belægningsplan")

if not df.empty:

    plot_df = df.copy()

    # Fjern tomme værelser
    plot_df = plot_df[
        plot_df["room_number"].notna()
    ]

    plot_df = plot_df[
        plot_df["room_number"].astype(str).str.strip() != ""
    ]

    # Udtræk værelsesnummer til sortering
    plot_df["room_sort"] = (
        plot_df["room_number"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
    )

    # Fjern rækker uden gyldigt værelsesnummer
    plot_df = plot_df[
        plot_df["room_sort"].notna()
    ]

    plot_df["room_sort"] = plot_df["room_sort"].astype(int)

    # Fjern værelse 0
    plot_df = plot_df[
        plot_df["room_sort"] > 0
    ]

    # Sortér værelserne numerisk
    plot_df = plot_df.sort_values("room_sort")

    plot_df["booking_number"] = plot_df["booking_number"].astype(str)
    plot_df["checkin_date"] = pd.to_datetime(plot_df["checkin_date"])
    plot_df["checkout_date"] = pd.to_datetime(plot_df["checkout_date"])

    st.write(
        df.groupby("booking_number")
        .size()
        .sort_values(ascending=False)
        .head(20)
    )
    st.write(df.dtypes)
    st.write(df.head(5))
    st.write(plot_df.columns.tolist())
    fig = px.timeline(
        plot_df,
        x_start="checkin_date",
        x_end="checkout_date",
        y="room_number",
        color="booking_number",
        hover_name="booking_number",
        text="booking_number",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    # Tving rækkefølgen på værelserne
    room_order = (
        plot_df
        .sort_values("room_sort")
        ["room_number"]
        .drop_duplicates()
        .tolist()
    )

    fig.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=room_order
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Dato",
        yaxis_title="",
        showlegend=False,
        height=400
    )

    fig.update_xaxes(
        rangeslider_visible=True,
        tickformat="%d-%m"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -------------------------
    # EDIT BOOKINGS
    # -------------------------
    st.subheader("Administrer bookinger")

    booking_id = st.selectbox(
        "Vælg booking",
        df["id"],
        format_func=lambda x: (
            f"{df[df['id'] == x].iloc[0]['booking_number']} - "
            f"{df[df['id'] == x].iloc[0]['room_number']}"
        )
    )

    booking = df[df["id"] == booking_id].iloc[0]

    room_number = int(
        str(booking["room_number"]).split()[-1]
    ) - 1

    new_room = st.selectbox(
        "edit room",
        [f"room_number {i}" for i in range(1, 8)],
        index=room_number
    )

    new_start = st.date_input(
        "Rediger checkin_date",
        value=pd.to_datetime(
            booking["checkin_date"]
        ).date()
    )

    new_end = st.date_input(
        "Rediger checkout_date",
        value=pd.to_datetime(
            booking["checkout_date"]
        ).date()
    )

    new_guest = st.text_input(
        "Rediger booking_number",
        value=str(booking["booking_number"])
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button("Gem til lille dtb ", key="save old dtb"):
            supabase.table("bookings").update({
                "room_number": new_room,
                "checkin_date": new_start.isoformat(),
                "checkout_date": new_end.isoformat(),
                "booking_number": int(new_guest)
            }).eq("id", booking_id).execute()

            st.success("Ændringer gemt")
            st.rerun()

    with col2:

        if st.button("Slet booking", key="slet_old"):
            supabase.table("bookings").delete().eq(
                "id",
                booking_id
            ).execute()

            st.success("Booking slettet")
            st.rerun()
    # vis samlet overblik over alle indtastede bookinger
    with st.expander("Se alle bookinger"):

        st.dataframe(
            df,
            use_container_width=True
        )

else:

    st.info(
        "Ingen bookinger at vise endnu."
    )
#####
# try new database
#####

try:
    result = supabase.table("hammerknuden_dtb").select("*").limit(1).execute()

    st.success("Forbindelse OK")
    #st.write(result.data)

except Exception as e:
    st.error(f"Fejl: {e}")


def to_dt(x):
    return pd.to_datetime(x)

# -------------------------
# LOAD / SAVE
# -------------------------

def load_bookings():
    result = (
        supabase
        .table("hammerknuden_dtb")
        .select("*")
        .execute()
    )

    df = pd.DataFrame(result.data)

    if not df.empty:
        df["checkin_date"] = pd.to_datetime(df["checkin_date"])
        df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    return df
# -------------------------
# RESERVATION INFO
# -------------------------
df = load_bookings()
st.write(df.columns.tolist())

# -------------------------
# CREATE BOOKING
# -------------------------
with st.sidebar.form("booking_form_new"):

    room = st.selectbox(
        "room_number",
        [f"room_number {i}" for i in range(1, 8)]
    )

    start_date = st.date_input(
        "checkin_date",
        value=datetime.date.today()
    )

    end_date = st.date_input(
        "checkout_date",
        value=datetime.date.today() + datetime.timedelta(days=2)
    )

    name = st.text_input("booking_number")

    submitted = st.form_submit_button("Book nu")

    if submitted:

        if end_date < start_date:

            st.error("Slut dato skal være efter start dato")

        else:

            try:

                supabase.table("hammerknuden_dtb").insert({
                    "room_number": room,
                    "checkin_date": start_date.isoformat(),
                    "checkout_date": end_date.isoformat(),
                    "booking_number": int(name)
                }).execute()

                st.success("Booking gemt")

                st.rerun()

            except Exception as e:

                st.error(f"Fejl ved gemning: {e}")

# -------------------------
# TIMELINE
# -------------------------
st.subheader("Belægningsplan")

if not df.empty:

    plot_df = df.copy()

    # Fjern tomme værelser
    plot_df = plot_df[
        plot_df["room_number"].notna()
    ]

    plot_df = plot_df[
        plot_df["room_number"].astype(str).str.strip() != ""
    ]

    # Udtræk værelsesnummer til sortering
    plot_df["room_sort"] = (
        plot_df["room_number"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
    )

    # Fjern rækker uden gyldigt værelsesnummer
    plot_df = plot_df[
        plot_df["room_sort"].notna()
    ]

    plot_df["room_sort"] = plot_df["room_sort"].astype(int)

    # Fjern værelse 0
    plot_df = plot_df[
        plot_df["room_sort"] > 0
    ]

    # Sortér værelserne numerisk
    plot_df = plot_df.sort_values("room_sort")

    plot_df["booking_number"] = plot_df["booking_number"].astype(str)
    plot_df["checkin_date"] = pd.to_datetime(plot_df["checkin_date"])
    plot_df["checkout_date"] = pd.to_datetime(plot_df["checkout_date"])

    debug = st.checkbox("Debug timeline")

    if debug:
        st.write("Antal rækker:", len(plot_df))
    st.write(
        df[
            ["id",
             "booking_number",
             "room_number"]
        ].head(20)
    )
    fig = px.timeline(
        plot_df,
        x_start="checkin_date",
        x_end="checkout_date",
        y="room_number",
        color="booking_number",
        hover_name="booking_number",
        text="booking_number",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    # Tving rækkefølgen på værelserne
    room_order = (
        plot_df
        .sort_values("room_sort")
        ["room_number"]
        .drop_duplicates()
        .tolist()
    )

    fig.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=room_order
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Dato",
        yaxis_title="",
        showlegend=False,
        height=400
    )

    fig.update_xaxes(
        rangeslider_visible=True,
        tickformat="%d-%m"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -------------------------
    # EDIT BOOKINGS
    # -------------------------
    st.subheader("Administrer bookinger")

    booking_id = st.selectbox(
        "Vælg booking",
        df["id"],
        format_func=lambda x: (
            f"{df[df['id'] == x].iloc[0]['booking_number']} - "
            f"{df[df['id'] == x].iloc[0]['room_number']}"
        )
    )

    booking = df[df["id"] == booking_id].iloc[0]

    room_text = str(booking["room_number"])

    match = re.search(r"(\d+)", room_text)

    if match:
        room_number = int(match.group(1)) - 1
    else:
        room_number = 0

    room_number = max(0, min(room_number, 6))

    new_room = st.selectbox(
        "Edit room",
        [f"room_number {i}" for i in range(1, 8)],
        index=room_number
    )

    new_start = st.date_input(
        "Rediger checkin_date",
        value=pd.to_datetime(
            booking["checkin_date"]
        ).date()
    )

    new_end = st.date_input(
        "Rediger checkout_date",
        value=pd.to_datetime(
            booking["checkout_date"]
        ).date()
    )

    new_guest = st.text_input(
        "Rediger booking_number",
        value=str(booking["booking_number"])
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button("Gem ændringer",key="new_dtb"):
            supabase.table("hammerknuden_dtb").update({
                "room_number": new_room,
                "checkin_date": new_start.isoformat(),
                "checkout_date": new_end.isoformat(),
                "booking_number": int(new_guest)
            }).eq("id", booking_id).execute()

            st.success("Ændringer gemt")
            st.rerun()

    with col2:

        if st.button("Slet booking", key="new dtb"):
            supabase.table("hammerknuden_dtb").delete().eq(
                "id",
                booking_id
            ).execute()

            st.success("Booking slettet")
            st.rerun()
    # vis samlet overblik over alle indtastede bookinger
    with st.expander("Se alle bookinger"):

        st.dataframe(
            df,
            use_container_width=True
        )

else:

    st.info(
        "Ingen bookinger at vise endnu."
    )






