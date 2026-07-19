import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
from pathlib import Path
import streamlit_authenticator as stauth
import plotly.express as px
from auth import require_login
from common import init_session
import re
import os
from dotenv import load_dotenv
from supabase import create_client
from importlib.metadata import version
from modules.level2_optimizer import analyze_improvements
from modules.level2_optimizer import can_swap_blocks
from modules.room_swap import execute_room_swap
# -------------------------
# INIT
# -------------------------

st.set_page_config(page_title="Timeline2", layout="wide")
require_login()

#st.session_state
st.write(version("streamlit-authenticator"))
load_dotenv()

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

#####
# new database
#####

try:
    result = supabase.table("hk_dtb").select("*").limit(1).execute()

    st.success("Forbindelse OK")
    #st.write(result.data)

except Exception as e:
    st.error(f"Fejl: {e}")


def to_dt(x):
    return pd.to_datetime(x)

# -------------------------
# LOAD / SAVE
# -------------------------


selected_season = st.selectbox(
    "Sæson",
    [2026, 2027, 2028]
)
if (
    "optimizer_season" not in st.session_state
    or st.session_state["optimizer_season"] != selected_season
):
    st.session_state.pop("optimizer_suggestions", None)
    st.session_state["optimizer_season"] = selected_season


def load_bookings():
    result = (
        supabase
        .table("hk_dtb")
        .select("*")
        .eq("season", selected_season)
        .execute()
    )

    df = pd.DataFrame(result.data)

    if not df.empty:

        df["checkin_date"] = pd.to_datetime(df["checkin_date"])
        df["checkout_date"] = pd.to_datetime(df["checkout_date"])

        if "web" in df.columns:
            df = df[
                df["web"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                != "cansl"
            ]

        if "room_number" in df.columns:
            df["room_number"] = (
                pd.to_numeric(
                    df["room_number"],
                    errors="coerce"
                )
                .astype("Int64")
            )

        if "season" in df.columns:
            df["season"] = (
                pd.to_numeric(
                    df["season"],
                    errors="coerce"
                )
                .astype("Int64")
            )

    return df


def optimize_temp_room(df):

    bookings = df.copy()

    bookings = bookings[
        bookings["room_number"].notna()
    ]

    bookings["room_number"] = pd.to_numeric(
        bookings["room_number"],
        errors="coerce"
    )

    bookings = bookings[
        bookings["room_number"].notna()
    ]

    bookings["room_number"] = (
        bookings["room_number"].astype(int)
    )

    bookings["optimized_room"] = (
        bookings["room_number"]
    )

    bookings["packing_status"] = "Normal"

    bookings = bookings.sort_values(
        "checkin_date"
    )

    for idx, row in bookings.iterrows():

        room = row["room_number"]

        if room != 7:
            continue

        start = row["checkin_date"]
        end = row["checkout_date"]

        for target_room in [1, 2, 3, 4, 5]:

            overlaps = bookings[
                (bookings.index != idx)
                &
                (bookings["optimized_room"] == target_room)
                &
                (bookings["checkin_date"] < end)
                &
                (bookings["checkout_date"] > start)
            ]

            if overlaps.empty:

                bookings.loc[idx, "optimized_room"] = target_room
                bookings.loc[idx, "packing_status"] = "Flyttet"

                break

    # <-- INDSÆT BLOKKEN HER

    mask = (
        (bookings["room_number"] == 7)
        &
        (bookings["optimized_room"] == 7)
    )

    bookings.loc[
        mask,
        "packing_status"
    ] = "Ikke flyttet"

    return bookings
# RESERVATION INFO
# -------------------------


df = load_bookings()

df["season"] = pd.to_numeric(
    df["season"],
    errors="coerce"
)
df["room_number"] = pd.to_numeric(
    df["room_number"],
    errors="coerce"
)
optimized_df = optimize_temp_room(df)

st.write(
    f"Antal bookinger i sæson {selected_season}:",
    len(df)
)

# -------------------------
# CREATE BOOKING
# -------------------------
with st.sidebar.form("booking_form_new"):
    room = st.selectbox(
        "room_number",
        [str(i) for i in range(1, 8)]
    )

    start_date = st.date_input(
        "checkin_date",
        value=datetime.date.today()
    )

    end_date = st.date_input(
        "checkout_date",
        value=datetime.date.today() + datetime.timedelta(days=2)
    )

    name = st.text_input("booking_number")

    season = selected_season

    submitted = st.form_submit_button("Book nu")

    if submitted:

        if end_date < start_date:

            st.error("Slut dato skal være efter start dato")

        else:

            try:

                # Find eksisterende bookinger på samme værelse
                existing = (
                    supabase
                    .table("hk_dtb")
                    .select("*")
                    .eq("room_number", int(room))
                    .neq("web", "cansl")
                    .execute()
                )

                overlap = False

                for booking in existing.data:

                    existing_checkin = pd.to_datetime(
                        booking["checkin_date"]
                    ).date()

                    existing_checkout = pd.to_datetime(
                        booking["checkout_date"]
                    ).date()

                    if (
                            existing_checkin < end_date
                            and
                            existing_checkout > start_date
                    ):
                        overlap = True
                        break

                if overlap:

                    st.error(
                        f"Værelset er allerede booket "
                        f"fra {existing_checkin} til {existing_checkout}"
                    )

                else:
                    if not name:
                        st.error("Booking nummer mangler")
                        st.stop()

                    supabase.table("hk_dtb").insert({
                        "room_number": int(room),
                        "checkin_date": start_date.isoformat(),
                        "checkout_date": end_date.isoformat(),
                        "booking_number": int(name),
                        "season": int(selected_season),
                        "movable": True,
                        "web": "web",
                    }).execute()

                    st.success("Booking gemt")

                    result = (
                        supabase
                        .table("hk_dtb")
                        .select("*")
                        .eq("booking_number", int(name))
                        .execute()
                    )

                    st.write("Ny booking i DB:")
                    st.write(result.data)
                    st.rerun()

            except Exception as e:

                st.error(f"Fejl ved gemning: {e}")


# -------------------------
# TIMELINE
# -------------------------
st.subheader("Belægningsplan")

if not df.empty:

    plot_df = df.copy()

    # Fjern tomme værelser
    plot_df = plot_df[
        plot_df["room_number"].notna()
    ]

    plot_df = plot_df[
        plot_df["room_number"].astype(str).str.strip() != ""
    ]

    # Udtræk værelsesnummer til sortering
    plot_df["room_sort"] = (
        plot_df["room_number"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
    )

    plot_df = plot_df[
        plot_df["room_sort"].notna()
    ]

    plot_df["room_sort"] = plot_df["room_sort"].astype(int)

    plot_df = plot_df[
        plot_df["room_sort"] > 0
        ]

    room_labels = {
        1: "Værelse 1",
        2: "Værelse 2",
        3: "Værelse 3",
        4: "Værelse 4",
        5: "Værelse 5",
        6: "Privat",
        7: "Temporary",
    }

    plot_df["room_number"] = (
        plot_df["room_sort"]
        .map(room_labels)
    )

    plot_df = plot_df.sort_values("room_sort")

    plot_df["booking_number"] = plot_df["booking_number"].astype(str)
    plot_df["checkin_date"] = pd.to_datetime(plot_df["checkin_date"])
    plot_df["checkout_date"] = pd.to_datetime(plot_df["checkout_date"])

    plot_df["room_number"] = (
        plot_df["room_sort"]
        .astype(int)
        .map(room_labels)
    )

    plot_df_display = plot_df.copy()

    if len(plot_df_display) > 0:

        dummy_date = plot_df_display["checkin_date"].min()
        dummy_rows = []

        for room_no, room_label in room_labels.items():

            if room_label not in plot_df_display["room_number"].unique():
                dummy_rows.append({
                    "room_number": room_label,
                    "checkin_date": dummy_date,
                    "checkout_date": dummy_date + pd.Timedelta(minutes=1),
                    "booking_number": f"DUMMY_{room_no}",
                    "room_sort": room_no
                })

        if dummy_rows:
            plot_df_display = pd.concat(
                [plot_df_display, pd.DataFrame(dummy_rows)],
                ignore_index=True
            )

    fig = px.timeline(
        plot_df_display,
        x_start="checkin_date",
        x_end="checkout_date",
        y="room_number",
        color="booking_number",
        hover_name="booking_number",
        text="booking_number",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    room_order = [
        "Værelse 1",
        "Værelse 2",
        "Værelse 3",
        "Værelse 4",
        "Værelse 5",
        "Privat",
        "Temporary",
    ]

    fig.update_yaxes(
        categoryorder="array",
        categoryarray=room_order[::-1]
    )
    # Ugenumre som lodrette mandagslinjer
    mandage = pd.date_range(
        plot_df_display["checkin_date"].min(),
        plot_df_display["checkout_date"].max(),
        freq="W-MON"
    )

    for d in mandage:
        x = d.strftime("%Y-%m-%d")

        fig.add_shape(
            type="line",
            x0=x,
            x1=x,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(
                color="gray",
                width=1,
                dash="dot"
            )
        )
        fig.add_annotation(
            x=x,
            y=0,
            yref="paper",
            text=f"{d.isocalendar().week}",
            showarrow=False,
            yshift=-18,
            font=dict(size=10, color="gray")
        )

    # Tving rækkefølgen på værelserne

    room_order = [
        "Værelse 1",
        "Værelse 2",
        "Værelse 3",
        "Værelse 4",
        "Værelse 5",
        "Privat",
        "Temporary",
    ]

    fig.update_yaxes(
        categoryorder="array",
        categoryarray=room_order[::-1]
    )

    # Hent kalender-events fra Supabase
    events_result = (
        supabase
        .table("Events")
        .select("*")
        .eq("season", int(selected_season))
        .execute()
    )

    events_df = pd.DataFrame(events_result.data)

    if not events_df.empty:

        events_df["start_date"] = pd.to_datetime(events_df["start_date"])
        events_df["end_date"] = pd.to_datetime(events_df["end_date"])

        for _, event in events_df.iterrows():
            events_df["start_date"] = pd.to_datetime(events_df["start_date"])
            events_df["end_date"] = pd.to_datetime(events_df["end_date"])

            for _, event in events_df.iterrows():
                fig.add_vrect(
                    x0=event["start_date"],
                    x1=event["end_date"],
                    fillcolor=event["color"],
                    opacity=(
                        float(event["opacity"])
                        if pd.notna(event["opacity"])
                        else 0.10
                    ),
                    line_width=0
                )

                fig.add_annotation(
                    x=event["start_date"],
                    y=-0.08,
                    xref="x",
                    yref="paper",
                    text=event["event"],
                    showarrow=False,
                    xanchor="left",
                    bgcolor="white",
                    bordercolor="lightgray",
                    borderwidth=1,
                    font=dict(size=8)
                )

        #ugenumre
    fig.update_xaxes(
        rangeslider_visible=True,
        tickformat="%d-%m",
        showgrid=True,
        gridcolor="lightgray",
        dtick="D1"
    )
    fig.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=room_order
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_title="Dato",
        yaxis_title="",
        showlegend=False,
        height=400
    )

    zoom_today = st.checkbox(
        "Zoom omkring dags dato",
        value=False
    )

    xaxis_settings = dict(
        rangeslider_visible=True,
        tickformat="%d-%m",
        showgrid=True,
        gridcolor="lightgray",
        gridwidth=1,
        dtick="D7"
    )

    if zoom_today:
        xaxis_settings["range"] = [
            pd.Timestamp.today() - pd.Timedelta(days=7),
            pd.Timestamp.today() + pd.Timedelta(days=21)
        ]

    fig.update_xaxes(**xaxis_settings)

    st.plotly_chart(
        fig,
        use_container_width=True
    )
    if st.checkbox("What if - timeline"):

        st.subheader("Optimeret belægningsplan")

        opt_plot = optimized_df.copy()

        opt_plot["room_number"] = (
                "Værelse "
                + opt_plot["optimized_room"].astype(str)
        )
        opt_plot["room_sort"] = (
            opt_plot["room_number"]
            .astype(str)
            .str.extract(r"(\d+)")
            .astype(int)
        )
        fig2 = px.timeline(
            opt_plot,
            x_start="checkin_date",
            x_end="checkout_date",
            y="room_number",
            color="packing_status",
            text="booking_number",
            color_discrete_map={
                "Normal": "lightblue",
                "Flyttet": "green",
                "Ikke flyttet": "red"
            }
        )
        room_order = [
            "Værelse 1",
            "Værelse 2",
            "Værelse 3",
            "Værelse 4",
            "Værelse 5",
            "Værelse 6",
            "Værelse 7"
        ]

        fig2.update_yaxes(
            autorange="reversed",
            categoryorder="array",
            categoryarray=room_order
        )

        fig2.update_xaxes(
            rangeslider_visible=True,
            tickformat="%d-%m",
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
            dtick="D7"
        )
        fig2.update_yaxes(
            autorange="reversed",
            categoryorder="array",
            categoryarray=room_order
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )
    # -------------------------
    # EDIT BOOKINGS
    # -------------------------

    def room_label(room):
        if pd.isna(room) or str(room).strip() == "":
            return "Ikke tildelt"

        try:
            return f"Værelse {int(float(room))}"
        except:
            return f"Værelse {room}"


    st.subheader("Administrer bookinger")

    booking_id = st.selectbox(
        "Vælg booking",
        df["id"],
        format_func=lambda x: (
            f"Booking {df[df['id'] == x].iloc[0]['booking_number']} | "
            f"{room_label(df[df['id'] == x].iloc[0]['room_number'])} | "
            f"{'🔓' if df[df['id'] == x].iloc[0].get('movable', True) else '🔒'}"
        )
    )

    booking = df[df["id"] == booking_id].iloc[0]

    room_text = str(booking["room_number"])

    match = re.search(r"(\d+)", room_text)

    if match:
        room_number = int(match.group(1)) - 1
    else:
        room_number = 0

    room_number = max(0, min(room_number, 6))

    room_options = [1, 2, 3, 4, 5, 6, 7]

    new_room = st.selectbox(
        "Edit room",
        room_options,
        index=room_number
    )

    new_start = st.date_input(
        "Rediger checkin_date",
        value=pd.to_datetime(
            booking["checkin_date"]
        ).date()
    )

    new_end = st.date_input(
        "Rediger checkout_date",
        value=pd.to_datetime(
            booking["checkout_date"]
        ).date()
    )

    new_guest = st.text_input(
        "Rediger booking_number",
        value=str(booking["booking_number"])
    )
    new_movable = st.checkbox(
        "Kan flyttes af optimering",
        value=bool(booking.get("movable", True))
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
                "Gem ændringer",
                key=f"timeline_save_{booking_id}"
        ):
            supabase.table("hk_dtb").update({
                "room_number": new_room,
                "checkin_date": new_start.isoformat(),
                "checkout_date": new_end.isoformat(),
                "booking_number": int(new_guest),
                "movable": new_movable
            }).eq(
                "id",
                booking_id
            ).execute()

            st.success("Ændringer gemt")
            st.rerun()

    with col2:
        if st.button(
                "Slet booking",
                key=f"timeline_delete_{booking_id}"
        ):
            supabase.table("hk_dtb").delete().eq(
                "id",
                booking_id
            ).execute()

            st.success("Booking slettet")
            st.rerun()

    with col3:
        if st.button(
                "🔄 Byt værelse",
                key=f"timeline_open_swap_{booking_id}"
        ):
            st.session_state["timeline_swap_open"] = True
            st.session_state["timeline_swap_source_id"] = int(booking_id)

    if (
            st.session_state.get("timeline_swap_open")
            and
            st.session_state.get("timeline_swap_source_id") == int(booking_id)
    ):
        st.divider()
        st.subheader("🔄 Byt værelse")

        st.info(
            f"Valgt booking: "
            f"{booking['booking_number']} | "
            f"Værelse {booking['room_number']}"
        )
        swap_candidates = df[
            df["id"] != int(booking_id)
            ].copy()

        swap_target_id = st.selectbox(
            "Vælg booking der skal byttes med",
            options=swap_candidates["id"].tolist(),
            format_func=lambda x: (
                f"Booking "
                f"{swap_candidates.loc[swap_candidates['id'] == x, 'booking_number'].iloc[0]} | "
                f"Værelse "
                f"{swap_candidates.loc[swap_candidates['id'] == x, 'room_number'].iloc[0]} | "
                f"{pd.to_datetime(
                    swap_candidates.loc[
                        swap_candidates['id'] == x,
                        'checkin_date'
                    ].iloc[0]
                ).strftime('%d-%m-%Y')} "
                f"til "
                f"{pd.to_datetime(
                    swap_candidates.loc[
                        swap_candidates['id'] == x,
                        'checkout_date'
                    ].iloc[0]
                ).strftime('%d-%m-%Y')}"
            ),

            key=f"timeline_swap_target_{booking_id}"
        )

        target_booking = swap_candidates[
            swap_candidates["id"] == swap_target_id
            ].iloc[0]

        st.markdown("#### Valgte bookinger")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Booking A**")
            st.write(f"Bookingnummer: {booking['booking_number']}")
            st.write(f"Værelse: {int(booking['room_number'])}")
            st.write(
                "Periode: "
                f"{pd.to_datetime(booking['checkin_date']).strftime('%d-%m-%Y')} "
                "til "
                f"{pd.to_datetime(booking['checkout_date']).strftime('%d-%m-%Y')}"
            )

        with col_b:
            st.markdown("**Booking B**")
            st.write(f"Bookingnummer: {target_booking['booking_number']}")
            st.write(f"Værelse: {int(target_booking['room_number'])}")
            st.write(
                "Periode: "
                f"{pd.to_datetime(target_booking['checkin_date']).strftime('%d-%m-%Y')} "
                "til "
                f"{pd.to_datetime(target_booking['checkout_date']).strftime('%d-%m-%Y')}"
            )

        block_a = {
            "booking_ids": [int(booking["id"])],
            "room_number": int(booking["room_number"]),
        }

        block_b = {
            "booking_ids": [int(target_booking["id"])],
            "room_number": int(target_booking["room_number"]),
        }

        swap_result = can_swap_blocks(
            block_a,
            block_b,
            df
        )

        st.markdown("#### Kontrol af bytte")

        if swap_result["possible"]:
            st.success(
                f"🟢 Bytte muligt: "
                f"Booking {booking['booking_number']} kan flyttes til værelse "
                f"{swap_result['room_b']}, og booking "
                f"{target_booking['booking_number']} kan flyttes til værelse "
                f"{swap_result['room_a']}."
            )
        else:
            st.error("🔴 Bytte ikke muligt")

            if not swap_result["block_a_ok"]:
                st.warning(
                    f"Booking {booking['booking_number']} kan ikke flyttes "
                    f"til værelse {swap_result['room_b']}."
                )

            if not swap_result["block_b_ok"]:
                st.warning(
                    f"Booking {target_booking['booking_number']} kan ikke flyttes "
                    f"til værelse {swap_result['room_a']}."
                )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                    "❌ Afbryd",
                    key=f"timeline_close_swap_{booking_id}"
            ):
                st.session_state["timeline_swap_open"] = False
                st.session_state.pop("timeline_swap_source_id", None)
                st.rerun()

        with col2:
            if swap_result["possible"]:
                if st.button(
                        "🔄 Udfør bytte",
                        key=f"timeline_execute_swap_{booking_id}"
                ):
                    swap_execution = execute_room_swap(
                        supabase=supabase,
                        booking_a_ids=swap_result["booking_ids_a"],
                        booking_b_ids=swap_result["booking_ids_b"],
                        room_a=swap_result["room_a"],
                        room_b=swap_result["room_b"],
                    )

                    st.cache_data.clear()

                    st.session_state["timeline_swap_open"] = False
                    st.session_state.pop("timeline_swap_source_id", None)

                    st.success("Bytte udført")
                    st.write("Booking A IDs:", swap_result["booking_ids_a"])
                    st.write("Booking B IDs:", swap_result["booking_ids_b"])
                    st.write("Værelse A:", swap_result["room_a"])
                    st.write("Værelse B:", swap_result["room_b"])

                    #st.rerun()



    # vis samlet overblik over alle indtastede bookinger --

    with st.expander("Se alle bookinger"):

        st.dataframe(
            df,
            use_container_width=True
        )

