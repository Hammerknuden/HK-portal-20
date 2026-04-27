import streamlit as st
from auth import require_login
st.set_page_config(
        page_title="main",
        layout="wide",
        initial_sidebar_state="expanded",
)
st.text("version 2.0.1")
st.image("logo2.jpg")
st.title("HAMMERKNUDEN SOMMERPENSION")

#require_login()

st.success(f"Velkommen {st.session_state.get('username')} 👋")
st.info("Brug menuen i venstre side 👈")


