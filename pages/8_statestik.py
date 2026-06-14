import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
import plotly.express as px
from auth import require_login
from common import init_session
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


    st.success("Forbindelse OK")
    #st.write(result.data)

except Exception as e:
    st.error(f"Fejl: {e}")

#df = pd.DataFrame(result.data)

st.subheader("Rapport til Danmarks Statistik")
st.dataframe(rapport)