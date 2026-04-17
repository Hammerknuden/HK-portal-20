import streamlit as st
from auth import login


st.set_page_config(
    page_title="main",
    layout="wide"
)

st.image("logo2.jpg")
st.title("HAMMERKNUDEN SOMMERPENSION")

status = login()

if status:
    st.success(f"Velkommen {st.session_state.get('name')} 👋")
    st.write("Vælg en side i menuen 👈")
elif status is False:
    st.error("Forkert login")
else:
    st.info("Indtast loginoplysninger")


#page = st.sidebar.selectbox("Vælg side", ["Booking", "Setup"])

#if page == "Booking":
#    page: 1
#elif page == "Setup":
#    page: 2