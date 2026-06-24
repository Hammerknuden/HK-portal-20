import streamlit as st
from auth import require_login
import pandas as pd
from pathlib import Path
import sys
from datetime import date, timedelta
sys.path.append(str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from supabase import create_client
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Inns and Outs", layout="wide")
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
# ---------- ANKOMSTER ----------

df_ankomst = pd.DataFrame(result.data)

st.subheader("Periodens ankomster")

if not df_ankomst.empty:
    df_ankomst["room_number"] = pd.to_numeric(df_ankomst["room_number"], errors="coerce")
    df_ankomst = df_ankomst.sort_values(["checkin_date", "room_number"])

    df_ankomst_print = df_ankomst[
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

    st.table(df_ankomst_print)

else:
    df_ankomst_print = pd.DataFrame()
    st.info("Ingen ankomster i perioden.")


# ---------- AFREJSER ----------

st.subheader("Periodens afrejser")

result = (
    supabase.table("hk_dtb")
    .select("booking_number, checkout_date, room_number, web")
    .gte("checkout_date", str(check_dato_start))
    .lte("checkout_date", str(check_dato_slut))
    .neq("web", "cansl")
    .order("checkout_date")
    .execute()
)

df_afrejse = pd.DataFrame(result.data)

if not df_afrejse.empty:
    df_afrejse["room_number"] = pd.to_numeric(df_afrejse["room_number"], errors="coerce")
    df_afrejse["checkout_date"] = pd.to_datetime(df_afrejse["checkout_date"])
    df_afrejse = df_afrejse.sort_values(["checkout_date", "room_number"])

    df_afrejse_print = df_afrejse[
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

    st.table(df_afrejse_print)

else:
    df_afrejse_print = pd.DataFrame()
    st.info("Ingen udcheckninger i perioden.")


# ---------- PDF-FUNKTION ----------

def lav_pdf(df_ankomst_print, df_afrejse_print):
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Ankomster og afrejser", styles["Heading1"]))
    story.append(Spacer(1, 12))

    if not df_ankomst_print.empty:
        story.append(Paragraph("Ankomster", styles["Heading2"]))

        data = [df_ankomst_print.columns.tolist()] + df_ankomst_print.astype(str).values.tolist()

        table = Table(data)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ]))

        story.append(table)
        story.append(Spacer(1, 18))

    if not df_afrejse_print.empty:
        story.append(Paragraph("Afrejser", styles["Heading2"]))

        data = [df_afrejse_print.columns.tolist()] + df_afrejse_print.astype(str).values.tolist()

        table = Table(data)
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ]))

        story.append(table)

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


# ---------- DOWNLOAD-KNAP ----------

pdf_bytes = lav_pdf(df_ankomst_print, df_afrejse_print)

st.download_button(
    "📄 Download rapport",
    data=pdf_bytes,
    file_name="rapport.pdf",
    mime="application/pdf",
)
# # Sortér værelser 1-5
# df = pd.DataFrame(result.data)
#
# if not df.empty:
#     df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")
#     df = df.sort_values(["checkin_date", "room_number"])
#
#     st.table(
#         df[
#             [
#                 "checkin_date",
#                 "booking_number",
#                 "room_number",
#                 "navn",
#                 "nation",
#                 "ankomst",
#                 "bed",
#                 "enkelt",
#                 "known",
#             ]
#         ].rename(
#             columns={
#                 "checkin_date": "Check-in",
#                 "booking_number": "Booking nr.",
#                 "room_number": "Værelse",
#                 "navn": "Navn",
#                 "nation": "Land",
#                 "ankomst": "Ankomst",
#                 "bed": "Seng",
#                 "enkelt": "Enkelt",
#                 "known": "Kendt",
#             }
#         )
#     )
# else:
#     st.info("Ingen ankomster i perioden.")
#
# st.subheader("Periodens afrejser")
# result = (
#     supabase.table("hk_dtb")
#     .select(
#         "booking_number, checkout_date, room_number, web"
#     )
#     .gte("checkout_date", str(check_dato_start))
#     .lte("checkout_date", str(check_dato_slut))
#     .neq("web", "cansl")
#     .order("checkout_date")
#     .execute()
# )
#
# df = pd.DataFrame(result.data)
#
# #st.write(df["web"].unique())
#
# # Sortér værelser 1-5
# df = pd.DataFrame(result.data)
#
# if not df.empty:
#     df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")
#     df["checkout_date"] = pd.to_datetime(df["checkout_date"])
#
#     df = df.sort_values(["checkout_date", "room_number"])
#
#     st.table(
#         df[
#             [
#                 "checkout_date",
#                 "room_number",
#                 "booking_number",
#             ]
#         ].rename(
#             columns={
#                 "checkout_date": "Udcheck",
#                 "room_number": "Værelse",
#                 "booking_number": "Booking nr.",
#             }
#         )
#     )
# else:
#     st.info("Ingen udcheckninger i perioden.")
#
#
# def lav_pdf(df_ankomst, df_afrejse):
#     buffer = BytesIO()
#
#     doc = SimpleDocTemplate(buffer)
#     styles = getSampleStyleSheet()
#     story = []
#
#     story.append(Paragraph("Ankomster og afrejser", styles["Heading1"]))
#     story.append(Spacer(1, 12))
#
#     if not df_ankomst.empty:
#         story.append(Paragraph("Ankomster", styles["Heading2"]))
#
#         data = [df_ankomst.columns.tolist()] + df_ankomst.astype(str).values.tolist()
#
#         table = Table(data)
#         table.setStyle(TableStyle([
#             ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
#             ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#         ]))
#
#         story.append(table)
#         story.append(Spacer(1, 18))
#
#     if not df_afrejse.empty:
#         story.append(Paragraph("Afrejser", styles["Heading2"]))
#
#         data = [df_afrejse.columns.tolist()] + df_afrejse.astype(str).values.tolist()
#
#         table = Table(data)
#         table.setStyle(TableStyle([
#             ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
#             ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
#         ]))
#
#         story.append(table)
#
#     doc.build(story)
#
#     pdf_bytes = buffer.getvalue()
#     buffer.close()
#
#     return pdf_bytes


#st.write( " for print brug Ctrl + P husk at lukke sidebar først")

