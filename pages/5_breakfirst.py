import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import streamlit as st
from auth import require_login
import pandas as pd
from datetime import date, timedelta
sys.path.append(str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from supabase import create_client

st.set_page_config(page_title="Cleaning plan", layout="wide")
require_login()

st.subheader("Antal personer til morgenmad ")

load_dotenv()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.success("Forbindelse OK")

# Datoer
check_dato_start = date.today()

antal_dage = st.selectbox(
    "Vis udcheckninger de næste dage",
    [3, 5, 7, 9, 14],
    index=0
)

check_dato_slut = check_dato_start + timedelta(days=antal_dage)

# Hent data fra Supabase
result = (
    supabase
    .table("hk_dtb")
    .select(
        "checkin_date, checkout_date, numb_guests, morgenmad, web"
    )
    .neq("web", "cansl")
    .execute()
)

df = pd.DataFrame(result.data or [])

if not df.empty:

    df["checkin_date"] = pd.to_datetime(
        df["checkin_date"],
        errors="coerce"
    ).dt.date

    df["checkout_date"] = pd.to_datetime(
        df["checkout_date"],
        errors="coerce"
    ).dt.date

    df["numb_guests"] = pd.to_numeric(
        df["numb_guests"],
        errors="coerce"
    ).fillna(0)

    df["morgenmad"] = (
        df["morgenmad"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    breakfast_rows = []

    for d in pd.date_range(
        check_dato_start,
        check_dato_slut,
        freq="D"
    ):
        dato = d.date()

        antal = df.loc[
            (df["morgenmad"] == "Y")
            & (df["checkin_date"] < dato)
            & (df["checkout_date"] >= dato),
            "numb_guests"
        ].sum()

        breakfast_rows.append({
            "Dato": dato,
            "Morgenmadsgæster": int(antal)
        })

    breakfast_df = pd.DataFrame(breakfast_rows)

    st.subheader("Morgenmadsoversigt")

    st.dataframe(
        breakfast_df,
        hide_index=True,
        use_container_width=True
    )

else:
    st.info("Ingen bookinger fundet")

