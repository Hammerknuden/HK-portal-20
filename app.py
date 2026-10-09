import streamlit as st
from auth import require_login

st.set_page_config(
    page_title="main",
    layout="wide",
    initial_sidebar_state="expanded",
)


def show_home():
    st.subheader("HAMMERKNUDEN SOMMERPENSION")

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


# Explicit navigation keeps the original Timeline source as a reserve.
page = st.navigation([
    st.Page(show_home, title="Forside", default=True),
    st.Page("pages/1_Booking.py", title="Booking"),
    st.Page("pages/2_databaseopslag.py", title="Databaseopslag"),
    st.Page("pages/3_In and Out.py", title="In and Out"),
    st.Page("pages/4_Links.py", title="Links"),
    st.Page("pages/5_breakfast.py", title="Breakfast"),
    st.Page("pages/kalender.py", title="Kalender"),
    st.Page("pages/7_setup.py", title="Setup"),
    st.Page("pages/8_statestik.py", title="Statestik"),
    st.Page("pages/9_Booking_com_kontrol.py", title="Booking com kontrol"),
])
page.run()
