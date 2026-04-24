import streamlit as st
from auth import login
st.set_page_config(
        page_title="main",
        layout="wide",
        initial_sidebar_state="expanded",
)
st.text("version 2.0.1")
st.image("logo2.jpg")
st.title("HAMMERKNUDEN SOMMERPENSION")
status = login()
if status:
    st.success(f"Velkommen {st.session_state.get('name')} 👋")
    st.info("Brug menuen i venstre side 👈")
elif status is False:
    st.error("Forkert login")

