"""Booking tools copied from Timeline, without its What if chart."""
import datetime
import re
from collections.abc import MutableMapping

import pandas as pd

from auth import is_admin, require_admin
from common import exclude_cancelled_bookings
from portal_access import uses_supabase_auth
from modules.timeline_edit import validate_timeline_edit
from modules.level2_optimizer import analyze_improvements, can_swap_blocks
from modules.room_swap import execute_room_swap
from modules.optimizer_preview import select_plan, booking_today
from modules.optimizer_state import booking_signature, invalidate_analysis
from modules.optimizer_workflow import clear_selection, render_selected_solution


class CalendarToolState(MutableMapping):
    """Keep optimizer selections independent from the original Timeline page."""
    def __init__(self, state):
        self.state = state

    def __getitem__(self, key):
        return self.state["calendar_tools_" + key]

    def __setitem__(self, key, value):
        self.state["calendar_tools_" + key] = value

    def __delitem__(self, key):
        del self.state["calendar_tools_" + key]

    def __iter__(self):
        return (key.removeprefix("calendar_tools_") for key in self.state
                if key.startswith("calendar_tools_"))

    def __len__(self):
        return sum(1 for _ in self)


class CalendarToolUI:
    def __init__(self, st):
        self.ui = st
        self.session_state = CalendarToolState(st.session_state)

    def __getattr__(self, key):
        return getattr(self.ui, key)


def render_booking_creation(st, supabase, selected_season):
    with st.sidebar.form("calendar_booking_form_new"):
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

        booking_number = st.text_input("booking_number")
        guest_name = st.text_input("navn")

        season = selected_season

        submitted = st.form_submit_button("Book nu")

        if submitted:

            if end_date <= start_date:

                st.error("Slut dato skal være efter start dato")

            else:

                try:

                    # Find eksisterende bookinger på samme værelse
                    existing = (
                        supabase
                        .table("hk_dtb")
                        .select("*")
                        .eq("room_number", int(room))
                        .execute()
                    )

                    existing_bookings = exclude_cancelled_bookings(
                        pd.DataFrame(existing.data or [])
                    )

                    overlap = False

                    for booking in existing_bookings.to_dict("records"):

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
                        if not booking_number:
                            st.error("Booking nummer mangler")
                            st.stop()

                        supabase.table("hk_dtb").insert({
                            "room_number": int(room),
                            "checkin_date": start_date.isoformat(),
                            "checkout_date": end_date.isoformat(),
                            "booking_number": int(booking_number),
                            "navn": guest_name.strip(),
                            "season": int(selected_season),
                            "movable": True,
                            "web": "web",
                        }).execute()

                        st.success("Booking gemt")

                        result = (
                            supabase
                            .table("hk_dtb")
                            .select("*")
                            .eq("booking_number", int(booking_number))
                            .execute()
                        )

                        st.write("Ny booking i DB:")
                        st.write(result.data)
                        st.rerun()

                except Exception as e:

                    st.error(f"Fejl ved gemning: {e}")


