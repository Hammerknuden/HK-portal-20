import streamlit as st
from auth import require_login
import pandas as pd
from pathlib import Path
import sys
from datetime import timedelta
sys.path.append(str(Path(__file__).resolve().parents[1]))

st.set_page_config(page_title="Ankomster", layout="wide")
require_login()

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
st.subheader("Rengøring ")
# Date inputs fra Streamlit
year = st.selectbox("booking år", ["2026", "2027"])
plan_dato_start = st.date_input("Start dato")
antal_dage = st.number_input("Antal dage", min_value=1, value=5)
plan_dato_slut = plan_dato_start + timedelta(days=antal_dage)
clean_plan = st.button("planlæg regørring ")

if clean_plan and year == "2026":
    # Load Excel
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / "2026_BOOKING 10.xlsx"
    df = pd.read_excel(file_path, sheet_name="rengøring")

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
    df = pd.read_excel(file_path, sheet_name="rengøring")

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