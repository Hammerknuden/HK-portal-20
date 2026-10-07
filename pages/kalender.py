"""Timeline 3.0 with fixed-date room moves and scoped 2027 saving."""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from auth import require_login
from modules.calendar_view import build_calendar, prepare_bookings
from modules.calendar_drag import accept_move, preview_moves, render_drag_calendar
from modules.calendar_save import active_rows, build_move_request, load_calendar_rows, save_move_request
from portal_access import get_database_client, uses_supabase_auth


st.set_page_config(page_title="Kalender · Timeline 3.0", layout="wide")
require_login()
load_dotenv()
st.subheader("Kalender · Timeline 3.0")
st.caption("Trin 3: Flyt mellem værelser med faste datoer. Lagring afprøves kun i sæson 2027.")
season = st.selectbox("Sæson", [2026, 2027, 2028], key="calendar_season",
                      disabled=st.session_state.get("calendar_save_pending", False))
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
st.caption("Træk en booking direkte i kalenderen op eller ned til et andet værelse. "
           "Datoerne er faste; røde, låste bookinger bliver stående. "
           "Zoom og tidslinjen nederst ændrer datovisningen. "
           "Gem flytninger kontrollerer overlap og låse. Lagring er aktiveret for 2027.")
if bookings.empty:
    st.info("Ingen bookinger at vise i den valgte sæson.")
moves_key = f"calendar_moves_{season}"
sources_key = f"calendar_sources_{season}"
if moves_key not in st.session_state:
    st.session_state[moves_key] = {}
if sources_key not in st.session_state:
    st.session_state[sources_key] = {}
pending = st.session_state.get("calendar_save_pending", False)
if "calendar_saved_message" in st.session_state:
    st.success(st.session_state.pop("calendar_saved_message"))


def cancel_room_moves():
    st.session_state[moves_key] = {}
    st.session_state[sources_key] = {}
    st.session_state.pop("calendar_save_request", None)
    st.session_state["calendar_drag_revision"] = st.session_state.get("calendar_drag_revision", 0) + 1


st.button("Nulstil flytninger", disabled=pending or not st.session_state[moves_key],
          on_click=cancel_room_moves)
preview = preview_moves(bookings, st.session_state[moves_key])
figure = build_calendar(preview, events, season, zoom)
drag_key = f"calendar_drag_{season}"


def handle_room_move():
    # Apply before the page reruns, so it never renders the old room on drop.
    request = st.session_state[drag_key].move
    if st.session_state.get("calendar_save_pending"):
        return
    try:
        occupancy = active_rows(load_calendar_rows(client))
        updated = accept_move(bookings, st.session_state[moves_key], request, occupancy=occupancy)
        identity = str(request["id"])
        if identity in updated and identity not in st.session_state[sources_key]:
            source = bookings[bookings.id.astype(str) == identity].iloc[0].to_dict()
            st.session_state[sources_key][identity] = source
        if identity not in updated:
            st.session_state[sources_key].pop(identity, None)
        st.session_state[moves_key] = updated
    except ValueError as error:
        st.session_state["calendar_move_error"] = str(error)
        st.session_state["calendar_drag_revision"] = st.session_state.get("calendar_drag_revision", 0) + 1
    except Exception:
        st.session_state["calendar_move_error"] = "Belægningen kunne ikke kontrolleres. Flytningen er annulleret."
        st.session_state["calendar_drag_revision"] = st.session_state.get("calendar_drag_revision", 0) + 1


render_drag_calendar(preview, *figure.layout.xaxis.range,
                     key=drag_key, on_move=handle_room_move, disabled=pending,
                     revision=st.session_state.get("calendar_drag_revision", 0),
                     figure=figure, view_key=f"{season}:{zoom}")
if "calendar_move_error" in st.session_state:
    st.error(st.session_state.pop("calendar_move_error"))
if st.session_state[moves_key]:
    st.info(f"{len(st.session_state[moves_key])} værelsesflytning(er) i kladde – ikke gemt.")
    summary = []
    for identity, destination in st.session_state[moves_key].items():
        source = st.session_state[sources_key].get(identity, {})
        summary.append({"Booking": source.get("booking_number"),
                        "Fra værelse": source.get("room_number"), "Til værelse": destination,
                        "Ankomst": str(source.get("checkin_date", ""))[:10],
                        "Afrejse": str(source.get("checkout_date", ""))[:10]})
    st.dataframe(pd.DataFrame(summary), hide_index=True)
    st.button("Annuller flytninger", disabled=pending, on_click=cancel_room_moves)
if pending:
    st.warning("Gemningen er endnu ikke bekræftet. Prøv Gem flytninger igen for at afklare "
               "samme gemning. Kladden er fastholdt indtil da.")
if st.button("Gem flytninger i 2027", disabled=season != 2027 or
             (not st.session_state[moves_key] and not pending)):
    try:
        writer = get_database_client(allow_booking_writes=True)
        if not pending:
            request = build_move_request(load_calendar_rows(client),
                                         st.session_state[sources_key],
                                         st.session_state[moves_key], season)
            st.session_state["calendar_save_request"] = request
        st.session_state["calendar_save_pending"] = True
        save_move_request(writer, st.session_state["calendar_save_request"],
                          authenticated=uses_supabase_auth())
    except Exception as error:
        code = str(getattr(error, "code", ""))
        if code in {"P0001", "42501", "55P03", "57014", "PGRST202"}:
            st.session_state["calendar_save_pending"] = False
            st.session_state.pop("calendar_save_request", None)
            if code == "PGRST202":
                st.error("Kalenderens SQL-funktion skal installeres i Supabase først. "
                         "Ingen flytninger er gemt.")
            else:
                st.error("Databasen afviste flytningen. Ingen flytninger er gemt. "
                         "Nulstil kladden og kontrollér overlap, låse og skriveadgang.")
        elif st.session_state.get("calendar_save_pending"):
            st.error("Gemningen eller genlæsningen kunne ikke bekræftes. "
                     "Prøv Gem flytninger igen med samme kladde.")
        elif isinstance(error, ValueError):
            # No request was sent: restore persisted positions immediately.
            st.session_state[moves_key] = {}
            st.session_state[sources_key] = {}
            st.session_state.pop("calendar_save_request", None)
            st.session_state["calendar_move_error"] = str(error) + " Kladden er annulleret."
            st.session_state["calendar_drag_revision"] = st.session_state.get("calendar_drag_revision", 0) + 1
            st.rerun()
        else:
            st.error("Bookingerne kunne ikke kontrolleres. Prøv igen.")
        # Refresh controls whenever the request changes between pending/resolved.
        if code == "P0001":
            st.session_state[moves_key] = {}
            st.session_state[sources_key] = {}
            st.session_state["calendar_move_error"] = "Flytningen blev afvist. Kladden er annulleret, og bookingerne viser deres gemte placering."
            st.session_state["calendar_drag_revision"] = st.session_state.get("calendar_drag_revision", 0) + 1
            st.rerun()
        if pending and not st.session_state.get("calendar_save_pending"):
            st.session_state["calendar_move_error"] = "Gemningen blev afvist. Ingen flytninger er gemt."
            st.rerun()
        if st.session_state.get("calendar_save_pending") and not pending:
            st.rerun()
    else:
        st.session_state["calendar_save_pending"] = False
        st.session_state.pop("calendar_save_request", None)
        st.session_state[moves_key] = {}
        st.session_state[sources_key] = {}
        st.session_state["calendar_saved_message"] = "Flytningerne er gemt og genlæst fra Supabase."
        st.rerun()
