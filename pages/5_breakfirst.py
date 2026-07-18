import sys
from pathlib import Path
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from supabase import create_client

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

from auth import require_login


st.set_page_config(
    page_title="Morgenmadsplan",
    layout="wide"
)

require_login()

st.subheader("Antal personer til morgenmad")

load_dotenv()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# -------------------------
# Vælg periode
# -------------------------

check_dato_start = date.today()

antal_dage = st.selectbox(
    "Vis morgenmad de næste dage",
    [3, 5, 7, 9, 14],
    index=0
)

check_dato_slut = (
    check_dato_start
    + timedelta(days=antal_dage)
)

# -------------------------
# Hent bookingdata
# -------------------------

result = (
    supabase
    .table("hk_dtb")
    .select(
        "checkin_date, "
        "checkout_date, "
        "numb_guests, "
        "morgenmad, "
        "web"
    )
    .neq("web", "cansl")
    .execute()
)

df = pd.DataFrame(result.data or [])

if df.empty:
    st.info("Ingen bookinger fundet")
    st.stop()

# -------------------------
# Klargør bookingdata
# -------------------------

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

# -------------------------
# Beregn morgenmad pr. dato
# -------------------------

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
        "Morgenmadsgæster": int(antal),
    })

breakfast_df = pd.DataFrame(
    breakfast_rows
)

# -------------------------
# Hent ekstra gæster og assistance
# -------------------------

notes_result = (
    supabase
    .table("breakfast_notes")
    .select(
        "dato, ekstra_gæster, assistance"
    )
    .execute()
)

notes_df = pd.DataFrame(
    notes_result.data or []
)

if not notes_df.empty:
    notes_df["dato"] = pd.to_datetime(
        notes_df["dato"],
        errors="coerce"
    ).dt.date

    breakfast_df = breakfast_df.merge(
        notes_df,
        left_on="Dato",
        right_on="dato",
        how="left"
    )

    breakfast_df = breakfast_df.drop(
        columns=["dato"]
    )

else:
    breakfast_df["ekstra_gæster"] = 0
    breakfast_df["assistance"] = ""

# -------------------------
# Udfyld tomme værdier
# -------------------------

breakfast_df["ekstra_gæster"] = (
    pd.to_numeric(
        breakfast_df["ekstra_gæster"],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)

breakfast_df["assistance"] = (
    breakfast_df["assistance"]
    .fillna("")
    .astype(str)
)

breakfast_df["I alt"] = (
    breakfast_df["Morgenmadsgæster"]
    + breakfast_df["ekstra_gæster"]
)

# Pæne kolonnenavne
breakfast_df = breakfast_df.rename(
    columns={
        "ekstra_gæster": "Ekstra gæster",
        "assistance": "Assistance",
    }
)

# Fast kolonnerækkefølge
breakfast_df = breakfast_df[
    [
        "Dato",
        "Morgenmadsgæster",
        "Ekstra gæster",
        "I alt",
        "Assistance",
    ]
]

# -------------------------
# Vis oversigt
# -------------------------

st.subheader("Morgenmadsoversigt")

st.dataframe(
    breakfast_df,
    hide_index=True,
    use_container_width=True
)

# -------------------------
# Opret PDF
# -------------------------

buffer = BytesIO()

doc = SimpleDocTemplate(
    buffer
)

styles = getSampleStyleSheet()

elements = [
    Paragraph(
        "<b>Hammerknuden</b>",
        styles["Title"]
    ),
    Paragraph(
        "<b>Morgenmadsoversigt</b>",
        styles["Heading1"]
    ),
    Paragraph(
        (
            f"Periode: "
            f"{check_dato_start.strftime('%d-%m-%Y')} "
            f"til "
            f"{check_dato_slut.strftime('%d-%m-%Y')}"
        ),
        styles["Normal"]
    ),
    Spacer(1, 24),
]

table_data = [[
    "Dato",
    "Morgenmadsgæster",
    "Ekstra gæster",
    "I alt",
    "Assistance",
]]

for _, row in breakfast_df.iterrows():
    table_data.append([
        row["Dato"].strftime("%d-%m-%Y"),
        str(row["Morgenmadsgæster"]),
        str(row["Ekstra gæster"]),
        str(row["I alt"]),
        str(row["Assistance"]),
    ])

table = Table(
    table_data,
    repeatRows=1,
    colWidths=[
        80,
        110,
        90,
        55,
        130,
    ]
)

table.setStyle(
    TableStyle([
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.lightgrey
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.black
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),
        (
            "ALIGN",
            (1, 1),
            (3, -1),
            "CENTER"
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            6
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            6
        ),
    ])
)

elements.append(table)

doc.build(elements)

buffer.seek(0)

st.download_button(
    "📄 Download morgenmadsoversigt (PDF)",
    data=buffer,
    file_name="morgenmadsoversigt.pdf",
    mime="application/pdf"
)

