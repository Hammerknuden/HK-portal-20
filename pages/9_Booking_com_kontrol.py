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
from modules.guest_scan import (
    build_storage_path,
    camera_image_to_pdf,
    normalize_pdf_to_a4,
    validate_pdf,
)
from supabase import create_client


TEST_STORAGE_BUCKET = "test bucket"


st.set_page_config(page_title="Booking.com-kontrol", layout="wide")
require_login()
require_admin()

st.title("Booking.com-kontrol")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)

with st.expander("Test: Scan gæsteregistrering til Supabase Storage"):
    st.warning(
        "Bucket'en er offentlig under testen. Brug kun et testdokument uden "
        "rigtige personoplysninger."
    )
    st.caption(
        "Tag et billede med mobilkameraet, eller vælg en eksisterende PDF. "
        "Kamerabilledet og uploadede PDF-sider gemmes i A4-format."
    )

    scan_season = st.number_input(
        "Sæson",
        min_value=2022,
        max_value=2100,
        value=2026,
        step=1,
        key="scan_season",
    )
    scan_booking_number = st.number_input(
        "Bookingnummer",
        min_value=1,
        max_value=99999,
        value=None,
        step=1,
        placeholder="Eksempel: 13 gemmes som 013",
        key="scan_booking_number",
    )
    camera_file = st.camera_input(
        "Tag billede af den enkeltsidede registrering",
        key="guest_registration_camera",
    )
    pdf_file = st.file_uploader(
        "Eller vælg en eksisterende PDF",
        type=["pdf"],
        key="guest_registration_pdf",
    )

    if st.button("Upload testregistrering", type="primary"):
        if scan_booking_number is None:
            st.error("Indtast bookingnummer først.")
        elif camera_file is not None and pdf_file is not None:
            st.error("Vælg enten kamera eller PDF - ikke begge dele.")
        elif camera_file is None and pdf_file is None:
            st.error("Tag et billede eller vælg en PDF først.")
        else:
            try:
                storage_path = build_storage_path(
                    scan_season,
                    scan_booking_number,
                )
                if camera_file is not None:
                    pdf_bytes = camera_image_to_pdf(camera_file.getvalue())
                else:
                    pdf_bytes = normalize_pdf_to_a4(pdf_file.getvalue())

                validate_pdf(pdf_bytes)
                supabase.storage.from_(TEST_STORAGE_BUCKET).upload(
                    path=storage_path,
                    file=pdf_bytes,
                    file_options={
                        "content-type": "application/pdf",
                        "upsert": "false",
                    },
                )
                st.success("Testregistreringen er uploadet til Supabase Storage.")
                st.code(f"{TEST_STORAGE_BUCKET}/{storage_path}")
            except Exception as error:
                st.error(f"Upload mislykkedes: {error}")

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

    try:
        database_result = (
            supabase.table("hk_dtb")
            .select(
                "booking_number, season, navn, checkin_date, checkout_date, "
                "booking_date, numb_rooms, numb_guests, room_number, web"
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
                "room_number",
                "web",
            ],
        )
        database = prepare_database(database_raw)
    except Exception as error:
        st.error(f"Bookingerne kunne ikke hentes fra hk_dtb: {error}")
        st.stop()

    result = compare_bookings(booking_com, database)
    differences = combined_differences(result)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Præcise matches", len(result["exact"]))
    col2.metric("Ikke placeret", len(result["unplaced"]))
    col3.metric("Ændrede", len(result["changed"]))
    col4.metric("Kun Booking.com", len(result["only_bc"]))
    col5.metric("Kun hk_dtb", len(result["only_db"]))

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
            "Værelse 7 / temp",
            "Ændrede",
            "Kun Booking.com",
            "Kun hk_dtb",
            "Mulige matches",
            "Præcise matches",
        ]
    )
    tab_data = [
        result["unplaced"],
        result["changed"],
        result["only_bc"],
        result["only_db"],
        result["possible"],
        result["exact"],
    ]
    empty_messages = [
        "Ingen bookinger mangler endelig placering.",
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
        "kontrolleres manuelt. Bookinger på værelse 7 matches fortsat, men "
        "vises særskilt som ikke endeligt placeret."
    )
