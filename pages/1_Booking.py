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
from config.prices import DEFAULT_PRICES
sys.path.append(str(Path(__file__).resolve().parents[1]))

st.set_page_config(page_title="Booking", layout="wide")
require_login()

# ✅ Init KUN hvis ikke findes
if "prices" not in st.session_state:
    st.session_state.prices = DEFAULT_PRICES.copy()

st.title("Reservations formular")

year = st.selectbox("booking år", ["2026", "2027"])
now = st.date_input("booking dato")
booking_number = st.text_input("booking nummer")

st.write(st.session_state.prices)
bruger = "Finn"
network = st.selectbox("vælg lokal eller web ", options=["local", "URL"])

now = st.date_input("booking dato", key='booking date')

booking_number = st.text_input("booking nummer ")


checkin_date = st.date_input("Checkin dato", key='start booking')
checkout_date = st.date_input("Checkout dato", key='slut booking')

single_room = st.checkbox("Enkeltværelse")

days = checkout_date - checkin_date
st.text("Skema viser ikke udchecksdagen da den er irelevant i forbindelse med reservation")
st.markdown(f"**Antal dage denne booking**  {days.days}")

if year == '2026':
    if bruger == "Finn" and network == "local":
        BASE_DIR = Path.cwd()
        file_path = BASE_DIR / "data" / "2026_BOOKING 10.xlsx"
        #file_name = "data/2026_BOOKING 10.xlsx"
    elif bruger == "Finn" and network == "URL":
        file_path = 'http://gofile.me/2UxBN/PTz0N4NfV'
    else:
        st.text("file nor found")

df = pd.read_excel(file_path, sheet_name='book_simp')
new_data = df[(df['dato'].dt.date >= checkin_date) & (df['dato'].dt.date < checkout_date)]
unique_values = new_data["1-I"].unique()

counts_1 = new_data["1-I"].value_counts()
counts_2 = new_data["2-I"].value_counts()
counts_3 = new_data["3-I"].value_counts()
counts_4 = new_data["4-I"].value_counts()
counts_5 = new_data["5-I"].value_counts()
# chat
print(f"Counts 1: {counts_1}")
print(f"Counts 2: {counts_2}")
print(f"Counts 3: {counts_3}")
print(f"Counts 4: {counts_4}")
print(f"Counts 5: {counts_5}")

room_1 = (counts_1.get("va", 0))
room_2 = (counts_2.get("va", 0))
room_3 = (counts_3.get("va", 0))
room_4 = (counts_4.get("va", 0))
room_5 = (counts_5.get("va", 0))
# chat
print(f"Room 1: {room_1}")
print(f"Room 2: {room_2}")
print(f"Room 3: {room_3}")
print(f"Room 4: {room_4}")
print(f"Room 5: {room_5}")

if room_1 == days.days:
    ledige_rum_1 = 1
else:
    ledige_rum_1 = 0
if room_2 == days.days:
    ledige_rum_2 = 1
else:
    ledige_rum_2 = 0
if room_3 == days.days:
    ledige_rum_3 = 1
else:
    ledige_rum_3 = 0
if room_4 == days.days:
    ledige_rum_4 = 1
else:
    ledige_rum_4 = 0
if room_5 == days.days:
    ledige_rum_5 = 1
else:
    ledige_rum_5 = 0
ledige_rum = ledige_rum_1 + ledige_rum_2 + ledige_rum_3 + ledige_rum_4 + ledige_rum_5
print(unique_values)
st.markdown(f"**Antal ledige rum**  {ledige_rum}")  # "ledige} rum ", {ledige_rum})
print(df)

def highlight_cells(val):

    color = 'background-color: #66FF66' if val == 'va' else ''  # Grøn for 'va'
    return color
styled_data = new_data[['dato', '1-I', '2-I', '3-I', '4-I', '5-I']].style.map(highlight_cells)
st.dataframe(styled_data)

if single_room:
    num_guests = st.number_input("max en gæst", value=1, step=0)
else:
    num_guests = st.number_input("Antal gæster", value=2, step=1)

num_rooms = st.number_input("Antal rum", value=1, step=1)
web = st.selectbox("booking via web bc eller FM folkemøde ( ikke mulighed for enk rum)", options=["web", "bc", "FM"])
ankomst = st.text_input("Angiv ankomsts tidspunkt hvis haves ")
seng = st.text_input(" type seng Doob, Sing, OPCH, OPIN ")
if web == "web":
    rabat = st.number_input(" rabat i procent ", value=10, step=1)
    procent = rabat / 100
if web == "FM":
    FM_add = st.number_input(" Folkemøde tillæg i procent ", value=0, step=5)
    procent = FM_add / 100
else:
    procent = 0

if year == '2026':
    if single_room and (web == 'bc' or web == 'web'):
        high_season_price = st.session_state.prices["Sing-Room-HS-26"] #975  #2026 975
        low_season_price = st.session_state.prices["Sing-Room-LS-26"] #2026 850
        single_room = "Y"
        print(low_season_price)
        print(high_season_price)
    else:
        low_season_price = st.session_state.prices["Dobb-Room-LS-26"] #950
        high_season_price = st.session_state.prices["Dobb-Room-HS-26"] #1075
        if web == "FM":
            high_season_price = st.session_state.prices["Dobb-Room-HS-26"] #1075  #2026 1075
            low_season_price = st.session_state.prices["Dobb-Room-HS-26"] #1075   #2026 1075
            single_room = "N"
            print(low_season_price)
            print(high_season_price)
        else:
            high_season_price = st.session_state.prices["Dobb-Room-HS-26"] #1075   #2026 1075
            low_season_price = st.session_state.prices["Dobb-Room-LS-26"] #950     #2026 950
            single_room = "N"
            print(low_season_price)
            print(high_season_price)

    st.markdown(f"**High season** {high_season_price}")
    st.markdown(f"**Low season** {low_season_price}")
    st.markdown('year 2026')