def render_booking_admin(st, supabase, df):
    calendar_admin_test_enabled = False
    if df.empty:
        return
    if message := st.session_state.pop("calendar_admin_edit_saved", None):
        st.success(message)
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
    scoped_test = (calendar_admin_test_enabled and int(booking["season"]) == 2026
                   and int(booking["booking_number"]) == 300 and booking["navn"] == "NN")
    edit_blocked = False
    if uses_supabase_auth():
        st.info("Godkendte brugere kan redigere og annullere med web = cansl. Permanent sletning kræver administrator.")


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
    current_name = booking.get("navn", "")
    new_name = st.text_input(
        "Rediger navn",
        value="" if pd.isna(current_name) else str(current_name)
    )
    current_web = booking.get("web", "")
    new_web = st.text_input(
        "Rediger web",
        value="" if pd.isna(current_web) else str(current_web),
        key=f"calendar_admin_web_{booking_id}",
        help="Brug eksempelvis bc for et ekstra værelse fra Booking.com.",
    )
    current_comments = booking.get("comments", "")
    new_comments = st.text_area(
        "Kommentar",
        value=(
            ""
            if pd.isna(current_comments)
            else str(current_comments)
        ),
        key=f"calendar_admin_comments_{booking_id}",
        help="Kommentaren gemmes i hk_dtb-feltet comments.",
    )
    new_movable = st.checkbox(
        "Kan flyttes af optimering",
        value=bool(booking.get("movable", True))
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
                "Gem ændringer",
                key=f"calendar_admin_save_{booking_id}", disabled=edit_blocked
        ):
            try:
                payload = {
                    "room_number": new_room,
                    "checkin_date": new_start.isoformat(),
                    "checkout_date": new_end.isoformat(),
                    "booking_number": int(new_guest),
                    "navn": new_name.strip(),
                    "web": new_web.strip(),
                    "comments": new_comments.strip(),
                    "movable": new_movable
                }
                validate_calendar_admin_edit(supabase, booking_id, payload)
                query = supabase.table("hk_dtb").update(payload).eq("id", booking_id)
                if scoped_test:
                    query = query.eq("season", 2026).eq("booking_number", 300).eq("navn", "NN")
                result = query.execute()
                if len(result.data or []) != 1:
                    raise ValueError("Ingen ændring bekræftet. Genindlæs og kontrollér skriveadgang.")
                if scoped_test:
                    verified = (supabase.table("hk_dtb").select(",".join(payload))
                                .eq("id", booking_id).eq("season", 2026)
                                .eq("booking_number", 300).eq("navn", "NN").execute())
                    if (len(verified.data or []) != 1
                            or any(verified.data[0].get(k) != v for k, v in payload.items())):
                        raise ValueError("Ændringen kunne ikke genlæses. Kontrollér bookingen før næste forsøg.")
                st.session_state["calendar_admin_edit_saved"] = "Ændringer gemt" + (" og genlæst fra databasen." if scoped_test else ".")
            except Exception as error:
                st.error(f"Fejl ved opdatering: {error}")
            else:
                st.rerun()

    with col2:
        if st.button(
                "Slet booking",
                key=f"calendar_admin_delete_{booking_id}", disabled=not is_admin()
        ):
            require_admin()
            supabase.table("hk_dtb").delete().eq(
                "id",
                booking_id
            ).execute()

            st.success("Booking slettet")
            st.rerun()

    with col3:
        if st.button(
                "🔄 Byt værelse",
                key=f"calendar_admin_open_swap_{booking_id}"
        ):
            st.session_state["calendar_admin_swap_open"] = True
            st.session_state["calendar_admin_swap_source_id"] = int(booking_id)

    if (
            st.session_state.get("calendar_admin_swap_open")
            and
            st.session_state.get("calendar_admin_swap_source_id") == int(booking_id)
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

        if swap_candidates.empty:
            st.info("Ingen anden booking at bytte med.")
            return

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

            key=f"calendar_admin_swap_target_{booking_id}"
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
                    key=f"calendar_admin_close_swap_{booking_id}"
            ):
                st.session_state["calendar_admin_swap_open"] = False
                st.session_state.pop("calendar_admin_swap_source_id", None)
                st.rerun()

        with col2:
            if swap_result["possible"]:
                if st.button(
                        "🔄 Udfør bytte",
                        key=f"calendar_admin_execute_swap_{booking_id}"
                ):
                    try:
                        swap_execution = execute_room_swap(
                            supabase=supabase,
                            booking_a_ids=swap_result["booking_ids_a"],
                            booking_b_ids=swap_result["booking_ids_b"],
                            room_a=swap_result["room_a"],
                            room_b=swap_result["room_b"],
                        )

                        st.cache_data.clear()

                        st.session_state["calendar_admin_swap_open"] = False
                        st.session_state.pop("calendar_admin_swap_source_id", None)

                        st.session_state["calendar_admin_edit_saved"] = "Bytte udført. Begge bookinger er flyttet."

                        st.rerun()
                    except Exception as error:
                        st.error(f"Bytte kunne ikke bekræftes: {error}")




    # vis samlet overblik over alle indtastede bookinger --

    with st.expander("Se alle bookinger"):

        st.dataframe(
            df,
            use_container_width=True
        )


