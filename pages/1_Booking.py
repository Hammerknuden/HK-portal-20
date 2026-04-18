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
        file_name = "2026_BOOKING 10.xlsx"
    elif bruger == "Finn" and network == "URL":
        file_name = 'https://drive.usercontent.google.com/download?id=1MmfCR70RlDt3EIQ6eAIrf9OULon2OD_H&export=download&authuser=0&confirm=t&uuid=6021d22c-fa0f-45f4-9e61-2d99b296fcf1&at=AKSUxGMOeGtFihvrcKgymyTxiynP:1762359003826'
    else:
        st.text("file nor found")

df = pd.read_excel(file_name, sheet_name='book_simp')
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

