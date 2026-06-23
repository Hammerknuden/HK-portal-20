import streamlit as st
from auth import require_login
import pandas as pd
from pathlib import Path
import sys
from datetime import date, timedelta
sys.path.append(str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from supabase import create_client


st.set_page_config(page_title="Ankomster", layout="wide")
#require_login()

st.subheader("De næste dages ankomster og afrejser ")
# Date inputs fra Streamlit


#######
#Supabase
#######

load_dotenv()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.success("Forbindelse OK")

# Datoer
check_dato_start = date.today()

antal_dage = st.selectbox(
    "Ankomster og afrejser de næste dage",
    [3, 5, 7, 9, 14],
    index=0
)
st.subheader(" Ankomster ")

check_dato_slut = check_dato_start + timedelta(days=antal_dage)

# Hent data fra Supabase
result = (
    supabase.table("hk_dtb")
    .select(
        "booking_number, navn, checkin_date, ankomst, bed, known, room_number, nation, enkelt"
    )
    .gte("checkin_date", str(check_dato_start))
    .lte("checkin_date", str(check_dato_slut))
    .neq("web", "cansl")
    .order("room_number")
    .execute()
)

df = pd.DataFrame(result.data)

# Sortér værelser 1-5
df = pd.DataFrame(result.data)

if not df.empty:
    df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")
    df = df.sort_values(["checkin_date", "room_number"])

    st.table(
        df[
            [
                "checkin_date",
                "booking_number",
                "room_number",
                "navn",
                "nation",
                "ankomst",
                "bed",
                "enkelt",
                "known",
            ]
        ].rename(
            columns={
                "checkin_date": "Check-in",
                "booking_number": "Booking nr.",
                "room_number": "Værelse",
                "navn": "Navn",
                "nation": "Land",
                "ankomst": "Ankomst",
                "bed": "Seng",
                "enkelt": "Enkelt",
                "known": "Kendt",
            }
        )
    )
else:
    st.info("Ingen ankomster i perioden.")

st.subheader("Periodens afrejser")
result = (
    supabase.table("hk_dtb")
    .select(
        "booking_number, checkout_date, room_number, web"
    )
    .gte("checkout_date", str(check_dato_start))
    .lte("checkout_date", str(check_dato_slut))
    .neq("web", "cansl")
    .order("checkout_date")
    .execute()
)

df = pd.DataFrame(result.data)

#st.write(df["web"].unique())

# Sortér værelser 1-5
df = pd.DataFrame(result.data)

if not df.empty:
    df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")
    df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    df = df.sort_values(["checkout_date", "room_number"])

    st.table(
        df[
            [
                "checkout_date",
                "room_number",
                "booking_number",
            ]
        ].rename(
            columns={
                "checkout_date": "Udcheck",
                "room_number": "Værelse",
                "booking_number": "Booking nr.",
            }
        )
    )
else:
    st.info("Ingen udcheckninger i perioden.")

st.components.v1.html(
    """
    <button
        onclick="window.print()"
        style="
            background-color:#4CAF50;
            color:white;
            padding:10px 20px;
            border:none;
            border-radius:5px;
            cursor:pointer;
            font-size:16px;
        ">
        🖨️ Print rapport
    </button>
    """,
    height=60,
)

#st.write( " for print brug Ctrl + P husk at lukke sidebar først")

