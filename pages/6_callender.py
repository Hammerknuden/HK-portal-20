import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import plotly.express as px
from auth import require_login
from config.data_email import add_data
# INITIALISER SESSION STATE

st.set_page_config(page_title="Timeline", layout="wide")
require_login()

booking_number = st.session_state.get("reservation_number")

if booking_number:

    st.write("BOOKING FUNDET")

    name = st.session_state.get("reservation_name", "")
    checkin_date = st.session_state.get("reservation_checkin_date", "")
    checkout_date = st.session_state.get("reservation_checkout_date", "")

    st.text(
        f"Booking nummer {booking_number} - "
        f"{name} - "
        f"{checkin_date} til {checkout_date}"
    )

else:
    st.text("Ingen bookinger i session")
st.write(st.session_state)

booking_number = st.session_state.get("reservation_number")

if booking_number:

    st.write("BOOKING FUNDET")

    name = st.session_state.get("reservation_name", "")
    checkin_date = st.session_state.get("reservation_checkin_date", "")
    checkout_date = st.session_state.get("reservation_checkout_date", "")

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
# DATA SETUP
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(exist_ok=True)

BOOKING_FILE = DATA_DIR / "booking_data.csv"

if not BOOKING_FILE.exists():
    pd.DataFrame(
        columns=["Værelse", "Start", "Slut", "Gæst"]
    ).to_csv(BOOKING_FILE, index=False)

#st.write("Current file:", __file__)
#st.write("BASE_DIR:", BASE_DIR)
#st.write("DATA_DIR:", DATA_DIR)
#st.write("BOOKING_FILE:", BOOKING_FILE)


def save_bookings():

    if "booking_data" not in st.session_state:
        st.warning("Ingen booking_data i session")
        return

    if st.session_state.booking_data.empty:
        st.warning("booking_data er tom — gemmer ikke")
        return

    st.session_state.booking_data.to_csv(
        BOOKING_FILE,
        index=False,
        encoding="utf-8"
    )

    st.success(
        f"Gemte {len(st.session_state.booking_data)} bookinger"
    )

st.subheader('Anvend igangværende booking data fra "booking"')


# -------------------------
# LOAD / INIT DATA
# -------------------------
if "booking_data" not in st.session_state:

    if BOOKING_FILE.exists() and BOOKING_FILE.stat().st_size > 0:

        try:
            st.session_state.booking_data = pd.read_csv(
                BOOKING_FILE,
                parse_dates=["Start", "Slut"]
            )
            # Fjern unnamed kolonner
            st.session_state.booking_data = (
                st.session_state.booking_data
                .loc[:, ~st.session_state.booking_data.columns.str.contains("^Unnamed")]
            )

            # Sikre korrekte datatyper
            st.session_state.booking_data["Værelse"] = (
                st.session_state.booking_data["Værelse"].astype(str)
            )

            st.session_state.booking_data["Gæst"] = (
                st.session_state.booking_data["Gæst"].astype(str)
            )

        except Exception as e:

            st.error(f"Fejl ved læsning: {e}")

            st.session_state.booking_data = pd.DataFrame(
                columns=["Værelse", "Start", "Slut", "Gæst"]
            )

    else:

        st.session_state.booking_data = pd.DataFrame(
            columns=["Værelse", "Start", "Slut", "Gæst"]
        )

        st.session_state.booking_data.to_csv(BOOKING_FILE, index=False)

# -------------------------
# OPRET BOOKING
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
                "Gæst": name
            }])

            st.session_state.booking_data = pd.concat(
                [st.session_state.booking_data, new_row],
                ignore_index=True
            )

            save_bookings()
            st.success("Booking gemt")
            st.rerun()

# -------------------------
# VIS BOOKINGER
# -------------------------
# -------------------------
# VIS BOOKINGER
# -------------------------
st.subheader("Belægningsplan")

if not st.session_state.booking_data.empty:

    df = st.session_state.booking_data.copy()

    df["Start"] = pd.to_datetime(df["Start"])
    df["Slut"] = pd.to_datetime(df["Slut"])

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Slut",
        y="Værelse",
        color="Gæst",
        hover_name="Gæst",
        text="Gæst",
    )

    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Dato",
        yaxis_title="",
        showlegend=False,
        height=400
    )

    fig.update_xaxes(rangeslider_visible=True)

    fig.update_xaxes(
        tickformat="%d-%m",
        tickangle=0
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------
    # ADMINISTRATION
    # -------------------------
    st.subheader("Administrer bookinger")

    booking_index = st.selectbox(
        "Vælg booking",
        st.session_state.booking_data.index,
        format_func=lambda x:
            f"{st.session_state.booking_data.loc[x, 'Gæst']} - "
            f"{st.session_state.booking_data.loc[x, 'Værelse']}"
    )

    booking = st.session_state.booking_data.loc[booking_index]

    new_room = st.selectbox(
        "Rediger værelse",
        [f"Værelse {i}" for i in range(1, 8)],
        index=int(booking["Værelse"].split()[-1]) - 1
    )

    new_start = st.date_input(
        "Rediger start",
        value=pd.to_datetime(booking["Start"])
    )

    new_end = st.date_input(
        "Rediger slut",
        value=pd.to_datetime(booking["Slut"])
    )

    new_guest = st.text_input(
        "Rediger gæst",
        value=booking["Gæst"]
    )

    col1, col2 = st.columns(2)

    # GEM ÆNDRINGER
    with col1:

        if st.button("Gem ændringer"):

            st.session_state.booking_data.loc[booking_index] = [
                new_room,
                pd.to_datetime(new_start),
                pd.to_datetime(new_end),
                new_guest
            ]

            save_bookings()

            st.success("Booking opdateret")

            st.rerun()

    # SLET BOOKING
    with col2:

        if st.button("Slet booking"):

            st.session_state.booking_data = (
                st.session_state.booking_data
                .drop(index=booking_index)
                .reset_index(drop=True)
            )

            save_bookings()

            st.success("Booking slettet")

            st.rerun()

    # VIS TABEL
    with st.expander("Se alle bookinger som liste"):

        st.dataframe(st.session_state.booking_data)

else:

    st.info("Ingen bookinger at vise endnu.")
if "booking_data" not in st.session_state:

    if BOOKING_FILE.exists() and BOOKING_FILE.stat().st_size > 0:

        try:
            st.session_state.booking_data = pd.read_csv(
                BOOKING_FILE,
                parse_dates=["Start", "Slut"]
            )

        except Exception as e:

            st.error(f"Fejl ved læsning: {e}")

            st.session_state.booking_data = pd.DataFrame(
                columns=["Værelse", "Start", "Slut", "Gæst"]
            )

    else:

        st.session_state.booking_data = pd.DataFrame(
            columns=["Værelse", "Start", "Slut", "Gæst"]
        )




