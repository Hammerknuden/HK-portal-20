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
    result = supabase.table("hk_dtb").select("*").limit(1).execute()

    st.success("Forbindelse OK")
    st.write(result.data)

except Exception as e:
    st.error(f"Fejl: {e}")

df = pd.DataFrame(result.data)

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


