import streamlit as st


def init_session():

    defaults = {
        "reservation_number": "",
        "reservation_name": "",
        "reservation_date": date.today(),
        "reservation_checkin_date": date.today(),
        "reservation_checkout_date": date.today(),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value