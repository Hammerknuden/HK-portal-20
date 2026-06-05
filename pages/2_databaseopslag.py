import streamlit as st
from auth import require_login
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv
from supabase import create_client

st.set_page_config(page_title="Database", layout="wide")
require_login()

load_dotenv()

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

try:
    result = supabase.table("historie").select("*").limit(1).execute()

    st.success("Forbindelse OK")
    #st.write(result.data)

except Exception as e:
    st.error(f"Fejl: {e}")

st.subheader("Database opslag 4 niveauer ")


familie_navn = st.text_input("Familienavn")
telefon = st.text_input("Telefon")
email = st.text_input("Email")
booking = st.text_input("Bookingnummer")
result = (
    supabase
    .table("historie")
    .select("*")
    .limit(1)
    .execute()
)

st.write(result.data)

if st.button("Søg"):

    if familie_navn:

        result = (
            supabase
            .table("historie")
            .select("*")
            .eq("Familienavn", familie_navn)
            .execute()
        )

        st.dataframe(pd.DataFrame(result.data))

    elif telefon:

        result = (
            supabase
            .table("historie")
            .select("*")
            .eq("telefon", telefon)
            .execute()
        )

        st.dataframe(pd.DataFrame(result.data))

    elif email:

        try:
            result = (
                supabase
                .table("historie")
                .select("*")
                .eq("Email", email)
                .execute()
            )

            st.write(result.data)
            st.dataframe(pd.DataFrame(result.data))

        except Exception as e:
            st.error(e)

    elif booking:

        result = (
            supabase
            .table("historie")
            .select("*")
            .eq("booking", int(booking))
            .execute()
        )

        st.dataframe(pd.DataFrame(result.data))

