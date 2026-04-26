import streamlit as st
from auth import require_login

st.set_page_config(page_title="link", layout="wide")
require_login()

st.link_button("Booking_com", "https://account.booking.com")