else:

    st.info(
        "Ingen bookinger at vise endnu."
    )

st.subheader("Niveau 2 optimering")

if st.button("🔍 Undersøg optimeringsmuligheder"):
    st.session_state["optimizer_suggestions"] = analyze_improvements(
        bookings=df,
        season=selected_season
    )

suggestions = st.session_state.get("optimizer_suggestions")

if suggestions:

    recommendations = suggestions.get(
        "recommendations",
        []
    )

    st.subheader("Optimeringsforslag")

    if not recommendations:
        st.info("Ingen forslag fundet")

    for rec in recommendations:

        booking_number = rec.get("booking_number")
        status = rec.get("status")

        with st.container(border=True):

            st.markdown(f"### Booking {booking_number}")

            if status == "ready":
                st.success("🟢 Klar til flytning")
                continue

            elif status == "rearrangement":
                st.info("🔵 Kræver omrokering")

            else:
                st.error("🔴 Ingen flyttemulighed")
                continue

            target_room = rec.get("target_room")
            options = rec.get("options", [])

            st.success(
                f"Mulig placering på værelse {target_room}"
            )

            if not options:
                st.info("Ingen flyttemuligheder fundet")
                continue

            for i, option in enumerate(options, start=1):

                move_to_room = option["flyt_blok_til"]
                blockers = option["blokeringer"]
                score = option["score"]

                with st.expander(
                    f"Mulighed {i}: Flyt blok til værelse {move_to_room}",
                    expanded=(i == 1)
                ):
                    st.write(
                        f"Booking {booking_number} placeres på værelse {target_room}"
                    )
                    st.write(
                        f"Blok flyttes til værelse {move_to_room}"
                    )
                    st.write(f"Blokeringer: {blockers}")
                    st.write(f"Score: {score}")

                    if st.button(
                            f"Udfør mulighed {i}",
                            key=f"execute_{booking_number}_{i}"
                    ):

                        block_ids = rec.get("block_booking_ids")
                        source_room = rec.get("source_room")
                        move_to_room = option["flyt_blok_til"]
                        blocking_blocks = option.get("blocking_blocks", [])

                        # 1. Flyt blokerende blokke fra modtager-rummet tilbage til source_room
                        for blocking_block in blocking_blocks:
                            blocking_ids = blocking_block["booking_ids"]

                            supabase.table("hk_dtb").update({
                                "room_number": int(source_room)
                            }).in_(
                                "id",
                                blocking_ids
                            ).execute()

                        # 2. Flyt target-blokken til valgt værelse
                        supabase.table("hk_dtb").update({
                            "room_number": int(move_to_room)
                        }).in_(
                            "id",
                            block_ids
                        ).execute()

                        # 3. Ryd optimizer-session
                        st.session_state.pop("optimizer_suggestions", None)

                        st.success("Flytning udført - kør analysen igen")

                        st.rerun()
