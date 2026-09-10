import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth import require_login, require_admin
from modules.price_development import PRICE_FIELDS, build_price_development
from modules.price_sheet import create_price_sheet_pdf
from portal_access import get_database_client
from modules.booking_pace import normalize_season_rows


st.set_page_config(page_title="Setup", layout="wide")
require_login()
require_admin()


supabase = get_database_client()

st.success("Forbindelse til Supabase OK")

st.title("Setup ⚙️")

st.title("Pris modul setup")

price_result = (
    supabase
    .table("high_season")
    .select(
        "season, enk_low, enk_high, "
        "dobb_low, dobb_high, pris_morgenmad, "
        "start_season, end_season"
    )
    .order("season")
    .execute()
)

price_rows, season_warnings = normalize_season_rows(price_result.data or [], "Sæsonopsætning")
for message in season_warnings:
    st.warning(message)

if not price_rows:
    st.warning("Der er ingen sæsoner i high_season-tabellen")
else:
    prices_by_season = {
        int(row["season"]): row
        for row in price_rows
    }

    selected_price_season = st.selectbox(
        "Vælg sæson",
        options=list(prices_by_season)
    )
    current_prices = prices_by_season[selected_price_season]

    col1, col2 = st.columns(2)

    with col1:
        enk_low = st.number_input(
            "Enkeltværelse – lavsæson",
            value=float(current_prices["enk_low"]),
            min_value=0.0,
            step=5.0,
            key=f"enk_low_{selected_price_season}",
        )
        enk_high = st.number_input(
            "Enkeltværelse – højsæson",
            value=float(current_prices["enk_high"]),
            min_value=0.0,
            step=5.0,
            key=f"enk_high_{selected_price_season}",
        )
        breakfast_price = st.number_input(
            "Morgenmad pr. gæst pr. nat",
            value=float(current_prices["pris_morgenmad"]),
            min_value=0.0,
            step=5.0,
            key=f"breakfast_{selected_price_season}",
        )

    with col2:
        dobb_low = st.number_input(
            "Dobbeltværelse – lavsæson",
            value=float(current_prices["dobb_low"]),
            min_value=0.0,
            step=5.0,
            key=f"dobb_low_{selected_price_season}",
        )
        dobb_high = st.number_input(
            "Dobbeltværelse – højsæson",
            value=float(current_prices["dobb_high"]),
            min_value=0.0,
            step=5.0,
            key=f"dobb_high_{selected_price_season}",
        )

    draft_prices = {
        "enk_low": enk_low,
        "enk_high": enk_high,
        "dobb_low": dobb_low,
        "dobb_high": dobb_high,
        "pris_morgenmad": breakfast_price,
    }

    st.subheader("Prisudvikling år for år")
    development = build_price_development(
        price_rows,
        draft_season=selected_price_season,
        draft_prices=draft_prices,
    )
    price_columns = {
        "År": st.column_config.NumberColumn("År", format="%d"),
    }
    for label in PRICE_FIELDS.values():
        price_columns[label] = st.column_config.NumberColumn(
            label,
            format="%.0f kr",
        )
        price_columns[f"{label} ændring"] = st.column_config.NumberColumn(
            "Ændring",
            format="%.1f %%",
            help="Ændring i forhold til året før.",
        )
    st.dataframe(
        development,
        hide_index=True,
        use_container_width=True,
        column_config=price_columns,
    )
    st.caption(
        f"Tallene for {selected_price_season} opdateres straks, mens du ændrer "
        "priserne. De gemmes først, når du trykker på knappen nedenfor."
    )

    save_prices = st.button("Gem priser", type="primary")

    if save_prices:
        (
            supabase
            .table("high_season")
            .update({
                "enk_low": enk_low,
                "enk_high": enk_high,
                "dobb_low": dobb_low,
                "dobb_high": dobb_high,
                "pris_morgenmad": breakfast_price
            })
            .eq("season", int(selected_price_season))
            .execute()
        )

        st.success(f"Priser for {selected_price_season} er gemt")
        st.rerun()

    try:
        price_sheet_pdf = create_price_sheet_pdf(
            current_prices,
            logo_path=Path(__file__).resolve().parents[1] / "logo2.jpg"
        )
        st.download_button(
            "🖨️ Print prisskema (PDF)",
            data=price_sheet_pdf,
            file_name=f"prisskema_{selected_price_season}.pdf",
            mime="application/pdf",
            help="Hent det senest gemte prisskema som en printklar PDF."
        )
        st.caption("PDF'en indeholder de senest gemte priser.")
    except (KeyError, TypeError, ValueError) as error:
        st.warning(f"Prisskemaet kunne ikke dannes: {error}")

