import streamlit as st
from auth import require_login

st.set_page_config(
    page_title="main",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("HAMMERKNUDEN SOMMERPENSION")

# INIT AUTH STATE
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

if "username" not in st.session_state:
    st.session_state["username"] = None

# 🔥 DENNE MANGLEDE
if "logout" not in st.session_state:
    st.session_state["logout"] = None

# LOGIN
require_login()

# hvis ikke logget ind → stop
if not st.session_state.get("authentication_status"):
    st.stop()

st.text("version 2.1.1")
st.image("logo2.jpg")

st.success(f"Velkommen {st.session_state.get('username')} 👋")
st.info("Brug menuen i venstre side 👈")
