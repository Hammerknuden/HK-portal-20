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
year = st.selectbox("booking år", ["2026", "2027"])
check_dato_start = st.date_input("Start dato")
antal_dage = st.number_input("Antal dage", min_value=1, value=3)
check_dato_slut = check_dato_start + timedelta(days=antal_dage)
check_for_ankomst = st.button(" check ankomster")
#check_dato_slut = st.date_input("Slut dato")


if check_for_ankomst and year == "2026":
    # Load Excel
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / "2026_BOOKING 10.xlsx"
    df = pd.read_excel(file_path, sheet_name="ankomster")

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
        (df['dato'].dt.date >= check_dato_start) &
        (df['dato'].dt.date <= check_dato_slut)
        ]

        # Vis resultat
    st.write("Ankomst oversigt:")
    st.dataframe(filtreret_df)

    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / '2026_BOOKING 10.xlsx'

    #file_name = "2026_BOOKING 10.xlsx"
    df = pd.read_excel(file_path, sheet_name="ankomst navn")

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
        (df['dato'].dt.date >= check_dato_start) &
        (df['dato'].dt.date <= check_dato_slut)
        ]


    # Vis resultat
    st.write("Navne på ankomster:")
    st.dataframe(filtreret_df)

if check_for_ankomst and year == 2027:
    
    # Load Excel
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / '2027_BOOKING 10.xlsx'
    #file_name = "2027_BOOKING 10.xlsx"
    df = pd.read_excel(file_path, sheet_name="ankomster")

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
            (df['dato'].dt.date >= check_dato_start) &
            (df['dato'].dt.date <= check_dato_slut)
            ]

        # Vis resultat
        st.write("Ankomst oversigt:")
        st.dataframe(filtreret_df)

        BASE_DIR = Path.cwd()
        file_path = BASE_DIR / "data" / '2027_BOOKING 10.xlsx'
        #file_name = "2026_BOOKING 10.xlsx"
        df = pd.read_excel(file_path, sheet_name="ankomst navn")

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
                (df['dato'].dt.date >= check_dato_start) &
                (df['dato'].dt.date <= check_dato_slut)
                ]

            # Vis resultat
            st.write("Navne på ankomster:")
            st.dataframe(filtreret_df)
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
    [3, 5],
    index=0
)

check_dato_slut = check_dato_start + timedelta(days=antal_dage)

# Hent data fra Supabase
result = (
    supabase.table("hk_dtb")
    .select(
        "booking_number, name, checkin_date, bed, known, room_number"
    )
    .gte("checkin_date", str(check_dato_start))
    .lte("checkin_date", str(check_dato_slut))
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
                "booking_number",
                "name",
                "checkin_date",
                "bed",
                "known",
                "room_number",
            ]
        ],
        use_container_width=True,
    )
else:
    st.info("Ingen ankomster i perioden.")
