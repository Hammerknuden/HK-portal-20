import streamlit as st
from auth import require_login

require_login()

st.title("Reservations formular")

year = st.selectbox("booking år", ["2026", "2027"])
now = st.date_input("booking dato")
booking_number = st.text_input("booking nummer")
