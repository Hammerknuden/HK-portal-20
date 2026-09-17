"""Streamlit selection/preview state machine. Only Save can call the write RPC."""
from modules.optimizer_preview import build_preview, save_preview


def clear_selection(state):
    state.pop("optimizer_choice", None)
    state.pop("optimizer_preview", None)


def preview_figure(preview):
    import plotly.express as px
    frame = preview["timeline"]
    figure = px.timeline(
        frame, x_start="checkin_date", x_end="checkout_date", y="Værelse",
        color="Ændring", text="Booking", facet_row="Visning",
        category_orders={"Visning": ["Før", "Efter (forslag)"],
                         "Værelse": [f"Værelse {r}" for r in (1, 2, 3, 4, 5, 7)]},
        color_discrete_map={"Flyttes": "#d97706", "Uændret": "#94a3b8"},
        hover_data={"id": True, "Booking": True, "checkin_date": True, "checkout_date": True},
        height=650,
    )
    figure.update_yaxes(autorange="reversed", title=None)
    figure.update_xaxes(tickformat="%d-%m-%Y", title=None)
    figure.for_each_annotation(lambda a: a.update(text=a.text.replace("Visning=", "")))
    return figure


def render_selected_solution(st, client, season, load_bookings, *, read_only=False):
    state = st.session_state
    choice = state.get("optimizer_choice")
    if not choice:
        return
    # The caller also clears normal selections when switching season. Preserve
    # uncertain save requests until retried so "cancel" cannot falsely undo them.
    preview = state.get("optimizer_preview")
    pending = bool(preview and preview.get("save_pending"))
    if choice["season"] != season and not pending:
        clear_selection(state)
        return
    st.subheader("Valgt løsning")
    st.write(f"Booking på værelse 7 → værelse {choice['plan']['target_room']} · sæson {choice['season']}")
    import pandas as pd
    st.dataframe(pd.DataFrame(choice["plan"]["moves"]).rename(columns={
        "id": "Database-ID", "booking_number": "Booking", "from_room": "Fra værelse",
        "to_room": "Til værelse", "checkin_date": "Ankomst", "checkout_date": "Afrejse",
    }), hide_index=True, use_container_width=True)
    if st.button("Fortryd", key="optimizer_cancel", disabled=pending):
        clear_selection(state)
        st.rerun()
        return
    if preview is None:
        st.caption("Vis løsningen på timeline, før du kan gemme den.")
        if st.button("Vis på timeline", key="optimizer_preview_button"):
            try:
                state["optimizer_preview"] = build_preview(load_bookings(), choice)
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Forhåndsvisningen kunne ikke hente bookingdata. Ingen ændringer er gemt.")
            else:
                st.rerun()
        return

    if not pending:
        st.info("Forhåndsvisning – ikke gemt. Orange bookinger indgår i flytningen; grå bookinger bliver stående.")
    st.plotly_chart(preview_figure(preview), use_container_width=True)
    if pending:
        st.warning(
            "Den seneste gemning er ikke bekræftet. Tryk Gem ændringer igen for at få status "
            "på samme gemning. Fortryd er deaktiveret, indtil resultatet er afklaret."
        )
    if read_only:
        st.info("Dette testmiljø er i læsetilstand. Du kan se forhåndsvisningen, men ikke gemme.")
    if st.button("Gem ændringer", key="optimizer_save", disabled=read_only):
        preview["save_pending"] = True
        try:
            save_preview(client, preview)
        except Exception as exc:
            code = str(getattr(exc, "code", ""))
            # These server rejections guarantee no committed transaction.
            if code in {"P0001", "42501", "55P03", "57014", "PGRST202"}:
                preview["save_pending"] = False
                if code == "PGRST202":
                    st.error("Gem-funktionen er ikke installeret i databasen endnu. Ingen ændringer er gemt.")
                elif code == "42501":
                    st.error("Databaseforbindelsen har ikke tilladelse til at gemme planen. Ingen ændringer er gemt.")
                elif code in {"55P03", "57014"}:
                    st.error("Databasen var optaget. Ingen ændringer er gemt. Prøv igen.")
                else:
                    st.error("Planen blev afvist ved den sidste kontrol. Ingen ændringer er gemt. Fortryd og kør analysen igen.")
            else:
                st.error("Gemningen blev ikke bekræftet. Tryk Gem ændringer igen med denne forhåndsvisning.")
        else:
            clear_selection(state)
            state.pop("optimizer_suggestions", None)
            state["optimizer_saved_message"] = "Alle flytninger er gemt. Timeline viser nu den gemte placering."
            st.cache_data.clear()
            st.rerun()
