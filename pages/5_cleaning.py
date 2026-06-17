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

st.subheader("Rengøring ")
# Date inputs fra Streamlit
year = st.selectbox("booking år", ["2026", "2027"])
plan_dato_start = st.date_input("Start dato")
antal_dage = st.number_input("Antal dage", min_value=1, value=5)
plan_dato_slut = plan_dato_start + timedelta(days=antal_dage)
clean_plan = st.button("planlæg rengøring ")

if clean_plan and year == "2026":
    # Load Excel
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / "2026_BOOKING 10.xlsx"
    df = pd.read_excel(file_path, sheet_name="rengoering")

    # Rens kolonnenavne (vigtigt!)
    df.columns = df.columns.str.strip().str.lower()

    # Sikr at 'dato' findes
    if 'dato' not in df.columns:
        st.error(f"Kolonnen 'dato' findes ikke. Fundet kolonner: {df.columns.tolist()}")
    else:
        # Konverter til datetime
        df['dato'] = pd.to_datetime(df['dato'], errors='coerce')

        # Fjern rækker med ugyldige datoer
        df = df.dropna(subset=['dato'])

    # Filtrer på interval
    filtreret_df = df[
        (df['dato'].dt.date >= plan_dato_start) &
        (df['dato'].dt.date <= plan_dato_slut)
        ]

        # Vis resultat
    st.write("Room checkouts:")
    st.dataframe(filtreret_df)

if clean_plan and year == "2027":
    # Load Excel
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / "2027_BOOKING 10.xlsx"
    df = pd.read_excel(file_path, sheet_name="rengoering")

    # Rens kolonnenavne (vigtigt!)
    df.columns = df.columns.str.strip().str.lower()

    # Sikr at 'dato' findes
    if 'dato' not in df.columns:
        st.error(f"Kolonnen 'dato' findes ikke. Fundet kolonner: {df.columns.tolist()}")
    else:
        # Konverter til datetime
        df['dato'] = pd.to_datetime(df['dato'], errors='coerce')

        # Fjern rækker med ugyldige datoer
        df = df.dropna(subset=['dato'])

    # Filtrer på interval
    filtreret_df = df[
        (df['dato'].dt.date >= plan_dato_start) &
        (df['dato'].dt.date <= plan_dato_slut)
        ]

        # Vis resultat
    st.write("Room checkouts ")
    st.dataframe(filtreret_df)
else:
    st.text("Press button to plan ")

st.subheader("Dagens udcheckninger ")
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
    "Vis udcheckninger de næste dage",
    [3, 5, 7, 9, 14],
    index=0
)

check_dato_slut = check_dato_start + timedelta(days=antal_dage)

# Hent data fra Supabase
result = (
    supabase.table("hk_dtb")
    .select(
        "booking_number, checkout_date, room_number"
    )
    .gte("checkout_date", str(check_dato_start))
    .lte("checkout_date", str(check_dato_slut))
    .order("room_number")
    .execute()
)

df = pd.DataFrame(result.data)

# Sortér værelser 1-5
if not df.empty:
    df["room_number"] = pd.to_numeric(df["room_number"], errors="coerce")
    df = df.sort_values(["room_number", "checkout_date"])

    st.dataframe(
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
                "booking_number": "Booking nr."
            }
        ),
        use_container_width=True
    )

else:
    st.info("Ingen udcheckninger i perioden.")
