import streamlit as st
from importlib.metadata import PackageNotFoundError, version
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

    for package, label in (("streamlit", "Streamlit"), ("supabase", "Supabase Python")):
        try:
            installed_version = version(package)
        except PackageNotFoundError:
            installed_version = "ikke installeret"
        st.text(f"{label}: {installed_version}")
    st.image("logo2.jpg")

    name = st.session_state.get("name") or st.session_state.get("username") or ""
    st.success(f"Velkommen {name} 👋")
    st.info("Brug menuen i venstre side 👈")


# Keep page scripts outside Streamlit's auto-discovered pages/ directory.
# This ensures direct links also initialize this navigation before login.
# The original Timeline source is kept as a reserve.
page = st.navigation([
    st.Page(show_home, title="Start", default=True),
    st.Page("portal_pages/1_Booking.py", title="Booking"),
    st.Page("portal_pages/kalender.py", title="Kalender"),
    st.Page("portal_pages/2_databaseopslag.py", title="Opslag"),
    st.Page("portal_pages/3_In and Out.py", title="In & Out"),
    st.Page("portal_pages/5_breakfast.py", title="Breakfast"),
    st.Page("portal_pages/4_Links.py", title="Links"),
    st.Page("portal_pages/8_statestik.py", title="Statistik"),
    st.Page("portal_pages/9_Booking_com_kontrol.py", title="Afstemning"),
    st.Page("portal_pages/7_setup.py", title="Setup"),
])
page.run()
