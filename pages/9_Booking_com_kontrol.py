import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth import require_admin, require_login
from modules.booking_comparison import (
    combined_differences,
    compare_bookings,
    prepare_booking_com,
    prepare_database,
)
from supabase import create_client


st.set_page_config(page_title="Booking.com-kontrol", layout="wide")
require_login()
require_admin()

st.title("Booking.com-kontrol")
st.write(
    "Upload listen over aktive bookinger fra Booking.com. "
    "Filen sammenlignes med bookinger i hk_dtb, hvor web er sat til bc."
)

uploaded_file = st.file_uploader(
    "Booking.com-fil",
    type=["xls", "xlsx"],
    help="Eksporten skal indeholde gæstens navn, ind-/udtjekning og bookingdato.",
)

if uploaded_file is not None:
    try:
        booking_com_raw = pd.read_excel(uploaded_file)
        booking_com = prepare_booking_com(booking_com_raw)
    except ImportError:
        st.error(
            "Excel-filen kræver pakken xlrd. Kontrollér, at requirements.txt "
            "indeholder xlrd>=2.0.1, og genstart appen."
        )
        st.stop()
    except (ValueError, TypeError) as error:
        st.error(f"Booking.com-filen kunne ikke læses: {error}")
        st.stop()

    if booking_com.empty:
        st.warning("Filen indeholder ingen aktive bookinger.")
        st.stop()

    seasons = sorted(
        {
            checkin.year
            for checkin in booking_com["checkin"].dropna()
        }
    )
    if not seasons:
        st.error("Sæsonen kunne ikke findes ud fra indtjekningsdatoerne.")
        st.stop()

    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

    try:
        database_result = (
            supabase.table("hk_dtb")
            .select(
                "booking_number, season, navn, checkin_date, checkout_date, "
                "booking_date, numb_rooms, numb_guests, web"
            )
            .eq("web", "bc")
            .in_("season", seasons)
            .execute()
        )
        database_raw = pd.DataFrame(
            database_result.data or [],
            columns=[
                "booking_number",
                "season",
                "navn",
                "checkin_date",
                "checkout_date",
                "booking_date",
                "numb_rooms",
                "numb_guests",
                "web",
            ],
        )
        database = prepare_database(database_raw)
    except Exception as error:
        st.error(f"Bookingerne kunne ikke hentes fra hk_dtb: {error}")
        st.stop()

    result = compare_bookings(booking_com, database)
    differences = combined_differences(result)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Præcise matches", len(result["exact"]))
    col2.metric("Ændrede", len(result["changed"]))
    col3.metric("Kun Booking.com", len(result["only_bc"]))
    col4.metric("Kun hk_dtb", len(result["only_db"]))

    if differences.empty:
        st.success("Ingen forskelle fundet.")
    else:
        st.warning(f"Der er fundet {len(differences)} forskelle.")
        st.download_button(
            "Download differenceliste (CSV)",
            data=differences.to_csv(index=False).encode("utf-8-sig"),
            file_name="booking_com_differencer.csv",
            mime="text/csv",
        )

    tabs = st.tabs(
        [
            "Ændrede",
            "Kun Booking.com",
            "Kun hk_dtb",
            "Mulige matches",
            "Præcise matches",
        ]
    )
    tab_data = [
        result["changed"],
        result["only_bc"],
        result["only_db"],
        result["possible"],
        result["exact"],
    ]
    empty_messages = [
        "Ingen ændrede bookinger.",
        "Ingen bookinger mangler i hk_dtb.",
        "Ingen ekstra bc-bookinger i hk_dtb.",
        "Ingen usikre matches.",
        "Ingen præcise matches.",
    ]
    for tab, frame, empty_message in zip(tabs, tab_data, empty_messages):
        with tab:
            if frame.empty:
                st.info(empty_message)
            else:
                st.dataframe(frame, hide_index=True, use_container_width=True)

    st.caption(
        f"DB-data er afgrænset til sæson: {', '.join(map(str, seasons))}. "
        "Matchning bruger normaliseret navn og bookingdato først, derefter "
        "navn og opholdsdatoer. Flere hk_dtb-linjer med samme bookingnummer "
        "tælles som flere værelser under én booking. Mulige matches skal altid "
        "kontrolleres manuelt."
    )
