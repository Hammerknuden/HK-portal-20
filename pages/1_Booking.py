import streamlit as st
from auth import require_login
import pandas as pd
import openpyxl
import requests
from datetime import datetime, date
from pathlib import Path
import numpy as np
#from confirmation_email import (
 #   admin_email,
 #   send_danish_confirmation_email,
 #   send_english_confirmation_email,
 #   send_german_confirmation_email
#)
#from data_email import (add_data, send_data_email)
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
st.set_page_config(page_title="Booking", layout="wide")
require_login()

st.title("Reservations formular")

year = st.selectbox("booking år", ["2026", "2027"])
now = st.date_input("booking dato")
booking_number = st.text_input("booking nummer")
bruger = "Finn"  #st.selectbox("bruger computer ", options=["Finn", "Naja"])
network = st.selectbox("vælg lokal eller web ", options=["local", "URL"])

now = st.date_input("booking dato")

booking_number = st.text_input("booking nummer ")


checkin_date = st.date_input("Checkin dato")
checkout_date = st.date_input("Checkout dato")

single_room = st.checkbox("Enkeltværelse")

days = checkout_date - checkin_date
st.text("Skema viser ikke udchecksdagen da den er irelevant i forbindelse med reservation")
st.markdown(f"**Antal dage denne booking**  {days.days}")
