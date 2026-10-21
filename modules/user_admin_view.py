"""Read-only user directory with a preview of future editing controls."""


def render_user_administration(st):
    from auth import require_admin
    from modules.user_directory import load_user_directory

    require_admin()
    st.divider()
    st.header("Brugeradministration")
    st.info(
        "Brugeroversigten kan læses. Invitationer og ændringer er endnu ikke aktiveret."
    )
    st.caption("Brugere til Secure login. Legacy-login administreres separat.")

    st.subheader("Brugeroversigt")
    try:
        with st.spinner("Henter brugere …"):
            users = load_user_directory()
        if users:
            st.dataframe(users, hide_index=True, use_container_width=True)
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
        st.selectbox(
            "Vælg bruger", ["Brugerlisten tilkobles senere"],
            disabled=True, key="user_admin_selected",
        )
        st.selectbox(
            "Brugerens rolle", ["Almindelig bruger", "Administrator"],
            disabled=True, key="user_admin_edit_role",
        )
        st.selectbox(
            "Adgang", ["Aktiv", "Deaktiveret"],
            disabled=True, key="user_admin_edit_status",
        )
        st.button("Gem ændringer", disabled=True, key="user_admin_save")
        st.button("Send nulstillingsmail", disabled=True, key="user_admin_reset")

    st.caption(
        "Almindelige brugere kan arbejde med bookinger og morgenmad. "
        "Administratorer har desuden adgang til Setup, Booking.com-afstemning, "
        "gæsteregistreringer og permanent sletning af bookinger."
    )
