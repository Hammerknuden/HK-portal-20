import streamlit as st
from auth import require_login, require_admin
st.set_page_config(page_title="Setup", layout="wide")
require_login()
require_admin()

st.title("Setup ⚙️")

st.write("Her kan du styre systemet")

# Eksempel:
new_year = st.text_input("Tilføj nyt booking år")
if st.button("Gem"):
    st.success(f"{new_year} gemt!")
