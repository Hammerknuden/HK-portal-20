"""Separate Cloud entrypoint for testing the restored backup with legacy login."""
import streamlit as st
from portal_access import validate_restore_test

st.set_page_config(page_title="TEST – Hammerknuden", layout="wide")
validate_restore_test(required=True)
st.warning("TESTAPP – gendannet backup. Ændringer gælder kun testdata. Ingen mails sendes.")
st.navigation([
    st.Page("app.py", title="Start", default=True),
    st.Page("pages/1_Booking.py", title="Booking"),
    st.Page("pages/2_databaseopslag.py", title="Databaseopslag"),
    st.Page("pages/3_In and Out.py", title="In and Out"),
    st.Page("pages/4_Links.py", title="Links"),
    st.Page("pages/5_breakfast.py", title="Morgenmad"),
    st.Page("pages/6_timeline.py", title="Timeline"),
    st.Page("pages/7_setup.py", title="Setup"),
    st.Page("pages/8_statestik.py", title="Statistik"),
    st.Page("pages/9_Booking_com_kontrol.py", title="Booking.com-kontrol"),
]).run()
