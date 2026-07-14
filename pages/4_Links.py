import streamlit as st
from auth import require_login

st.set_page_config(page_title="link", layout="wide")
require_login()

st.link_button("Booking_com", "https://account.booking.com")
st.link_button("Mobil pay", "https://portal.vippsmobilepay.com/login")
st.link_button("Zettle", "https://login.zettle.com/login?username=bonnevie%40mail.dk")
st.link_button("Danske Bank", "https://shared-logon.danskebank.com/logon/default/index.html?clientId=District-DK")
