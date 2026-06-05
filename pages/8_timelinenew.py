import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
import plotly.express as px
from auth import require_login
from common import init_session
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
    st.write(result.data)

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
        df["Start"] = pd.to_datetime(df["Start"])
        df["Slut"] = pd.to_datetime(df["Slut"])

    return df
# -------------------------
# RESERVATION INFO
# -------------------------
df = load_bookings()
st.write(df.columns.tolist())

# -------------------------
# CREATE BOOKING
# -------------------------
with st.sidebar.form("booking_form"):

    room = st.selectbox(
        "Værelse",
        [f"Værelse {i}" for i in range(1, 8)]
    )

    start_date = st.date_input(
        "Start dato",
        value=datetime.date.today()
    )

    end_date = st.date_input(
        "Slut dato",
        value=datetime.date.today() + datetime.timedelta(days=2)
    )

    name = st.text_input("Gæstnavn")

    submitted = st.form_submit_button("Book nu")

    if submitted:

        if end_date < start_date:

            st.error("Slut dato skal være efter start dato")

        else:

            try:

                supabase.table("bookings").insert({
                    "Værelse": room,
                    "Start": start_date.isoformat(),
                    "Slut": end_date.isoformat(),
                    "Gæst": int(name)
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

    plot_df["Start"] = pd.to_datetime(plot_df["Start"])
    plot_df["Slut"] = pd.to_datetime(plot_df["Slut"])

    fig = px.timeline(
        plot_df,
        x_start="Start",
        x_end="Slut",
        y="Værelse",
        color="Gæst",
        hover_name="Gæst",
        text="Gæst",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    fig.update_yaxes(
        autorange="reversed"
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
            f"{df[df['id'] == x].iloc[0]['Gæst']} - "
            f"{df[df['id'] == x].iloc[0]['Værelse']}"
        )
    )

    booking = df[df["id"] == booking_id].iloc[0]


    room_number = int(
        str(booking["Værelse"]).split()[-1]
    ) - 1

    new_room = st.selectbox(
        "Rediger værelse",
        [f"Værelse {i}" for i in range(1, 8)],
        index=room_number
    )

    new_start = st.date_input(
        "Rediger start",
        value=pd.to_datetime(
            booking["Start"]
        ).date()
    )

    new_end = st.date_input(
        "Rediger slut",
        value=pd.to_datetime(
            booking["Slut"]
        ).date()
    )

    new_guest = st.text_input(
        "Rediger gæst",
        value=str(booking["Gæst"])
    )


    col1, col2 = st.columns(2)

    with col1:

        if st.button("Gem ændringer"):
            supabase.table("bookings").update({
                "Værelse": new_room,
                "Start": new_start.isoformat(),
                "Slut": new_end.isoformat(),
                "Gæst": int(new_guest)
            }).eq("id", booking_id).execute()

            st.success("Ændringer gemt")
            st.rerun()

    with col2:

        if st.button("Slet booking"):
            supabase.table("bookings").delete().eq(
                "id",
                booking_id
            ).execute()

            st.success("Booking slettet")
            st.rerun()

    with st.expander("Se alle bookinger"):

        st.dataframe(
            df,
            use_container_width=True
        )

else:

    st.info(
        "Ingen bookinger at vise endnu."
    )




