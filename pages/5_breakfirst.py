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
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

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

    notes = (
        supabase
        .table("breakfast_notes")
        .select("dato, ekstra_gæster, assistance")
        .execute()
    )

    notes_df = pd.DataFrame(notes.data or [])

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
        breakfast_df["ekstra_gaester"] = 0
        breakfast_df["assistance"] = ""

    breakfast_df["ekstra_gaester"] = (
        pd.to_numeric(
            breakfast_df["ekstra_gaester"],
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
            + breakfast_df["ekstra_gaester"]
    )

    breakfast_df = breakfast_df.rename(
        columns={
            "ekstra_gaester": "Ekstra gæster",
            "assistance": "Køkkenhjælp"
        }
    )

    st.subheader("Morgenmadsoversigt")

    st.dataframe(
        breakfast_df,
        hide_index=True,
        use_container_width=True
    )
    notes = (
        supabase
        .table("breakfast_notes")
        .select("dato, ekstra_gæster")
        .execute()
    )

    st.subheader("Morgenmadsoversigt")

    st.dataframe(
        breakfast_df,
        hide_index=True,
        use_container_width=True
    )
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "<b>Hammerknuden</b>",
            styles["Title"]
        )
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



        table_data = [["Dato", "Morgenmadsgæster"]]

        for _, row in breakfast_df.iterrows():
            table_data.append([
                row["Dato"].strftime("%d-%m-%Y"),
                str(row["Morgenmadsgæster"])
            ])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    st.download_button(
        "📄 Download morgenmadsoversigt (PDF)",
        data=buffer,
        file_name="morgenmadsoversigt.pdf",
        mime="application/pdf"
    )

else:
    st.info("Ingen bookinger fundet")

