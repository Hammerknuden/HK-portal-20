import streamlit as st
from auth import require_login
import pandas as pd
from pathlib import Path
st.set_page_config(page_title="Database", layout="wide")
require_login()

st.subheader("Database opslag 3 niveauer ")

familie_navn = st.text_input("family name")
telefon_nummer = st.text_input("telefon nummer med prefix")
email = st.text_input("email adresse ")
booking = st.text_input("booking nummer input")

database_check = st.button("check for known person")

if database_check:
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / 'Database hammerknuden.xlsx'
    df = pd.read_excel(file_path, sheet_name='Dtb', dtype={'familienavn': str})
    search_value = familie_navn
    pd.set_option("display.max_columns", None, )
    rows1 = df[df['Familienavn'] == search_value]
    df = pd.read_excel(file_path, sheet_name='Dtb', dtype={'telefon': str})
    search_value = telefon_nummer
    pd.set_option("display.max_columns", None,)
    rows2 = df[df['telefon'] == search_value]
    df = pd.read_excel(file_path, sheet_name="Dtb", dtype={'Email': str})
    search_value = email
    pd.set_option("display.max_columns", None)
    rows3 = df[df['Email'] == search_value]
    df = pd.read_excel(file_path, sheet_name="Dtb", dtype={'booking': str})
    search_value = booking
    pd.set_option("display.max_columns", None)
    rows4 = df[df['booking'] == search_value]

    if familie_navn:
        st.dataframe(rows1)
    if telefon_nummer:
        st.dataframe(rows2)
    if email:
        st.dataframe(rows3)
    elif booking:
        st.dataframe(rows4)
else:
    st.text(" not in Database")