def render_calendar_optimizer(st, supabase, selected_season):
    st = CalendarToolUI(st)
    if st.session_state.get("optimizer_season") != selected_season:
        st.session_state.pop("optimizer_suggestions", None)
        st.session_state["optimizer_season"] = selected_season
    st.subheader("Niveau 2 optimering")
    saved_message = st.session_state.pop("optimizer_saved_message", None)
    if saved_message:
        st.success(saved_message)
    choice = st.session_state.get("optimizer_choice")
    pending_save = st.session_state.get("optimizer_preview", {}).get("save_pending", False)
    if choice and choice["season"] != selected_season and not pending_save:
        clear_selection(st.session_state)
    st.caption(
        "Find placeringer fra værelse 7 til værelse 1–5. Alle ophold flyttes samlet. "
        "Vælg en løsning og se den på timeline. Først Gem ændringer opdaterer bookingerne."
    )


    def load_optimizer_bookings():
        # All seasons are needed to check stays crossing a season boundary.
        rows = []
        offset = 0
        while True:
            result = (
                supabase.table("hk_dtb")
                .select("id,booking_number,season,room_number,checkin_date,checkout_date,movable,web")
                .order("id").range(offset, offset + 999).execute()
            )
            rows.extend(result.data)
            if len(result.data) < 1000:
                break
            offset += 1000
        return pd.DataFrame(rows)


    optimizer_rows = None
    if (st.session_state.get("optimizer_suggestions") or st.session_state.get("optimizer_choice")) and not pending_save:
        try:
            optimizer_rows = load_optimizer_bookings()
            signature = booking_signature(optimizer_rows, selected_season, booking_today())
        except Exception:
            invalidate_analysis(st.session_state, None)
            st.error("De gemte forslag kunne ikke kontrolleres mod aktuelle bookinger og er derfor ryddet. Kør analysen igen.")
        else:
            if invalidate_analysis(st.session_state, signature):
                st.info("Bookingdata eller dags dato er ændret. Den tidligere analyse og forhåndsvisning er ryddet. Kør analysen igen.")

    if st.button("🔍 Undersøg optimeringsmuligheder", disabled=bool(st.session_state.get("optimizer_choice"))):
        st.session_state.pop("optimizer_suggestions", None)
        try:
            with st.spinner("Undersøger målværelser, skæringspunkter og flyttekæder …"):
                if optimizer_rows is None:
                    optimizer_rows = load_optimizer_bookings()
                st.session_state["optimizer_suggestions"] = analyze_improvements(
                    bookings=optimizer_rows, season=selected_season
                )
                st.session_state["optimizer_suggestions"]["data_signature"] = booking_signature(
                    optimizer_rows, selected_season, booking_today()
                )
        except Exception:
            st.error("Analysen kunne ikke gennemføres. Hent bookingdata igen og prøv på ny.")

    suggestions = st.session_state.get("optimizer_suggestions")
    if suggestions and suggestions.get("schema_version") != 3:
        st.session_state.pop("optimizer_suggestions", None)
        suggestions = None
        st.info("Kør analysen igen for at få forslag fra den nye søgning.")

    if suggestions and not st.session_state.get("optimizer_choice"):
        st.caption(f"Analyseret med dags dato: {suggestions['analysis_date']}")
        st.caption(f"Kun bookinger fra sæson {selected_season} kan flyttes. Andre sæsoner forbliver faste.")
        st.caption(
            "Søgningen prøver korte kæder med op til 3 andre bookinger samt længere bytter "
            "mellem to værelser ved hele bookinggrænser. Op til 25 alternativer vises pr. målværelse."
        )
        for error in suggestions.get("errors", []):
            st.error(error)
        recommendations = suggestions.get("recommendations", [])
        if not recommendations and not suggestions.get("errors"):
            st.info("Ingen fremtidige, flytbare bookinger på værelse 7 i den valgte sæson.")
        st.info(
            "Hvert forslag gælder alene. Forslag til forskellige bookinger kan bruge den samme plads. "
            "Kør analysen igen efter ændringer i bookingerne."
        )
        for rec in recommendations:
            with st.container(border=True):
                st.markdown(f"### Booking {rec['booking_number']}")
                st.write(f"Værelse 7 · {rec['checkin_date']} → {rec['checkout_date']}")
                if rec["status"] == "no_capacity":
                    st.warning("Ingen ledig kapacitet på værelse 1–5: " + ", ".join(rec["no_capacity_dates"]))
                    continue
                options = rec["options"]
                if options:
                    st.success(f"{len(options)} kontrollerede muligheder fundet")
                else:
                    st.info("Ingen løsning fundet i den udførte søgning.")
                limited_rooms = [str(r["room"]) for r in rec["target_results"] if r["limited"]]
                if limited_rooms:
                    st.caption(
                        "Søgningen er begrænset for værelse " + ", ".join(limited_rooms)
                        + ". Flere eller længere flyttekæder kan give yderligere løsninger."
                    )
                omitted = sum(r["omitted_options"] for r in rec["target_results"])
                if omitted:
                    st.caption(f"{omitted} yderligere fundne alternativer er udeladt; de korteste vises først.")
                locked_rooms = [str(r["room"]) for r in rec["target_results"] if r["locked_blocker_ids"]]
                if locked_rooms:
                    st.caption("Låste eller påbegyndte bookinger spærrer på værelse " + ", ".join(locked_rooms) + ".")
                for index, plan in enumerate(options, start=1):
                    title = (
                        f"Mulighed {index}: 7 → {plan['target_room']} · "
                        f"{plan['moved_existing']} andre bookinger flyttes"
                    )
                    with st.expander(title, expanded=(index == 1)):
                        if plan["window"]:
                            st.write("Bytte mellem bookinggrænser: " + " → ".join(plan["window"]))
                        if plan["missing_dates"]:
                            st.write("Frigør nætterne: " + ", ".join(plan["missing_dates"]))
                        table = pd.DataFrame(plan["moves"]).rename(columns={
                            "id": "Database-ID", "booking_number": "Booking",
                            "from_room": "Fra værelse", "to_room": "Til værelse",
                            "checkin_date": "Ankomst", "checkout_date": "Afrejse",
                        })
                        st.dataframe(table, hide_index=True, use_container_width=True)
                        st.caption(
                            "Alle viste flytninger hører sammen. Rækkefølgen i tabellen er ikke en "
                            "udførelsesrækkefølge. Ingen bookinger er ændret."
                        )
                        if st.button(
                            "Vælg denne løsning", key=f"optimizer_choose_{rec['candidate_id']}_{index}",
                            disabled=bool(st.session_state.get("optimizer_choice")),
                        ):
                            st.session_state["optimizer_choice"] = select_plan(plan, selected_season)
                            st.session_state.pop("optimizer_preview", None)
                            st.rerun()

    render_selected_solution(
        st, supabase, selected_season, load_optimizer_bookings,
        rpc_name="apply_optimizer_plan_authenticated" if uses_supabase_auth() else "apply_optimizer_plan"
    )
