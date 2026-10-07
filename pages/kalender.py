"""Timeline 3.0, first step: a read-only calendar alongside Timeline."""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from auth import require_login
from modules.calendar_view import build_calendar, prepare_bookings
from modules.calendar_drag import accept_move, preview_moves, render_drag_calendar
from portal_access import get_database_client


st.set_page_config(page_title="Kalender · Timeline 3.0", layout="wide")
require_login()
load_dotenv()
st.subheader("Kalender · Timeline 3.0")
st.caption("Trin 2: Afprøv flytning mellem værelser. Flytninger er kladder og gemmes ikke i databasen.")
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
moves_key = f"calendar_moves_{season}"
if moves_key not in st.session_state:
    st.session_state[moves_key] = {}
if st.button("Nulstil flytninger", disabled=not st.session_state[moves_key]):
    st.session_state[moves_key] = {}
preview = preview_moves(bookings, st.session_state[moves_key])
figure = build_calendar(preview, events, season, zoom)
st.plotly_chart(figure, use_container_width=True,
                key="calendar_chart")
st.subheader("Afprøv værelsesflytning")
st.caption("Træk en booking op eller ned til et andet værelse. Datoerne er faste. "
           "Røde, låste bookinger kan ikke trækkes. Brug knapperne til zoom og rul vandret. "
           "Overlapkontrol og lagring kommer i trin 3.")
result = render_drag_calendar(preview, *figure.layout.xaxis.range,
                              key=f"calendar_drag_{season}")
if result.move:
    try:
        st.session_state[moves_key] = accept_move(bookings, st.session_state[moves_key], result.move)
    except ValueError as error:
        st.error(str(error))
    else:
        st.rerun()
if st.session_state[moves_key]:
    st.info(f"{len(st.session_state[moves_key])} værelsesflytning(er) i kladde – ikke gemt.")
