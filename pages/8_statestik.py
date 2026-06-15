import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
import plotly.express as px
from auth import require_login
from common import init_session
import plotly.express as px
import os
from dotenv import load_dotenv
from supabase import create_client
# -------------------------
# INIT
# -------------------------

st.set_page_config(page_title="Timeline", layout="wide")
require_login()

load_dotenv()

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

try:
    all_rows = []
    offset = 0
    page_size = 1000

    while True:
        response = (
            supabase.table("hk_dtb")
            .select("*")
            .range(offset, offset + page_size - 1)
            .execute()
        )

        if not response.data:
            break

        all_rows.extend(response.data)
        offset += page_size

    df = pd.DataFrame(all_rows)

    # Fjern annullerede bookinger
    df = df[
        df["web"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        != "CANSL"
        ]

    # Beregn antal nætter
    df["checkin_date"] = pd.to_datetime(df["checkin_date"])
    df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    df["nights"] = (
        df["checkout_date"] - df["checkin_date"]
    ).dt.days

    df["overnatninger"] = (
        df["numb_guests"] * df["nights"]
    )
    df["nation"] = (
        df["nation"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df[df["nation"] != ""]
    # Statistik pr. land
    stats = (
        df.groupby("nation")
        .agg(
            ankomster=("numb_guests", "sum"),
            overnatninger=("overnatninger", "sum")
        )
        .reset_index()
    )

    hovedlande = ["DK", "D", "S", "N", "NL"]

    stats["nation"] = stats["nation"].fillna("").str.upper()

    stats["gruppe"] = stats["nation"].apply(
        lambda x: x if x in hovedlande else "ANDRE"
    )

    rapport = (
        stats.groupby("gruppe")
        .agg({
            "ankomster": "sum",
            "overnatninger": "sum"
        })
        .reset_index()
    )

    st.success("Forbindelse OK")

except Exception as e:
    st.error(f"Fejl: {e}")

st.subheader("Rapport til Danmarks Statistik")
st.dataframe(rapport)

st.subheader("Booking com bookings")
# Bookingkanaler
kanal_df = df.copy()

kanal_df["kanal"] = kanal_df["web"].str.upper().str.strip()

kanal_df["kanal"] = kanal_df["kanal"].apply(
    lambda x: "Booking.com" if x == "BC" else "Egne bookinger"
)

kanal_stats = (
    kanal_df.groupby("kanal")
    .agg(
        overnatninger=("overnatninger", "sum")
    )
    .reset_index()
)

st.write(kanal_stats)
fig = px.pie(
    kanal_stats,
    names="kanal",
    values="overnatninger",
    title="Andel af overnatninger fra Booking.com"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Booking pace")

response = (
    supabase.table("bookin_pace")
    .select("*")
    .execute()
)

pace_df = pd.DataFrame(response.data)
fig = px.line(
    pace_df,
    x="week_number",
    y="sold_nights",
    color="season_year",
    markers=True
)