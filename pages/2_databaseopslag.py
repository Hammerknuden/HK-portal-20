import streamlit as st
from auth import require_login
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


TABLE_NAME = "historie_new"

st.set_page_config(page_title="Database", layout="wide")
require_login()

load_dotenv()

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

try:
    supabase.table(TABLE_NAME).select("id").limit(1).execute()

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

if st.button("Søg"):
    try:
        if familie_navn.strip():
            result = (
                supabase
                .table(TABLE_NAME)
                .select("*")
                .ilike("familie_navn", familie_navn.strip())
                .execute()
            )
        elif telefon.strip():
            result = (
                supabase
                .table(TABLE_NAME)
                .select("*")
                .eq("phone", telefon.strip())
                .execute()
            )
        elif email.strip():
            # E-mailopslag er ikke afgrænset af sæson og viser derfor
            # alle bookinger med den pågældende adresse.
            result = (
                supabase
                .table(TABLE_NAME)
                .select("*")
                .ilike("email", email.strip())
                .execute()
            )
        elif booking.strip():
            try:
                booking_nr = int(booking.strip())
            except ValueError:
                st.error("Bookingnummer skal være et helt tal.")
                st.stop()

            # Bookingnumre kan gentages i forskellige sæsoner.
            result = (
                supabase
                .table(TABLE_NAME)
                .select("*")
                .eq("season", int(season))
                .eq("booking_nr", booking_nr)
                .execute()
            )
        else:
            st.warning("Udfyld mindst ét søgefelt.")
            st.stop()

        if result.data:
            st.dataframe(pd.DataFrame(result.data), use_container_width=True)
        else:
            st.info("Ingen bookinger fundet.")
    except Exception as e:
        st.error(f"Opslaget kunne ikke gennemføres: {e}")

