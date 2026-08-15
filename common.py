from datetime import date
import streamlit as st


def exclude_cancelled_bookings(
    df,
    column="web",
    booking_column="booking_number",
):
    """Remove cancelled rows and every row belonging to their booking."""
    if df.empty or column not in df.columns:
        return df

    normalized_status = (
        df[column]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[^a-z0-9]", "", regex=True)
    )
    cancelled_rows = normalized_status == "cansl"

    if booking_column not in df.columns:
        return df[~cancelled_rows].copy()

    booking_keys = (
        df[booking_column]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0+$", "", regex=True)
    )
    cancelled_booking_keys = booking_keys[cancelled_rows & booking_keys.ne("")]

    return df[
        ~cancelled_rows & ~booking_keys.isin(cancelled_booking_keys)
    ].copy()


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


