import streamlit as st
from auth import login


st.set_page_config(
    page_title="Hammerknuden Booking",
    layout="wide"
)

st.image("logo2.jpg")
st.title("HAMMERKNUDEN SOMMERPENSION")

status = login()

if status:
    st.success(f"Velkommen {st.session_state['name']} 👋")
    st.write("Vælg en side i menuen 👈")
elif status is False:
    st.stop()
else:
    st.stop()