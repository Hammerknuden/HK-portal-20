import pandas as pd
import streamlit as st
from datetime import date
from auth import require_login, require_admin
from supabase import create_client


st.set_page_config(page_title="Setup", layout="wide")
require_login()
require_admin()

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

st.success("Forbindelse til Supabase OK")

st.title("Setup ⚙️")

st.title("Pris modul setup")

st.write("priser 2026-2027-2028")
# Initialiser state første gang_

st.write("priser 2026-2027-2028")

from config.prices import DEFAULT_PRICES

if "prices" not in st.session_state:
    st.session_state.prices = DEFAULT_PRICES.copy()

st.session_state.prices["Sing-Room-HS-26"] = st.number_input(
    "Single room high season 2026",
    value=st.session_state.prices["Sing-Room-HS-26"]
)

if "prices" not in st.session_state:
    st.session_state.prices = {
        "Sing-Room-HS-26": 975,
        "Sing-Room-LS-26": 850,
        "Dobb-Room-HS-26": 1075,
        "Dobb-Room-LS-26": 950,
        "Breakfirst-26": 100,
        "Sing-Room-HS-27": 990,
        "Sing-Room-LS-27": 875,
        "Dobb-Room-HS-27": 1090,
        "Dobb-Room-LS-27": 980,
        "Breakfirst-27": 110,
    }

st.write("Rediger priser:")

# Opdater priser direkte i session_state
for produkt in st.session_state.prices:
    st.session_state.prices[produkt] = st.number_input(
        produkt,
        value=float(st.session_state.prices[produkt]),
        min_value=0.0,
        step=5.0,
        key=produkt
    )

# Vis aktuelle værdier
st.write("### Nuværende priser")
st.json(st.session_state.prices)
# Eksempel:
new_year = st.text_input("Tilføj nyt booking år")
if st.button("Gem"):
    st.success(f"{new_year} gemt!")

st.header("Administrer events")


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

    with st.form("edit_event_form"):

        edit_event_name = st.text_input(
            "Eventnavn",
            value=str(selected_event["event"])
        )

        col1, col2 = st.columns(2)

        with col1:
            edit_start_date = st.date_input(
                "Startdato",
                value=selected_event["start_date"],
                key="edit_event_start"
            )

        with col2:
            edit_end_date = st.date_input(
                "Slutdato",
                value=selected_event["end_date"],
                key="edit_event_end"
            )

        edit_color = st.text_input(
            "Farve",
            value=(
                str(selected_event["color"])
                if pd.notna(selected_event.get("color"))
                else "lightgray"
            )
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
            key="edit_event_opacity"
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
