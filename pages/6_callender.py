import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
import plotly.express as px
from auth import require_login
from common import init_session
import os
from supabase import create_client
# -------------------------
# INIT
# -------------------------

st.set_page_config(page_title="Timeline", layout="wide")
require_login()

st.session_state

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
# PATHS
#
# -------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BOOKING_FILE = DATA_DIR / "booking_data.csv"

# -------------------------
# LOAD / SAVE
# -------------------------


def load_bookings():

    if BOOKING_FILE.exists() and BOOKING_FILE.stat().st_size > 0:

        df = pd.read_csv(
            BOOKING_FILE,
            parse_dates=["Start", "Slut"],
            dtype={
                "Værelse": str,
                "Gæst": str
            }
        )

        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        return df

    return pd.DataFrame(
        columns=["Værelse", "Start", "Slut", "Gæst"]
    )


def save_bookings(df):

    try:
        df = df.copy()

        if not df.empty:
            df["Start"] = pd.to_datetime(df["Start"])
            df["Slut"] = pd.to_datetime(df["Slut"])

        # Fjern eksisterende number-kolonne
        if "number" in df.columns:
            df = df.drop(columns=["number"])

        # Lav nye fortløbende numre
        df = df.reset_index(drop=True)
        df.insert(0, "number", range(len(df)))

        df.to_csv(
            BOOKING_FILE,
            index=False,
            encoding="utf-8"
        )

    except Exception as e:
        st.error(f"Fejl ved gemning: {e}")

# -------------------------
# ALWAYS LOAD FRESH DATA
# -------------------------
df = load_bookings()

# -------------------------
# RESERVATION INFO
# -------------------------


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

            new_row = pd.DataFrame([{
                "Værelse": room,
                "Start": to_dt(start_date),
                "Slut": to_dt(end_date),
                "Gæst": str(name)
            }])

            df = pd.concat(
                [df, new_row],
                ignore_index=True
            )

            save_bookings(df)

            st.success("Booking gemt")
            st.rerun()

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

    st.subheader("Administrer bookinger")

    booking_number = st.selectbox(
        "Vælg booking",
        df["number"],
        format_func=lambda x:
        f"{df[df['number'] == x].iloc[0]['Gæst']} - "
        f"{df[df['number'] == x].iloc[0]['Værelse']}"
    )

    booking = df[df["number"] == booking_number].iloc[0]

    # Find DataFrame-rækken
    row_idx = df[df["number"] == booking_number].index[0]

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

            df.loc[row_idx, "Værelse"] = new_room
            df.loc[row_idx, "Start"] = pd.to_datetime(new_start)
            df.loc[row_idx, "Slut"] = pd.to_datetime(new_end)
            df.loc[row_idx, "Gæst"] = new_guest

            save_bookings(df)

            st.success("Ændringer gemt")
            st.rerun()

    with col2:

        if st.button("Slet booking"):
            df = (
                df
                .drop(index=row_idx)
                .reset_index(drop=True)
            )

            save_bookings(df)

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

# -------------------------
# FILE INFO
# -------------------------
if BOOKING_FILE.exists():

    st.caption(
        "Sidst ændret: "
        + str(
            datetime.datetime.fromtimestamp(
                os.path.getmtime(BOOKING_FILE)
            )
        )
    )