st.header("Afslut sæson")
st.caption(
    "Afslutningen gemmer alle sæsonens statistikopgørelser. Fra 2027 overføres "
    "også bookinghistorikken. For 2026 bevares den allerede overførte bookinghistorik. "
    "Bookingerne bliver liggende i hk_dtb, så de fortsat kan slås op."
)
try:
    pace_status_rows = (
        supabase.table("high_season").select("season, pace_archived")
        .order("season").execute().data or []
    )
    pace_status_rows, season_warnings = normalize_season_rows(pace_status_rows, "Sæsonopsætning")
    for message in season_warnings:
        st.warning(message)
    pace_status_rows = [r for r in pace_status_rows if int(r["season"]) >= 2026]
    if pace_status_rows:
        pace_year = st.selectbox("Sæson der skal afsluttes", [int(r["season"]) for r in pace_status_rows])
        pace_current = next(r for r in pace_status_rows if int(r["season"]) == pace_year)
        saved_reports = supabase.table("statistik_historik").select("report_type").eq("season", pace_year).execute().data or []
        statistics_complete = len(saved_reports) == 8
        if pace_current["pace_archived"] and statistics_complete:
            st.success(f"Sæson {pace_year} er afsluttet. Booking pace og statistik bruger historikken.")
        else:
            if pace_current["pace_archived"]:
                st.info(f"Booking pace for {pace_year} er historisk. Sæsonens øvrige statistik mangler at blive gemt.")
            else:
                st.info(f"Sæson {pace_year} er åben. Statistikken beregnes fra aktuelle bookinger.")
            if pace_year == 2026:
                st.caption("2026: Kun statistik og sæsonstatus gemmes. Bookinghistorikken overføres ikke igen.")
            ready_to_close = st.checkbox(
                f"Sæson {pace_year} er færdig, og tallene er klar til at blive gemt",
                key=f"ready_to_close_{pace_year}",
            )
            label = "Gem statistik og afslut 2026" if pace_year == 2026 else "Afslut sæson og gem historik"
            if st.button(label, disabled=not ready_to_close):
                try:
                    with st.spinner("Gemmer og afstemmer sæsonen …"):
                        supabase.rpc("close_booking_season", {"p_season": pace_year}).execute()
                    st.rerun()
                except Exception as error:
                    st.error(f"Sæsonafslutningen blev ikke bekræftet. Genindlæs siden for status. {error}")
    else:
        st.info("Der er ingen sæsoner fra 2026 i sæsonopsætningen.")
except Exception as error:
    st.warning("Sæsonstatus kunne ikke hentes. Kontrollér databaseadgang og statistikmigrationerne.")
    st.text(str(error))

st.header("Administrer events")
st.write("Brug farven 'blue' til events som wonder, FM , brug 'green' til familie og brug 'grey' til helligdage ")


# -------------------------------------------------
# HENT EVENTS
# -------------------------------------------------

def load_events():
    result = (
        supabase
        .table("Events")
        .select("*")
        .order("start_date")
        .execute()
    )

    events = pd.DataFrame(result.data or [])

    if not events.empty:
        events["start_date"] = pd.to_datetime(
            events["start_date"]
        ).dt.date

        events["end_date"] = pd.to_datetime(
            events["end_date"]
        ).dt.date

    return events


events_df = load_events()


# -------------------------------------------------
# OPRET EVENT
# -------------------------------------------------

st.subheader("Opret event")

