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

st.subheader("Dagens ankomster ")
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
    "Vis ankomster de næste dage",
    [3, 5, 7, 9, 14],
    index=0
)

check_dato_slut = check_dato_start + timedelta(days=antal_dage)

# Hent data fra Supabase
result = (
    supabase.table("hk_dtb")
    .select(
        "booking_number, navn, checkin_date, ankomst, bed, known, room_number"
    )
    .gte("checkin_date", str(check_dato_start))
    .lte("checkin_date", str(check_dato_slut))
    .neq("web", "cansl")
    .order("room_number")
    .execute()
)

df = pd.DataFrame(result.data)

# Sortér værelser 1-5
if not df.empty:
    df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")
    df = df.sort_values(["room_number", "checkin_date"])

    st.dataframe(
        df[
            [
                "checkin_date",
                "booking_number",
                "room_number",
                "navn",
                "ankomst",
                "bed",
                "known",

            ]
        ],
        use_container_width=True,
    )
else:
    st.info("Ingen ankomster i perioden.")
