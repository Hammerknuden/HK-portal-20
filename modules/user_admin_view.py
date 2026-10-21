"""Read-only user directory with a preview of future editing controls."""


def render_user_administration(st):
    from auth import require_admin
    from modules.user_directory import load_user_directory, save_user_display_name

    require_admin()
    st.divider()
    st.header("Brugeradministration")
    st.info(
        "Du kan ændre brugernes visningsnavne. Invitationer og ændring af adgang er endnu ikke aktiveret."
    )
    st.caption("Brugere til Secure login. Legacy-login administreres separat.")

    if message := st.session_state.pop("user_admin_saved", None):
        st.success(message)
    users = []
    st.subheader("Brugeroversigt")
    try:
        with st.spinner("Henter brugere …"):
            users = load_user_directory(include_ids=True)
        if users:
            st.dataframe([{k: v for k, v in user.items() if k != "uid"} for user in users],
                         hide_index=True, use_container_width=True)
        else:
            st.info("Ingen brugere er angivet i portalens adgangsopsætning.")
    except Exception:
        st.warning("Brugeroversigten kunne ikke hentes. Kontrollér portalens bruger-ID'er, "
                   "Supabase-adresser og servernøgle i Cloud Secrets.")
    st.caption("Navn og e-mail hentes fra Supabase. Rollen viser portalens adgangsopsætning; "
               "oversigten kontrollerer ikke hver enkelt databasepolitik.")

    create_column, edit_column = st.columns(2)
    with create_column:
        st.subheader("Invitér bruger")
        st.text_input("Navn", disabled=True, key="user_admin_invite_name")
        st.text_input("E-mail", disabled=True, key="user_admin_invite_email")
        st.selectbox(
            "Rolle", ["Almindelig bruger", "Administrator"],
            disabled=True, key="user_admin_invite_role",
        )
        st.caption("Den kommende invitation skal lade brugeren vælge sin egen adgangskode.")
        st.button("Send invitation", disabled=True, key="user_admin_invite", type="primary")

    with edit_column:
        st.subheader("Administrér bruger")
        if users:
            by_id = {user["uid"]: user for user in users}
            selected = st.selectbox(
                "Vælg bruger", list(by_id),
                format_func=lambda uid: f"{by_id[uid]['Navn']} · {by_id[uid]['E-mail']}",
                key="user_admin_selected",
            )
            user = by_id[selected]
            with st.form(f"user_admin_name_{selected}"):
                name = st.text_input("Visningsnavn", value="" if user["Navn"] == "Navn mangler" else user["Navn"], max_chars=100)
                st.text_input("E-mail", value=user["E-mail"], disabled=True)
                st.text_input("Rolle", value=user["Rolle"], disabled=True)
                submitted = st.form_submit_button("Gem navn")
            if submitted:
                if not name.strip():
                    st.error("Indtast et navn.")
                else:
                    try:
                        saved_name = save_user_display_name(selected, name)
                    except Exception:
                        st.error("Navneændringen kunne ikke bekræftes. Genindlæs oversigten før et nyt forsøg.")
                    else:
                        st.session_state["user_admin_saved"] = f"Navnet {saved_name} er gemt og genlæst fra Supabase."
                        st.rerun()
        else:
            st.caption("Hent brugeroversigten for at redigere et navn.")
        st.selectbox(
            "Adgang", ["Aktiv", "Deaktiveret"],
            disabled=True, key="user_admin_edit_status",
        )
        st.button("Send nulstillingsmail", disabled=True, key="user_admin_reset")

    st.caption(
        "Almindelige brugere kan arbejde med bookinger og morgenmad. "
        "Administratorer har desuden adgang til Setup, Booking.com-afstemning, "
        "gæsteregistreringer og permanent sletning af bookinger."
    )
