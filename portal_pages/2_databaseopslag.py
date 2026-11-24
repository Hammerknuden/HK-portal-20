import streamlit as st
from auth import require_login, require_admin, is_admin
from modules.guest_document import download_registration
import pandas as pd
from dotenv import load_dotenv
from portal_access import get_database_client


BOOKING_SOURCES = (
    ("hk_dtb", "Bookinger i reservationssystemet", "telefon", "booking_number"),
    ("historie_new", "Historiske bookinger", "phone", "booking_nr"),
)

st.set_page_config(page_title="Database", layout="wide")
require_login()

load_dotenv()

supabase = get_database_client()

try:
    for table_name, _, _, booking_column in BOOKING_SOURCES:
        supabase.table(table_name).select(booking_column).limit(1).execute()

    st.success("Forbindelse OK")

except Exception as e:
    st.error(f"Fejl: {e}")
    st.stop()

st.subheader("Databaseopslag")


familie_navn = st.text_input("Familienavn")
telefon = st.text_input("Telefon")
email = st.text_input("Email")
booking = st.text_input("Bookingnummer")
season = st.number_input(
    "Sæson for bookingnummer",
    min_value=2022,
    max_value=2100,
    value=2025,
    step=1,
    help="Sæson bruges kun, når du søger på bookingnummer.",
)

search_values = (familie_navn, telefon, email, booking, int(season))
if st.button("Søg"):
    st.session_state["history_active_search"] = search_values

if st.session_state.get("history_active_search") == search_values:
    try:
        if familie_navn.strip():
            match_column, match_value = "familie_navn", familie_navn.strip()
        elif telefon.strip():
            match_column, match_value = "phone", telefon.strip()
        elif email.strip():
            match_column, match_value = "email", email.strip()
        elif booking.strip():
            try:
                match_value = int(booking.strip())
            except ValueError:
                st.error("Bookingnummer skal være et helt tal.")
                st.stop()
            match_column = "booking_nr"
        else:
            st.warning("Udfyld mindst ét søgefelt.")
            st.stop()

        found_bookings = False
        for table_name, heading, phone_column, booking_column in BOOKING_SOURCES:
            query = supabase.table(table_name).select("*")
            if match_column == "booking_nr":
                query = query.eq("season", int(season)).eq(booking_column, match_value)
            elif match_column == "phone":
                query = query.eq(phone_column, match_value)
            else:
                query = query.ilike(match_column, match_value)

            result = query.execute()
            if not result.data:
                continue

            found_bookings = True
            st.markdown(f"#### {heading}")
            dataframe = pd.DataFrame(result.data).drop(columns=["created_at"], errors="ignore")
            st.dataframe(dataframe, use_container_width=True)
            if is_admin():
                for index, row in enumerate(result.data):
                    path = row.get("storage_path")
                    if not path:
                        continue
                    label = f"Gæsteregistrering – {row.get('season')} / booking {row.get(booking_column)}"
                    if st.button(label, key=f"guest_document_{table_name}_{index}"):
                        try:
                            filename, pdf = download_registration(supabase, path, require_admin)
                            st.download_button(
                                "Åbn / download PDF", data=pdf,
                                file_name=filename, mime="application/pdf",
                                key=f"guest_document_download_{table_name}_{index}", on_click="ignore",
                            )
                        except Exception:
                            st.error("Dokumentet kunne ikke hentes. Kontrollér filstien og din Storage-adgang.")
        if not found_bookings:
            st.info("Ingen bookinger fundet.")
    except Exception as e:
        st.error(f"Opslaget kunne ikke gennemføres: {e}")

