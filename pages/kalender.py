"""Timeline 3.0, first step: a read-only calendar alongside Timeline."""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from auth import require_login
from modules.calendar_view import build_calendar, prepare_bookings
from portal_access import get_database_client


st.set_page_config(page_title="Kalender · Timeline 3.0", layout="wide")
require_login()
load_dotenv()
st.subheader("Kalender · Timeline 3.0")
st.caption("Trin 1: Visning. Flytning og redigering af bookinger kommer senere.")
season = st.selectbox("Sæson", [2026, 2027, 2028], key="calendar_season")
client = get_database_client()

try:
    rows = client.table("hk_dtb").select("*").eq("season", season).execute().data
    bookings = prepare_bookings(pd.DataFrame(rows or []), season)
except Exception:
    st.error("Bookingerne kunne ikke hentes. Prøv at genindlæse siden.")
    st.stop()

try:
    rows = client.table("Events").select("*").eq("season", season).execute().data
    events = pd.DataFrame(rows or [])
except Exception:
    st.warning("Events kunne ikke hentes. Kalenderen viser kun bookinger.")
    events = pd.DataFrame()

st.write(f"Antal bookinger i sæson {season}:", len(bookings))
st.subheader("Belægningsplan")
st.caption(
    "Farver: web = grøn · bc = blå · FM = orange · Låst = rød (overstyrer typen) · "
    "Øvrige = grå. Bookingnummeret bestemmer nuancen."
)
zoom = st.checkbox("Zoom omkring dags dato", key="calendar_zoom_today")
if bookings.empty:
    st.info("Ingen bookinger at vise i den valgte sæson.")
st.plotly_chart(build_calendar(bookings, events, season, zoom), use_container_width=True,
                key="calendar_chart")
