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

# Beregn antal nætter
df["checkin_date"] = pd.to_datetime(df["checkin_date"])
df["checkout_date"] = pd.to_datetime(df["checkout_date"])

df["nights"] = (
    df["checkout_date"] - df["checkin_date"]
).dt.days

df["overnatninger"] = df["numb_guests"] * df["nights"]

# Statistik pr. land
stats = (
    df.groupby("nation")
      .agg(
          ankomster=("numb_guests", "sum"),
          overnatninger=("overnatninger", "sum")
      )
      .reset_index()
      .sort_values("overnatninger", ascending=False)
)
st.write(stats)
sortering = {
    "DK": 1,
    "D": 2,
    "S": 3,
    "N": 4,
    "NL": 5,
    "ANDRE": 6
}

rapport["sort"] = rapport["gruppe"].map(sortering)
rapport = rapport.sort_values("sort").drop(columns="sort")

