import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit_authenticator as stauth
import datetime
import plotly.express as px
from auth import require_login
from common import init_session
import re
import os
from dotenv import load_dotenv
from supabase import create_client
from importlib.metadata import version
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


def load_bookings():
    result = (
        supabase
        .table("hk_dtb")
        .select("*")
        .execute()
    )

    df = pd.DataFrame(result.data)

    if not df.empty:
        df["checkin_date"] = pd.to_datetime(df["checkin_date"])
        df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    return df
def load_bookings():
    result = (
        supabase
        .table("hk_dtb")
        .select("*")
        .execute()
    )

    df = pd.DataFrame(result.data)

    if not df.empty:
        df["checkin_date"] = pd.to_datetime(df["checkin_date"])
        df["checkout_date"] = pd.to_datetime(df["checkout_date"])

    return df


# <-- INDSÆT HER

def optimize_temp_room(df):

    bookings = df.copy()

    bookings["optimized_room"] = bookings["room_number"]

    bookings = bookings.sort_values("checkin_date")

    for idx, row in bookings.iterrows():

        room = int(row["room_number"])

        if room != 7:
            continue

        start = row["checkin_date"]
        end = row["checkout_date"]

        for target_room in [1, 2, 3, 4, 5]:

            overlaps = bookings[
                (bookings.index != idx)
                &
                (bookings["optimized_room"].astype(int) == target_room)
                &
                (bookings["checkin_date"] < end)
                &
                (bookings["checkout_date"] > start)
            ]

            if overlaps.empty:

                bookings.loc[idx, "optimized_room"] = target_room
                break

    return bookings

# RESERVATION INFO
# -------------------------
df = load_bookings()
#st.write(df.columns.tolist())
optimized_df = optimize_temp_room(df)
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
                    .eq("room_number", room)
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

                    supabase.table("hk_dtb").insert({
                        "room_number": room,
                        "checkin_date": start_date.isoformat(),
                        "checkout_date": end_date.isoformat(),
                        "booking_number": int(name)
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
                    #st.rerun()

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

    # Fjern rækker uden gyldigt værelsesnummer
    plot_df = plot_df[
        plot_df["room_sort"].notna()
    ]

    plot_df["room_sort"] = plot_df["room_sort"].astype(int)

    plot_df["room_number"] = (
            "Værelse "
            + plot_df["room_number"].astype(str)
    )

    # Fjern værelse 0
    plot_df = plot_df[
        plot_df["room_sort"] > 0
    ]

    # Sortér værelserne numerisk
    plot_df = plot_df.sort_values("room_sort")

    plot_df["booking_number"] = plot_df["booking_number"].astype(str)
    plot_df["checkin_date"] = pd.to_datetime(plot_df["checkin_date"])
    plot_df["checkout_date"] = pd.to_datetime(plot_df["checkout_date"])

    debug = st.checkbox("Debug timeline")

    if debug:
        st.write("Antal rækker:", len(plot_df))

        st.write(
            df[
                ["id",
                 "booking_number",
                 "room_number"]
            ].head(20)
        )

        st.write(
            "Unikke værelser:",
            sorted(
                plot_df["room_number"]
                .astype(str)
                .unique()
            )
        )

        st.write(
            "Seneste bookinger:"
        )

        st.dataframe(
            df.sort_values(
                "id",
                ascending=False
            ).head(10)
        )

    fig = px.timeline(
        plot_df,
        x_start="checkin_date",
        x_end="checkout_date",
        y="room_number",
        color="booking_number",
        hover_name="booking_number",
        text="booking_number",
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    # Tving rækkefølgen på værelserne
    room_order = (
        plot_df
        .sort_values("room_sort")
        ["room_number"]
        .drop_duplicates()
        .tolist()
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

    fig.update_xaxes(
        rangeslider_visible=True,
        tickformat="%d-%m"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
    st.subheader("Optimeret belægningsplan")

    opt_plot = optimized_df.copy()

    opt_plot["room_number"] = (
            "Værelse "
            + opt_plot["optimized_room"].astype(str)
    )

    fig2 = px.timeline(
        opt_plot,
        x_start="checkin_date",
        x_end="checkout_date",
        y="room_number",
        color="booking_number",
        text="booking_number"
    )

    fig2.update_yaxes(
        autorange="reversed"
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
            f"{room_label(df[df['id'] == x].iloc[0]['room_number'])}"
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

    col1, col2 = st.columns(2)

    with col1:

        if st.button("Gem ændringer", key="new_dtb"):
            supabase.table("hk_dtb").update({
                "room_number": new_room,
                "checkin_date": new_start.isoformat(),
                "checkout_date": new_end.isoformat(),
                "booking_number": int(new_guest)
            }).eq("id", booking_id).execute()

            st.success("Ændringer gemt")
            st.rerun()

    with col2:

        if st.button("Slet booking", key="new dtb"):
            supabase.table("hk_dtb").delete().eq(
                "id",
                booking_id
            ).execute()

            st.success("Booking slettet")
            st.rerun()
    # vis samlet overblik over alle indtastede bookinger
    with st.expander("Se alle bookinger"):

        st.dataframe(
            df,
            use_container_width=True
        )

else:

    st.info(
        "Ingen bookinger at vise endnu."
    )






