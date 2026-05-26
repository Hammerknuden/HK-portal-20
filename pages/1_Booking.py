import streamlit as st
from auth import require_login
import pandas as pd
import openpyxl
import requests
from datetime import datetime, date
import sys
from pathlib import Path
import numpy as np
from config.confirmation_email import (admin_email,
    send_danish_confirmation_email,
    send_english_confirmation_email,
    send_german_confirmation_email)
from config.data_email import add_data, send_data_email
from common import init_session
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
from config.prices import DEFAULT_PRICES
sys.path.append(str(Path(__file__).resolve().parents[1]))

st.set_page_config(page_title="Booking", layout="wide")


def init_session():

    defaults = {
        "reservation_number": "",
        "reservation_name": "",
        #"reservation_date": date.today(),
        "reservation_checkin_date": date.today(),
        "reservation_checkout_date": date.today()
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

#byt evt init og login


require_login()
init_session()

# ✅ Init KUN hvis ikke findes


if "prices" not in st.session_state:
    st.session_state.prices = DEFAULT_PRICES.copy()

st.title("Reservations formular")

year = st.selectbox("booking år", ["2026", "2027"])

bruger = "Finn"
network = st.selectbox("vælg lokal eller web ", options=["local", "URL"])

now = st.date_input("booking dato")#, key='reservation_date')

booking_number = st.text_input("booking nummer ", key="reservation_number")
st.write(st.session_state["reservation_number"])
col1, col2 = st.columns(2)
with col1:
    checkin_date = st.date_input("Checkin dato", key="reservation_checkin_date"
    )

with col2:
    checkout_date = st.date_input("Checkout dato", key="reservation_checkout_date"
    )

single_room = st.checkbox("Enkeltværelse")

if checkin_date and checkout_date:
    days = (checkout_date - checkin_date).days
else:
    days = 0

st.markdown(f"**Antal dage denne booking** {days}")

st.text("Skema viser ikke udchecksdagen da den er irelevant i forbindelse med reservation")

if year == '2026':
    if bruger == "Finn" and network == "local":
        BASE_DIR = Path.cwd()
        file_path = BASE_DIR / "data" / "2026_BOOKING 10.xlsx"
        #file_name = "data/2026_BOOKING 10.xlsx"
    elif bruger == "Finn" and network == "URL":
        file_path = 'http://gofile.me/2UxBN/PTz0N4NfV'
    else:
        st.text("file nor found")

if year == '2027':
    if bruger == "Finn" and network == "local":
        BASE_DIR = Path.cwd()
        file_path = BASE_DIR / "data" / "2027_BOOKING 10.xlsx"
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

if room_1 == days: #days:
    ledige_rum_1 = 1
else:
    ledige_rum_1 = 0
if room_2 == days: #.days:
    ledige_rum_2 = 1
else:
    ledige_rum_2 = 0
if room_3 == days:#.days:
    ledige_rum_3 = 1
else:
    ledige_rum_3 = 0
if room_4 == days:#.days:
    ledige_rum_4 = 1
else:
    ledige_rum_4 = 0
if room_5 == days:#.days:
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


styled_data = new_data[['dato', 'week_event', '1-I', '2-I', '3-I', '4-I', '5-I']].style.map(highlight_cells)
st.dataframe(styled_data)
col1, col2, = st.columns(2)
with col1:
    num_rooms = st.number_input("Antal rum", value=1, step=1)
with col2:
    if single_room:
        num_guests = st.number_input("max en gæst", value=1, step=0)
    else:
        num_guests = st.number_input("Antal gæster", value=2, step=1)


col1, col2, col3 = st.columns(3)
with col1:
    web = st.selectbox("booking via web bc eller FM folkemøde ( ikke mulighed for enk rum)", options=["web", "bc", "FM"])
with col2:
    ankomst = st.text_input("Angiv ankomsts tidspunkt hvis haves, kan efterlades blankt ")
with col3:
    seng = st.text_input(" type af seng der ønskes hvis det vides f.eks. Dobb, Sing, OPred, OPIN ")
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
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**High season** {high_season_price} kr")
        with col2:
            st.markdown(f"**Low season** {low_season_price} kr")
    st.markdown('year 2026')

if year == '2027':
    if single_room and (web == 'bc' or web == 'web'):
        high_season_price = st.session_state.prices["Sing-Room-HS-27"]
        low_season_price = st.session_state.prices["Sing-Room-LS-27"]
        single_room = "Y"
        print(low_season_price)
        print(high_season_price)
    else:
        low_season_price = st.session_state.prices["Dobb-Room-LS-27"]
        high_season_price = st.session_state.prices["Dobb-Room-HS-27"]
        if web == "FM":
            high_season_price = st.session_state.prices["Dobb-Room-HS-27"]
            low_season_price = st.session_state.prices["Dobb-Room-HS-27"]
            single_room = "N"
            print(low_season_price)
            print(high_season_price)
        else:
            high_season_price = st.session_state.prices["Dobb-Room-HS-27"]
            low_season_price = st.session_state.prices["Dobb-Room-LS-27"]
            single_room = "N"
            print(low_season_price)
            print(high_season_price)
            st.markdown('year 2027')
        col1, col2, = st.columns(2)
        with col1:
            st.markdown(f"**High season** {high_season_price} kr")
        with col2:
            st.markdown(f"**Low season** {low_season_price} kr")

if year == '2026':
    bf_price = st.session_state.prices["Breakfirst-26"]  #100
if year == '2027':
    bf_price = st.session_state.prices["Breakfirst-27"] #100

Sprog = st.selectbox("Sprog - email confirmation dk uk D", options=["DK", "UK", "D"])

breakfast = st.checkbox("Morgenmad")
breakfast_alt = st.checkbox("begrænset morgenmad bestilles direkte ved ankomst mod beregning  ")
breakfast_rabat = st.checkbox("Der beregnes ikke rabat på morgenmad")

if breakfast:
    br_f = int(bf_price * int(num_guests) * int(days))#.days))
    BF = "Y"
    if Sprog == "DK":
        text_bf = "Morgenmad er inkluderet i prisen"
    if Sprog == "UK":
        text_bf = "Breakfast is included "
    if Sprog == "D":
        text_bf = "Das Frühstück ist im Preis inbegriffen"
else:
    br_f = 0
    BF = "N"
    if Sprog == "DK":
        text_bf = "Morgenmad er ikke inkluderet i prisen"
    if Sprog == "UK":
        text_bf = " Breakfast is not included "
    if Sprog == "D":
        text_bf = "Frühstück ist nicht mit enthalten"

if breakfast and breakfast_alt:
    br_f = 0
    BF = "A"
    if Sprog == "DK":
        text_bf = "Morgenmad kan tilkøbes alle dage undtagen Søndag"
    if Sprog == "UK":
        text_bf = "Breakfast can be purchased every day except Sunday. "
    if Sprog == "D":
        text_bf = "Frühstück kann täglich außer sonntags erworben werden."
if year == '2026':
    high_season_start = datetime.strptime("28-06-26", _format := "%d-%m-%y").date()
    high_season_end = datetime.strptime("15-08-26", _format := "%d-%m-%y").date()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Højsæson starter** {high_season_start}")
    with col2:
        st.markdown(f"**Højsæson slutter** {high_season_end}")
if year == '2027':
    high_season_start = datetime.strptime("22-06-27", _format := "%d-%m-%y").date()
    high_season_end = datetime.strptime("17-08-27", _format := "%d-%m-%y").date()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Højsæson starter** {high_season_start}")
    with col2:
        st.markdown(f"**Højsæson slutter** {high_season_end}")

days = checkout_date - checkin_date

high_season_days = high_season_end - high_season_start
high_booking = (checkin_date >= high_season_start) and (checkout_date <= high_season_end)
low_booking = (((checkin_date <= high_season_start) and (checkout_date < high_season_start)) or
               (checkin_date > high_season_end))
mixbooking_early = (checkin_date < high_season_start) and (checkout_date > high_season_start)
mixbooking_end = (checkout_date > high_season_end) and (high_season_start < checkin_date) and (checkin_date <
                                                                                                   high_season_end)

high_season_days = high_season_end - high_season_start
mixearly = checkout_date - high_season_start
mixearly_b = high_season_start - checkin_date
mixend = high_season_end - checkin_date
mixend_b = checkout_date - high_season_end

if web == "FM":
    pris = (high_season_price * int(days.days)) * int(num_rooms)
else:
    if high_booking:
        pris = (high_season_price * int(days.days)) * int(num_rooms)
    if low_booking:
        pris = (low_season_price * int(days.days)) * int(num_rooms)
    if mixbooking_early:
        pris = (((int(mixearly.days) * high_season_price) + (int(mixearly_b.days) * low_season_price)) * int(num_rooms))
    if mixbooking_end:
        pris = (high_season_price * (int(mixend.days)) + (int(mixend_b.days) * low_season_price)) * int(num_rooms)

st.markdown(f"**Værelsespris** {pris:.2f} kr".replace(".", ","))
print(pris)


def dkk(value):
    return f"{value:.2f}".replace(".", ",")


prismed = float(pris + br_f)
formatted_prismed = dkk(prismed)
st.markdown(f"**Pris incl breakfast** {formatted_prismed} kr")
print(prismed)

if breakfast_rabat and web == "web":

    formatted_prismed = (f"{prismed:.2f}".replace(".",","))
    rabat_a = (int(rabat) / 100)
    rabat_rm = pris * rabat_a
    rabat_t = rabat_rm
    formatted_rabat_t = f"{rabat_t:.2f}"
    st.markdown(f"**Rabat** {formatted_rabat_t} kr".replace(".",","))
    pristotal = prismed - rabat_t
    formatted_pristotal = f"{pristotal:.2f}".replace(".",",")

elif web == "web":
    formatted_prismed = (f"{prismed:.2f}".replace(".",","))
    rabat_a = (int(rabat) / 100)
    rabat_mm = br_f * rabat_a
    rabat_rm = pris * rabat_a
    rabat_t = rabat_mm + rabat_rm
    formatted_rabat_t = f"{rabat_t:.2f}"
    st.markdown(f"**Rabat** {formatted_rabat_t}kr".replace(".",","))
    pristotal = prismed - rabat_t
    formatted_pristotal = f"{pristotal:.2f}".replace(".",",")
    print("formatted_prismed:", formatted_prismed)
    print("type:", type(formatted_prismed))
elif web == "FM":
    formatted_prismed = f"{prismed:.2f}".replace(".",",")
    pris_add_a = (int(FM_add) / 100)
    pris_add_t = (prismed + br_f) * pris_add_a
    formatted_pris_add_t = f"{pris_add_t:.2f}"
    st.markdown(f"**Tiilæg** {formatted_pris_add_t} kr".replace(".",","))
    pristotal = prismed + pris_add_t
    formatted_pristotal = f"{pristotal:.2f}".replace(".",",")
else:
    rabat_a = 0
    formatted_prismed = f"{prismed:.2f}".replace(".",",")
    formatted_pristotal = formatted_prismed

    print(formatted_pristotal)
st.markdown(f"**Den totale pris** {formatted_pristotal}kr".replace(".",","))

st.subheader("Kontakt information")

name = st.text_input("Navn", key='reservation_name')
fam_name = st.text_input("Efternavn (kun til søgning ellers blank)  ")
telefon = st.text_input(" Kontakt telefon")
email_address = st.text_input("email")

nationalitet = st.text_input("Nationalitet - DK S N NL etc")

known_guest = st.checkbox("check for known person")
if known_guest and 'local':
    BASE_DIR = Path.cwd()
    file_path = BASE_DIR / "data" / 'Database hammerknuden.xlsx'
    df = pd.read_excel(file_path, sheet_name='Dtb', dtype={'familienavn': str})
    search_value = fam_name
    pd.set_option("display.max_columns", None, )
    rows1 = df[df['Familienavn'] == search_value]
    df = pd.read_excel(file_path, sheet_name='Dtb', dtype={'telefon': str})
    search_value = telefon
    pd.set_option("display.max_columns", None,)
    rows2 = df[df['telefon'] == search_value]
    df = pd.read_excel(file_path, sheet_name="Dtb", dtype={'Email': str})
    search_value = email_address
    pd.set_option("display.max_columns", None)
    rows3 = df[df['Email'] == search_value]

    if fam_name:
        st.dataframe(rows1)
    if telefon:
        st.dataframe(rows2)
        known = "Y"
    elif email_address:
        st.dataframe(rows3)
        known = "YY"
else:
    known = "N"

spouse = st.text_input("Spouce  ")
comments = st.text_input("yderligere info til Dtb  ")

col1, col2, col3 = st.columns(3)
with col1:
    st.text("Vælg tekst til kunde mail: ")
    text_ank = st.checkbox("tekst vedr. ankomsttid  ")
    if Sprog == 'DK':
        if text_ank:
            text_ank = ("Da vores reception ikke er bemandet H24, bedes I informere om ankomsts tidspunkt for nøgle "
                        "udlevering")
        else:
            text_ank = " - "

    if Sprog == 'UK':
        if text_ank:
            text_ank = (
                "Since the reception isn´t operative on a 24 hours basis, please inform us on your arrival time, "
                "to obtain room key")
        else:
            text_ank = " - "

    if Sprog == 'D':
        if text_ank:
            text_ank = ("Da die Rezeption nicht rund um die Uhr besetzt ist, informieren Sie uns bitte über Ihre "
                        "Ankunftszeit,um Zimmerschlüssel erhalten.")
        else:
            text_ank = " - "
with col2:
    st.text("Vælg tekst til kunde vedr. valg af seng ")
    text_bed = st.checkbox("tekst vedr. valg af seng  ")
    if Sprog == 'DK':
        if text_bed:
            text_bed = "Ønske om dobbelt eller enkelseng kan sendes på mail før ankomst"
        else:
            text_bed = " - "

    if Sprog == 'UK':
        if text_bed:
            text_bed = "Requests for a double or single bed can be sent by email before arrival"
        else:
            text_bed = " - "

    if Sprog == 'D':
        if text_bed:
            text_bed = "Anfragen für ein Doppel- oder Einzelbett können vor der Anreise per E-Mail gesendet werden"
        else:
            text_bed = " - "
with col3:
    st.text("Vælg tekst til kunde vedr. valg af seng")
    text_free = st.checkbox("Skriv ekstra tekst - husk sprog  ")
    if text_free:
        text_free = st.text_input("skriv add tekst ")
        print(text_free)
    else:
        text_free = " - "
if web == "web" and Sprog == "DK":
    text_web = "Rabat i forbindelse med opholdet er"
    justering = rabat_t
    formatted_justering = f"{justering:.2f}".replace(".", ",")
    print(formatted_justering)
elif web == "FM" and Sprog == "DK":
    text_web = "Evt tillæg i forbindelse med denne booking"
    justering = pris_add_t
    formatted_justering = f"{justering:.2f}".replace(".", ",")
    print(formatted_justering)
    depositum = pristotal * 0.5
    st.markdown(f"** depositum 50% ** {depositum:.2f}")
    text_free = (f"Depositum {depositum:.2f}  kr skal indbetales ved kontooverførsel eller mobilpay 133565 "
                 "inden 25 feb.2026 ")
elif web == "web" and Sprog == "UK":
    text_web = "Any discount in connection with this booking is."
    justering = rabat_t
    formatted_justering = f"{justering:.2f}".replace(".", ",")
elif web == "web" and Sprog == "D":
    text_web = f"Der Rabatt im Zusammenhang mit dieser Buchung beträgt."
    justering = rabat_t
    formatted_justering = f"{justering:.2f}".replace(".", ",")
else:
    text_web = " - "
    formatted_justering = " - "
guest_email = st.checkbox("send mail direkte til gæst  ")
if guest_email:
    to_addr = [email_address, admin_email]
else:
    to_addr = [admin_email]
#to_addr = "finnjorg@mail.dk"
confirmation_password = st.text_input("Admin kodeord")
booking_submitted = st.button("Send booking mail")


if Sprog == "DK" and booking_submitted:
    send_danish_confirmation_email(to_addr, confirmation_password, name, num_rooms, num_guests, booking_number,
                                   checkin_date, checkout_date, text_bf, formatted_prismed, text_web, formatted_justering,
                                   formatted_pristotal, text_ank, text_bed, text_free, email_address, telefon)
    st.markdown('dansk email er sendt')
elif Sprog == "UK" and booking_submitted:
    send_english_confirmation_email(to_addr, confirmation_password, name, num_rooms, num_guests, booking_number,
                                    checkin_date, checkout_date, text_bf, formatted_prismed, text_web, formatted_justering,
                                    formatted_pristotal, text_ank, text_bed, text_free, email_address, telefon)
    st.markdown('engelsk email er sendt')
elif Sprog == "D" and booking_submitted:
    send_german_confirmation_email(to_addr, confirmation_password, name, num_rooms, num_guests, booking_number,
                                   checkin_date, checkout_date, text_bf, formatted_prismed, text_web, formatted_justering,
                                   formatted_pristotal, text_ank, text_bed, text_free, email_address, telefon)
    st.markdown('tysk email er sendt')
else:
    st.markdown('Booking mail er ikke sendt ')

send_data = st.button("send data fil")
#send_data = st.checkbox("Data - mail til admin")
additional_mail = st.checkbox("fleksibel mail address  ")
if send_data:
    to_addr_1 = admin_email
if send_data and additional_mail:
    add_mail = st.text_input("enter additional mail")
    to_addr_1 = {admin_email, add_mail}

if send_data: #and booking_submitted:

    excel_file = add_data(year=year, booking_number=booking_number, name=name, checkin_date=checkin_date,
                          checkout_date=checkout_date, now=now, nationalitet=nationalitet, web=web,
                          ankomst=ankomst, seng=seng, rabat_a=rabat_a, num_rooms=num_rooms,
                          num_guests=num_guests, email_address=email_address, telefon=telefon,
                          spouse=spouse, single_room=single_room, BF=BF,
                          formatted_pristotal=formatted_pristotal, known=known, comments=comments)

    send_data_email(to_addr_1, confirmation_password, booking_number, name,
                    checkin_date, checkout_date, num_rooms, now,
                    nationalitet, web, ankomst, seng, procent,
                    num_guests, email_address, telefon,
                    formatted_pristotal, excel_file)

    st.markdown("data mail sendt")
    print(type(excel_file))

    st.markdown("data mail ikke sendt ")


def save_reservation():

    booking_number = st.session_state.get("reservation_number", "")
    name = st.session_state.get("reservation_name", "")
    checkin_date = st.session_state.get("reservation_checkin_date", "")
    checkout_date = st.session_state.get("reservation_checkout_date", "")

    st.write(f"Gemmer booking {booking_number} for {name}")
    st.write(f"Fra {checkin_date} til {checkout_date}")


if booking_number:
    save_reservation()
    st.success("Booking gemt")


#st.write("AFSENDER STATE")
#st.write(st.session_state)
#st.session_state












