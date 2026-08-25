import streamlit as st
from auth import require_login
import pandas as pd
import openpyxl
import requests
from datetime import datetime, date, timedelta
import sys
from pathlib import Path
import numpy as np
from config.confirmation_email import (admin_email,
    send_danish_confirmation_email,
    send_english_confirmation_email,
    send_german_confirmation_email)
from config.data_email import add_data, send_data_email
from common import init_session, exclude_cancelled_bookings
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
import re
sys.path.append(str(Path(__file__).resolve().parents[1]))
import os
from dotenv import load_dotenv
from supabase import create_client


st.set_page_config(page_title="Booking", layout="wide")

load_dotenv()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.success("Forbindelse OK")


def normalize_phone(value):
    """Returner telefonnummer som cifre med landekode uden + eller 00."""
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 8:
        digits = f"45{digits}"
    return digits


def init_session():

    defaults = {
        "reservation_number": "",
        "reservation_name": "",
        "reservation_checkin_date": date.today(),
        "reservation_checkout_date": date.today()
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


require_login()
init_session()

st.title("Reservation")

year = st.selectbox("booking år", ["2026", "2027"])

try:
    booking_number_result = (
        supabase
        .table("hk_dtb")
        .select("booking_number")
        .eq("season", int(year))
        .execute()
    )
    booking_numbers = pd.to_numeric(
        pd.Series(
            [
                row.get("booking_number")
                for row in (booking_number_result.data or [])
            ],
            dtype="object",
        ),
        errors="coerce",
    ).dropna()

    if booking_numbers.empty:
        st.info(f"DB: Ingen bookingnumre fundet for sæson {year}")
    else:
        highest_booking_number = int(booking_numbers.max())
        st.info(
            f"DB: Højeste registrerede bookingnummer  {year} er "
            f"{highest_booking_number}"
        )
except Exception as error:
    st.warning(f"Kunne ikke hente højeste bookingnummer fra DB: {error}")

bruger = "Finn"
network = "local"
#network = st.selectbox("vælg lokal eller web ", options=["local", "URL"])
mode = st.radio(
    "Bookingfunktion",
    [
        "➕ Ny booking",
        "✏️ Rediger booking"
    ],
    horizontal=True,
    key="booking_mode",
    label_visibility="collapsed"
)
if mode == "✏️ Rediger booking":
    st.write("Rediger ud fra bookingnummer")

    with st.expander("Se alle bookinger"):
        result = (
            supabase
            .table("hk_dtb")
            .select("*")
            .eq("season", int(year))
            .execute()
        )

        df_supabase = pd.DataFrame(result.data or [])

        if "room_number" in df_supabase.columns:
            df_supabase["room_number"] = (
                pd.to_numeric(
                    df_supabase["room_number"],
                    errors="coerce"
                )
                .astype("Int64")
            )

        if "season" in df_supabase.columns:
            df_supabase["season"] = (
                pd.to_numeric(
                    df_supabase["season"],
                    errors="coerce"
                )
                .astype("Int64")
            )

        st.dataframe(
            df_supabase,
            use_container_width=True
        )

    if df_supabase.empty:
        st.info(f"Ingen bookinger fundet for {year}")
        st.stop()

    booking_lookup = df_supabase.set_index("id")

    booking_id = st.selectbox(
        "Vælg booking",
        options=df_supabase["id"].tolist(),
        format_func=lambda x: (
            f"Booking: {booking_lookup.loc[x, 'booking_number']} | "
            f"Værelse: {booking_lookup.loc[x, 'room_number']} | "
            f"{booking_lookup.loc[x, 'navn']}"
        ),
        key="edit_booking_select"
    )

    booking = booking_lookup.loc[booking_id]

    new_booking_number = st.text_input(
        "Bookingnummer",
        value=str(booking["booking_number"]),
        key=f"booking_number_{booking_id}"
    )

    current_family_name = booking.get("familie_navn", "")
    new_family_name = st.text_input(
        "Familienavn",
        value=(
            "" if pd.isna(current_family_name) else str(current_family_name)
        ),
        key=f"familie_navn_{booking_id}"
    )

    new_email = st.text_input(
        "email",
        value="" if pd.isna(booking["email"]) else str(booking["email"]),
        key=f"email_{booking_id}"
    )

    new_phone = st.text_input(
        "Telefon",
        value="" if pd.isna(booking["telefon"]) else str(booking["telefon"]),
        key=f"telefon_{booking_id}"
    )

    new_checkin = st.date_input(
        "Checkin",
        value=pd.to_datetime(
            booking["checkin_date"]
        ).date()
    )

    new_checkout = st.date_input(
        "Checkout",
        value=pd.to_datetime(
            booking["checkout_date"]
        ).date()
    )

    new_nation = st.text_input(
        "nation",
        value=str(booking["nation"])
    )

    new_web = st.text_input(
        "web",
        value=str(booking["web"])
    )
    new_ankomst = st.text_input(
        "ankomst",
        value=str(booking["ankomst"])

    )

    new_bed = st.text_input(
        "Bed",
        value=str(booking["bed"])
    )

    breakfast_options = ["Y", "N"]# udbyg evt med A for alternativ

    current_breakfast = (
        str(booking["morgenmad"]).strip().upper()
        if pd.notna(booking["morgenmad"])
        else "N"
    )

    if current_breakfast not in breakfast_options:
        current_breakfast = "N"

    new_breakfast = st.selectbox(
        "Morgenmad",
        breakfast_options,
        index=breakfast_options.index(current_breakfast)
    )

    new_room_number = st.text_input(
        "room_number",
        value=str(booking["room_number"])
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
                "Gem ændringer",
                key=f"save_booking_{booking_id}"
        ):
            try:
                result = (
                    supabase
                    .table("hk_dtb")
                    .update({
                        "booking_number": new_booking_number,
                        "familie_navn": new_family_name.strip(),
                        "email": new_email,
                        "telefon": new_phone,
                        "checkin_date": new_checkin.isoformat(),
                        "checkout_date": new_checkout.isoformat(),
                        "nation": new_nation,
                        "web": new_web,
                        "ankomst": new_ankomst,
                        "bed": new_bed,
                        "morgenmad": new_breakfast,
                        "room_number": new_room_number,
                        "season": year,
                    })
                    .eq("id", booking_id)
                    .execute()
                )

                st.success("Ændringer gemt")
                st.write(result.data)
                st.rerun()

            except Exception as e:
                st.error(f"Fejl ved opdatering: {e}")

    with col2:
        if st.button(
                "Slet booking",
                key=f"delete_booking_{booking_id}"
        ):
            try:
                supabase.table("hk_dtb").delete().eq(
                    "id",
                    booking_id
                ).execute()

                st.success("Booking slettet")
                st.rerun()

            except Exception as e:
                st.error(f"Fejl ved sletning: {e}")

    with col3:
        if st.button(
                "🔄 Byt værelse",
                key=f"open_swap_{booking_id}"
        ):
            st.session_state["swap_open"] = True
            st.session_state["swap_source_id"] = int(booking_id)

    # Skal stå efter de tre kolonner
    if (
            st.session_state.get("swap_open")
            and
            st.session_state.get("swap_source_id") == int(booking_id)
    ):
        st.divider()
        st.subheader("🔄 Byt værelse")

        st.info(
            f"Valgt booking: "
            f"{booking['booking_number']} | "
            f"Værelse {booking['room_number']}"
        )

        # Senere:
        # - vælg booking B
        # - vis begge bookinger
        # - kontroller med can_swap_blocks()
        # - separat knap: Udfør bytte

else:
    now = st.date_input("booking dato")#, key='reservation_date')

    booking_number = st.text_input("booking_nummer ", key="reservation_number")

    col1, col2 = st.columns(2)
    with col1:
        checkin_date = st.date_input("Checkin dato", key="reservation_checkin_date"
        )

    with col2:
        checkout_date = st.date_input("Checkout dato", key="reservation_checkout_date"
        )
    if checkout_date <= checkin_date:
        st.warning("Checkout skal være efter checkin.")
        st.stop()

    single_room = st.checkbox("Enkeltværelse")

    if checkin_date and checkout_date:
        days = (checkout_date - checkin_date).days
    else:
        days = 0

    st.markdown(f"**Antal dage denne booking** {days}")

    st.text("Skema viser ikke udchecksdagen da den er irelevant i forbindelse med reservation")

    # Det tidligere Excel-opslag for ledige værelser er midlertidigt
    # deaktiveret. Tilgængeligheden beregnes nu kun fra Supabase nedenfor.

    #year = season
    result = (
        supabase
        .table("hk_dtb")
        .select("*")
        .lt("checkin_date", checkout_date.isoformat())
        .gt("checkout_date", checkin_date.isoformat())
        .execute()
    )

    bookings = exclude_cancelled_bookings(pd.DataFrame(result.data or []))

    if "room_number" in bookings.columns:
        occupied_rooms = set(
            pd.to_numeric(bookings["room_number"], errors="coerce")
            .dropna()
            .astype(int)
        )
    else:
        occupied_rooms = set()

    all_rooms = {1, 2, 3, 4, 5}

    available_rooms = (
        all_rooms - occupied_rooms
    )

    ledige_rum = len(available_rooms)

    st.markdown(
        f"**Antal ledige rum:** {ledige_rum}"
    )

    st.metric("Supabase", ledige_rum)

    st.markdown("### Værelsesstatus dtb")

    rooms = [1, 2, 3, 4, 5]

    cols = st.columns(len(rooms))

    for i, room in enumerate(rooms):

        with cols[i]:

            st.write(f"**Værelse {room}**")

            if room in available_rooms:
                st.success("Ledigt")
            else:
                st.error("Optaget")

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
    elif web == "FM":
        FM_add = st.number_input(" Folkemøde tillæg i procent ", value=0, step=5)
        procent = FM_add / 100
    else:
        procent = 0

    season_result = (
        supabase
        .table("high_season")
        .select(
            "season, start_season, end_season, "
            "enk_low, enk_high, dobb_low, dobb_high, pris_morgenmad"
        )
        .eq("season", int(year))
        .limit(1)
        .execute()
    )

    if not season_result.data:
        st.error(f"Ingen sæsonopsætning er oprettet for {year}")
        st.stop()

    season_data = season_result.data[0]

    try:
        bf_price = float(season_data["pris_morgenmad"])

        if single_room and web in ("bc", "web"):
            high_season_price = float(season_data["enk_high"])
            low_season_price = float(season_data["enk_low"])
            single_room = "Y"
        else:
            high_season_price = float(season_data["dobb_high"])
            low_season_price = float(season_data["dobb_low"])
            single_room = "N"

            if web == "FM":
                low_season_price = high_season_price
    except (KeyError, TypeError, ValueError):
        st.error(f"Ugyldige priser i sæsonopsætningen for {year}")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**High season** {high_season_price:.2f} kr")
    with col2:
        st.markdown(f"**Low season** {low_season_price:.2f} kr")

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
    try:
        high_season_start = date.fromisoformat(
            season_data["start_season"]
        )
        high_season_end = date.fromisoformat(
            season_data["end_season"]
        )
    except (KeyError, TypeError, ValueError):
        st.error(f"Ugyldige højsæsonsdatoer for {year}")
        st.stop()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"**Højsæson starter** "
            f"{high_season_start.strftime('%d-%m-%Y')}"
        )

    with col2:
        st.markdown(
            f"**Højsæson slutter** "
            f"{high_season_end.strftime('%d-%m-%Y')}"
        )

    days = checkout_date - checkin_date

    total_nights = (checkout_date - checkin_date).days

    high_start = max(checkin_date, high_season_start)
    high_end = min(checkout_date, high_season_end)

    high_nights = max(0, (high_end - high_start).days)
    low_nights = total_nights - high_nights

    if web == "FM":
        pris = high_season_price * total_nights * num_rooms
    else:
        pris = (
                       high_nights * high_season_price
                       + low_nights * low_season_price
               ) * num_rooms
    # high_season_days = high_season_end - high_season_start
    # high_booking = (checkin_date >= high_season_start) and (checkout_date <= high_season_end)
    # low_booking = (((checkin_date <= high_season_start) and (checkout_date < high_season_start)) or
    #                (checkin_date > high_season_end))
    # mixbooking_early = (checkin_date < high_season_start) and (checkout_date >= high_season_start)
    # mixbooking_end = (checkout_date >= high_season_end) and (high_season_start < checkin_date) and (checkin_date <=                                                                                               high_season_end)
    #
    # high_season_days = high_season_end - high_season_start
    # mixearly = checkout_date - high_season_start
    # mixearly_b = high_season_start - checkin_date
    # mixend = high_season_end - checkin_date
    # mixend_b = checkout_date - high_season_end
    #
    # if web == "FM":
    #     pris = (high_season_price * int(days.days)) * int(num_rooms)
    # else:
    #     if high_booking:
    #         pris = (high_season_price * int(days.days)) * int(num_rooms)
    #     if low_booking:
    #         pris = (low_season_price * int(days.days)) * int(num_rooms)
    #     if mixbooking_early:
    #         pris = (((int(mixearly.days) * high_season_price) + (int(mixearly_b.days) * low_season_price)) * int(num_rooms))
    #     if mixbooking_end:
    #         pris = (high_season_price * (int(mixend.days)) + (int(mixend_b.days) * low_season_price)) * int(num_rooms)

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
        st.markdown(f"**Rabat** {formatted_rabat_t}kr".replace(".", ","))
        pristotal = prismed - rabat_t
        formatted_pristotal = f"{pristotal:.2f}".replace(".", ",")
        print("formatted_prismed:", formatted_prismed)
        print("type:", type(formatted_prismed))
    elif web == "FM":
        formatted_prismed = f"{prismed:.2f}".replace(".", ",")
        pris_add_a = (int(FM_add) / 100)
        pris_add_t = (prismed + br_f) * pris_add_a
        formatted_pris_add_t = f"{pris_add_t:.2f}"
        st.markdown(f"**Tiilæg** {formatted_pris_add_t} kr".replace(".", ","))
        pristotal = prismed + pris_add_t
        formatted_pristotal = f"{pristotal:.2f}".replace(".", ",")
        rabat_a = pris_add_a
    else:
        rabat_a = 0
        pristotal = prismed
        formatted_prismed = f"{prismed:.2f}".replace(".",",")
        formatted_pristotal = formatted_prismed

        print(formatted_pristotal)
    st.markdown(f"**Den totale pris** {formatted_pristotal}kr".replace(".",","))

    st.subheader("Kontakt information")

    name = st.text_input("Navn", key='reservation_name')
    fam_name = st.text_input(
        "Familienavn",
        help="Gemmes på bookingen og bruges også til opslag i historikken.",
    )
    telefon = st.text_input(" Kontakt telefon")
    email_address = st.text_input("email")

    nationalitet = st.text_input("Nationalitet - DK S N NL etc")

    known_guest = st.checkbox("check for known person")
    known = "N"
    previous_bookings = []

    if known_guest:
        email_search = email_address.strip()
        phone_search = normalize_phone(telefon)
        family_name_search = fam_name.strip()

        # E-mail er det stærkeste match og har altid første prioritet.
        if email_search:
            result = (
                supabase
                .table("historie_new")
                .select(
                    "season, booking_nr, navn, familie_navn, "
                    "indcheck, email, phone, spouse, comments"
                )
                .ilike("email", email_search)
                .lt("udcheck", date.today().isoformat())
                .order("udcheck", desc=True)
                .execute()
            )
            previous_bookings = result.data or []
            if previous_bookings:
                known = "YY"

        # Telefon slås kun op, hvis e-mail ikke gav et match.
        if known == "N" and phone_search:
            phone_variants = [phone_search]
            if phone_search.startswith("45") and len(phone_search) == 10:
                # Historikken indeholder også ældre danske numre uden 45.
                phone_variants.append(phone_search[2:])

            result = (
                supabase
                .table("historie_new")
                .select(
                    "season, booking_nr, navn, familie_navn, "
                    "indcheck, email, phone, spouse, comments"
                )
                .in_("phone", phone_variants)
                .lt("udcheck", date.today().isoformat())
                .order("udcheck", desc=True)
                .execute()
            )
            previous_bookings = result.data or []
            if previous_bookings:
                known = "Y"

        # Familienavn kan bruges til at finde kontaktoplysninger, men er ikke
        # entydigt nok til automatisk at markere gæsten som kendt.
        if known == "N" and not previous_bookings and family_name_search:
            result = (
                supabase
                .table("historie_new")
                .select(
                    "season, booking_nr, navn, familie_navn, "
                    "indcheck, email, phone, spouse, comments"
                )
                .ilike("familie_navn", family_name_search)
                .lt("udcheck", date.today().isoformat())
                .order("udcheck", desc=True)
                .execute()
            )
            previous_bookings = result.data or []

        manual_known = st.checkbox(
            "Jeg kender gæsten og vil markere bookingen som kendt",
            key="manual_known_guest",
        )
        if manual_known:
            known = "Y"

        if previous_bookings:
            if known == "N":
                st.info(
                    f"Mulige match fundet: {len(previous_bookings)} booking(er). "
                    "Kontrollér oplysningerne og markér gæsten manuelt, hvis du "
                    "kender personen."
                )
            else:
                st.success(
                    f"Tidligere gæst fundet: {len(previous_bookings)} booking(er) "
                    f"({known})"
                )
            st.dataframe(
                pd.DataFrame(previous_bookings),
                use_container_width=True,
            )
        elif email_search or phone_search or family_name_search:
            st.info("Ingen tidligere bookinger fundet.")
        else:
            st.info(
                "Indtast e-mail, telefon eller familienavn for at søge efter "
                "tidligere gæst."
            )

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

    if send_data:

        missing_fields = []

        if not booking_number:
            missing_fields.append("booking nummer")

        #if not name:
        #    missing_fields.append("navn")

        #if not checkin_date:
        #    missing_fields.append("check-in dato")

        #if not checkout_date:
        #    missing_fields.append("check-out dato")

        if missing_fields:
            st.warning(
                "Check data - mangler: "
                + ", ".join(missing_fields)
            )
            st.stop()

        excel_file = add_data(
            year=year,
            booking_number=booking_number,
            name=name,
            family_name=fam_name.strip(),
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            now=now,
            nationalitet=nationalitet,
            web=web,
            ankomst=ankomst,
            seng=seng,
            rabat_a=rabat_a,
            num_rooms=num_rooms,
            num_guests=num_guests,
            email_address=email_address,
            telefon=telefon,
            spouse=spouse,
            single_room=single_room,
            BF=BF,
            formatted_pristotal=formatted_pristotal,
            known=known,
            comments=comments
        )

        send_data_email(
            to_addr_1,
            confirmation_password,
            booking_number,
            name,
            checkin_date,
            checkout_date,
            num_rooms,
            now,
            nationalitet,
            web,
            ankomst,
            seng,
            procent,
            num_guests,
            email_address,
            telefon,
            formatted_pristotal,
            excel_file
        )

        st.success("Data mail sendt")


        # Gem booking i Supabase
        supabase.table("hk_dtb").insert({
            "booking_number": booking_number,
            "navn": name,
            "familie_navn": fam_name.strip(),
            "checkin_date": checkin_date.isoformat(),
            "checkout_date": checkout_date.isoformat(),
            "booking_date": now.isoformat(),
            "nation": nationalitet,
            "web": web,
            "ankomst": ankomst,
            "bed": seng,
            "rabat": procent,
            "numb_rooms": num_rooms,
            "numb_guests": num_guests,
            "email": email_address,
            "telefon": telefon,
            "spouse": spouse,
            "enkelt": single_room,
            "morgenmad": BF,
            "pris": pristotal,
            "known": known,
            "comments": comments,
            "room_number": 7,
            "season": int(year),
            "movable": True
        }).execute()

        st.success("Booking gemt i Supabase")
    else:
        st.markdown("Data mail ikke sendt")

