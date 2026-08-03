from datetime import date
import streamlit as st


def exclude_cancelled_bookings(df, column="web"):
    """Remove bookings whose status is a variant of 'cansl'."""
    if df.empty or column not in df.columns:
        return df

    normalized_status = (
        df[column]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9]", "", regex=True)
    )
    return df[normalized_status != "cansl"].copy()


def init_session():
    defaults = {
        "reservation_number": "",
        "reservation_name": "",
        "reservation_checkin_date": date.today(),
        "reservation_checkout_date": date.today()
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


