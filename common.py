import streamlit as st

def init_session():

    defaults = {
        "reservation_number": "",
        "reservation_name": "",
        "reservation_date": None,
        "reservation_checkin_date": None,
        "reservation_checkout_date": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value