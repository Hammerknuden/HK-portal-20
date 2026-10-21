"""Layout preview for future user administration; no account or database calls."""


def render_user_administration(st):
    st.divider()
    st.header("Brugeradministration")
    st.info(
        "Forhåndsvisning: Brugeradministrationen er ikke aktiveret endnu. "
        "Brugerlisten indlæses ikke, og der oprettes eller ændres ingen brugere."
    )
    st.caption("Denne sektion skal administrere Secure login. Legacy-login administreres separat.")

    st.subheader("Brugeroversigt")
    st.dataframe(
        {"Navn": [], "E-mail": [], "Rolle": [], "Status": []},
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Oversigten er endnu ikke tilkoblet. Den tomme liste viser ikke de nuværende brugere.")

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
