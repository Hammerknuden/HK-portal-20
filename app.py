import streamlit as st
from auth import require_login
st.set_page_config(
        page_title="main",
        layout="wide",
        initial_sidebar_state="expanded",
)
st.title("HAMMERKNUDEN SOMMERPENSION")
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

if "username" not in st.session_state:
    st.session_state["username"] = None

if "name" not in st.session_state:
    st.session_state["name"] = None

if "logout" not in st.session_state:
    st.session_state["logout"] = None

require_login()

st.text("version 2.0.1")
st.image("logo2.jpg")
#st.title("HAMMERKNUDEN SOMMERPENSION")



st.success(f"Velkommen {st.session_state.get('username')} 👋")
st.info("Brug menuen i venstre side 👈")


