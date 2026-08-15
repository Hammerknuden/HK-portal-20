import streamlit as st
from auth import require_login
import pandas as pd
from pathlib import Path
import sys
from datetime import date, timedelta
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(str(Path(__file__).resolve().parents[1]))

from common import exclude_cancelled_bookings
from modules.in_out_pdf import create_in_out_pdf

st.set_page_config(page_title="Ins and Outs", layout="wide")

require_login()

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
        "booking_number, navn, checkin_date, ankomst, bed, known, room_number, nation, enkelt, comments, web"
    )
    .gte("checkin_date", str(check_dato_start))
    .lte("checkin_date", str(check_dato_slut))
    .order("room_number")
    .execute()
)

df = exclude_cancelled_bookings(pd.DataFrame(result.data))
# ---------- ANKOMSTER ----------

df_ankomst = df.copy()

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
            "comments",
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
            "comments": "Kommentar",
        }
    )

    st.table(df_ankomst_print)

else:
    df_ankomst_print = pd.DataFrame()
    st.info("Ingen ankomster i perioden.")


# ---------- AFREJSER ----------

st.subheader("Periodens afrejser")

# Afrejser i den valgte periode
result = (
    supabase.table("hk_dtb")
    .select("booking_number, checkout_date, room_number, web")
    .gte("checkout_date", str(check_dato_start))
    .lte("checkout_date", str(check_dato_slut))
    .order("checkout_date")
    .execute()
)

# Alle kommende indcheck bruges til at finde næste booking pr. værelse
checkin_result = (
    supabase.table("hk_dtb")
    .select("booking_number, checkin_date, room_number, web")
    .gte("checkin_date", str(check_dato_start))
    .order("checkin_date")
    .execute()
)

df_afrejse = exclude_cancelled_bookings(pd.DataFrame(result.data))
df_checkin = exclude_cancelled_bookings(pd.DataFrame(checkin_result.data))

if not df_afrejse.empty:

    df_afrejse["checkout_date"] = pd.to_datetime(
        df_afrejse["checkout_date"],
        errors="coerce"
    )

    df_afrejse["room_number"] = pd.to_numeric(
        df_afrejse["room_number"],
        errors="coerce"
    )

    if not df_checkin.empty:

        df_checkin["checkin_date"] = pd.to_datetime(
            df_checkin["checkin_date"],
            errors="coerce"
        )

        df_checkin["room_number"] = pd.to_numeric(
            df_checkin["room_number"],
            errors="coerce"
        )

        def find_next_checkin(row):
            next_bookings = df_checkin[
                (df_checkin["room_number"] == row["room_number"])
                &
                (df_checkin["checkin_date"] >= row["checkout_date"])
            ]

            if next_bookings.empty:
                return pd.NaT

            return next_bookings["checkin_date"].min()

        df_afrejse["next_checkin"] = df_afrejse.apply(
            find_next_checkin,
            axis=1
        )

    else:
        df_afrejse["next_checkin"] = pd.NaT

    df_afrejse["checkout_date"] = (
        df_afrejse["checkout_date"].dt.date
    )

    df_afrejse["next_checkin"] = (
        df_afrejse["next_checkin"].dt.date
    )

    df_afrejse_print = df_afrejse[
        [
            "checkout_date",
            "room_number",
            "booking_number",
            "next_checkin",
        ]
    ].rename(
        columns={
            "checkout_date": "Udcheck",
            "room_number": "Værelse",
            "booking_number": "Booking nr.",
            "next_checkin": "Næste indcheck",
        }
    )

    st.table(df_afrejse_print)

else:
    df_afrejse_print = pd.DataFrame()
    st.info("Ingen udcheckninger i perioden.")

# ---------- DOWNLOAD-KNAP ----------

pdf_bytes = create_in_out_pdf(
    df_ankomst_print,
    df_afrejse_print,
    report_date=check_dato_start,
    period_start=check_dato_start,
    period_end=check_dato_slut,
    logo_path=Path(__file__).resolve().parents[1] / "logo2.jpg",
)

st.download_button(
    "📄 Download rapport",
    data=pdf_bytes,
    file_name=f"in_out_{check_dato_start.isoformat()}.pdf",
    mime="application/pdf",
)

