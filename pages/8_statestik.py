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
    #markers=True
)
st.plotly_chart(fig, use_container_width=True)

st.subheader(" Omsætning inkl. moms")

historik_df = pd.DataFrame({
    "year": [2024, 2025],
    "maj": [86980, 78599],
    "juni": [143719, 121385],
    "juli": [151706, 146531],
    "aug": [146913, 159691],
    "sep": [107810, 104591]
})
df["checkin_date"] = pd.to_datetime(df["checkin_date"])

df["year"] = df["checkout_date"].dt.year
df["month"] = df["checkout_date"].dt.month

df["pris"] = (
    df["pris"]
    .astype(str)
    .str.replace(",", ".", regex=False)
)

df["pris"] = pd.to_numeric(
    df["pris"],
    errors="coerce"
)
oms_2026 = (
    df[df["year"] == 2026]
    .groupby("month")
    .agg(
        revenue=("pris", "sum")
    )
)
df["month"] = df["checkout_date"].dt.month

ny_række = pd.DataFrame({
    "year": [2026],
    "maj": [oms_2026.loc[5, "revenue"] if 5 in oms_2026.index else 0],
    "juni": [oms_2026.loc[6, "revenue"] if 6 in oms_2026.index else 0],
    "juli": [oms_2026.loc[7, "revenue"] if 7 in oms_2026.index else 0],
    "aug": [oms_2026.loc[8, "revenue"] if 8 in oms_2026.index else 0],
    "sep": [oms_2026.loc[9, "revenue"] if 9 in oms_2026.index else 0],
})
historik_df = pd.concat(
    [historik_df, ny_række],
    ignore_index=True
)
#st.subheader("Omsætning pr. måned med moms")

st.dataframe(historik_df)
historik_long = historik_df.melt(
    id_vars="year",
    var_name="month",
    value_name="revenue"
)
historik_long["year"] = historik_long["year"].astype(str)

fig = px.bar(
    historik_long,
    x="month",
    y="revenue",
    color="year",
    barmode="group",  # side om side
    title="Omsætning pr. måned"
)
#st.write(df["pris"].sum())
#st.write(df["pris"].describe())
st.write(
    df.groupby("month")
      .agg(
          bookinger=("pris", "count"),
          omsaetning=("pris", "sum")
      )
)
st.plotly_chart(fig, use_container_width=True)