with st.form("create_event_form"):

    new_event = st.text_input(
        "Eventnavn"
    )

    col1, col2 = st.columns(2)

    with col1:
        new_start_date = st.date_input(
            "Startdato",
            value=date.today()
        )

    with col2:
        new_end_date = st.date_input(
            "Slutdato",
            value=date.today()
        )

    new_color = st.text_input(
        "Farve",
        value="lightgray",
        help="Eksempel: lightgray, red, blue eller #DDEEFF"
    )

    new_opacity = st.slider(
        "Gennemsigtighed",
        min_value=0.0,
        max_value=1.0,
        value=0.20,
        step=0.05
    )

    create_event = st.form_submit_button(
        "Opret event"
    )


if create_event:

    if not new_event.strip():
        st.error("Eventnavn mangler")

    elif new_end_date < new_start_date:
        st.error("Slutdato må ikke ligge før startdato")

    else:
        supabase.table("Events").insert({
            "season": int(new_start_date.year),
            "event": new_event.strip(),
            "start_date": new_start_date.isoformat(),
            "end_date": new_end_date.isoformat(),
            "color": new_color.strip() or "lightgray",
            "opacity": float(new_opacity)
        }).execute()

        st.success("Event oprettet")
        st.rerun()


# -------------------------------------------------
# REDIGER EVENT
# -------------------------------------------------

st.subheader("Rediger event")

if events_df.empty:

    st.info("Der er endnu ingen events")

else:

    selected_event_id = st.selectbox(
        "Vælg event",
        events_df["id"].tolist(),
        format_func=lambda event_id: (
            f"{events_df.loc[events_df['id'] == event_id, 'event'].iloc[0]}"
            f" | "
            f"{events_df.loc[events_df['id'] == event_id, 'start_date'].iloc[0]}"
            f" - "
            f"{events_df.loc[events_df['id'] == event_id, 'end_date'].iloc[0]}"
        )
    )

    selected_event = events_df[
        events_df["id"] == selected_event_id
    ].iloc[0]
    edit_key_suffix = int(selected_event_id)

    with st.form(f"edit_event_form_{edit_key_suffix}"):

        edit_event_name = st.text_input(
            "Eventnavn",
            value=str(selected_event["event"]),
            key=f"edit_event_name_{edit_key_suffix}"
        )

        col1, col2 = st.columns(2)

        with col1:
            edit_start_date = st.date_input(
                "Startdato",
                value=selected_event["start_date"],
                key=f"edit_event_start_{edit_key_suffix}"
            )

        with col2:
            edit_end_date = st.date_input(
                "Slutdato",
                value=selected_event["end_date"],
                key=f"edit_event_end_{edit_key_suffix}"
            )

        edit_color = st.text_input(
            "Farve",
            value=(
                str(selected_event["color"])
                if pd.notna(selected_event.get("color"))
                else "lightgray"
            ),
            key=f"edit_event_color_{edit_key_suffix}"
        )

        current_opacity = (
            float(selected_event["opacity"])
            if pd.notna(selected_event.get("opacity"))
            else 0.20
        )

        edit_opacity = st.slider(
            "Gennemsigtighed",
            min_value=0.0,
            max_value=1.0,
            value=current_opacity,
            step=0.05,
            key=f"edit_event_opacity_{edit_key_suffix}"
        )

        save_event = st.form_submit_button(
            "Gem ændringer"
        )

    if save_event:

        if not edit_event_name.strip():
            st.error("Eventnavn mangler")

        elif edit_end_date < edit_start_date:
            st.error("Slutdato må ikke ligge før startdato")

        else:
            (
                supabase
                .table("Events")
                .update({
                    "season": int(edit_start_date.year),
                    "event": edit_event_name.strip(),
                    "start_date": edit_start_date.isoformat(),
                    "end_date": edit_end_date.isoformat(),
                    "color": edit_color.strip() or "lightgray",
                    "opacity": float(edit_opacity)
                })
                .eq("id", int(selected_event_id))
                .execute()
            )

            st.success("Event opdateret")
            st.rerun()


    # -------------------------------------------------
    # SLET EVENT
    # -------------------------------------------------

    st.subheader("Slet event")

    confirm_delete = st.checkbox(
        f"Bekræft sletning af {selected_event['event']}"
    )

    if st.button(
        "Slet event",
        type="secondary",
        disabled=not confirm_delete
    ):
        (
            supabase
            .table("Events")
            .delete()
            .eq("id", int(selected_event_id))
            .execute()
        )

        st.success("Event slettet")
        st.rerun()
