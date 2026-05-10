import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import sys
import plotly.express as px
from auth import require_login
from booking import (booking_number, name, checkin_date, checkout_date)
from config.data_email import add_data

st.set_page_config(page_title="Timeline", layout="wide")
require_login()

st.subheader("Anvend igang værende booking data fra ""booking")
current_booking = st.checkbox("anvend igangværede booking")
if current_booking:
    st.text(f"booking nummer {booking_number}", f" {name}", {checkin_date}, {checkou_date})
else:
    st.text("fault in import")

if "booking_data" not in st.session_state:
    st.session_state.booking_data = pd.DataFrame(
        columns=["Værelse", "Start", "Slut", "Gæst"]
    )
    # -------------------------
    # OPRET BOOKING
    # -------------------------
with st.sidebar.form("booking_form"):

    room = st.selectbox(
        "Værelse",
        [f"Værelse {i}" for i in range(1, 8)]
    )

    #if current_booking:
    #    st.text("[name]")
    #    start_date = [checkin_date]
    #    end_date = checkout_data
    #else:
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
                "Start": start_date,
                "Slut": end_date,
                "Gæst": name
            }])

            st.session_state.booking_data = pd.concat(
                [st.session_state.booking_data, new_row],
                ignore_index=True
            )

            st.success("Booking gemt")
            st.rerun()

# -------------------------
# VIS BOOKINGER
# -------------------------
if not st.session_state.booking_data.empty:

    st.subheader("Belægningsplan")

    fig = px.timeline(
        st.session_state.booking_data,
        x_start="Start",
        x_end="Slut",
        y="Værelse",
        color="Værelse",
        hover_name="Gæst",
        text="Gæst",
        category_orders={
            "Værelse": [f"Værelse {i}" for i in range(1, 8)]
        }
    )

    # Grid og akser
    fig.update_xaxes(
        showgrid=True,
        gridwidth=5,
        gridcolor="black",
        dtick="D2"
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=5,
        gridcolor="black",
        autorange="reversed"
    )

    fig.update_layout(
        xaxis_title="Dato",
        yaxis_title="",
        showlegend=False,
        height=400,
        plot_bgcolor="white"
    )
    fig = px.timeline(
        st.session_state.booking_data,
        x_start="Start",
        x_end="Slut",
        y="Værelse",
        color="Værelse",
        hover_name="Gæst",
        text="Gæst",
        category_orders={
            "Værelse": [f"Værelse {i}" for i in range(1, 8)]
        }
    )
    # Layout
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        xaxis_title="Dato",
        yaxis_title="",
        showlegend=False,
        height=400
    )
    fig.update_xaxes(
        tickformat="%d-%m",
        tickangle=0
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------
    # REDIGER / SLET
    # -------------------------

    st.subheader("Administrer bookinger")

    booking_index = st.selectbox(
        "Vælg booking",
        st.session_state.booking_data.index,
        format_func=lambda x:
            f"{st.session_state.booking_data.loc[x, 'Gæst']} "
            f"- {st.session_state.booking_data.loc[x, 'Værelse']}"
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

            st.session_state.booking_data.loc[
                booking_index
            ] = [
                new_room,
                new_start,
                new_end,
                new_guest
            ]

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

            st.success("Booking slettet")
            st.rerun()

    # Vis tabel
    with st.expander("Se alle bookinger som liste"):
        st.dataframe(st.session_state.booking_data)

else:
    st.info("Ingen bookinger at vise endnu.")
#st.set_page_config(page_title="Booking med Tidslinje", layout="wide")

