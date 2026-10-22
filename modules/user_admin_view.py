"""Administrator directory, display names and invitations awaiting access."""


def render_user_administration(st):
    from auth import require_admin
    from modules.user_directory import load_user_directory, save_user_display_name
    from modules.user_invitation import invite_portal_user, load_pending_invitations, InvitationInputError

    from modules.portal_roles import save_member

    require_admin()
    st.divider()
    st.header("Brugeradministration")
    st.info(
        "Du kan invitere brugere, aktivere adgang og ændre roller. Den sidste aktive administrator kan ikke deaktiveres eller nedgraderes."
    )
    st.caption("Brugere til Secure login.")

    if message := st.session_state.pop("user_admin_saved", None):
        st.success(message)
    users = []
    st.subheader("Brugeroversigt")
    try:
        with st.spinner("Henter brugere …"):
            users = load_user_directory(include_ids=True)
        if users:
            st.dataframe([{k: v for k, v in user.items() if k not in ("uid", "membership")} for user in users],
                         hide_index=True, use_container_width=True)
        else:
            st.info("Ingen brugere er angivet i portalens adgangsopsætning.")
    except Exception:
        st.warning("Brugeroversigten kunne ikke hentes. Kontrollér portalens bruger-ID'er, "
                   "Supabase-adresser og servernøgle i Cloud Secrets.")
    st.caption("Roller og aktiv adgang styres samlet i Supabase.")

    st.subheader("Invitationer uden portaladgang")
    pending = []
    try:
        pending = load_pending_invitations()
        if pending:
            st.dataframe([{k: v for k, v in row.items() if k not in ("uid", "confirmed")} for row in pending], hide_index=True, use_container_width=True)
        else:
            st.caption("Ingen invitationer afventer portaladgang.")
    except Exception:
        st.warning("Invitationerne kunne ikke hentes. Genindlæs siden før et nyt forsøg.")

    if pending:
        pending_by_id = {row["uid"]: row for row in pending}
        with st.form("activate_portal_user"):
            target = st.selectbox("Inviteret bruger", list(pending_by_id),
                                  format_func=lambda uid: pending_by_id[uid]["E-mail"])
            new_role = st.selectbox("Tildel rolle", ["user", "admin"],
                                   format_func=lambda role: "Administrator" if role == "admin" else "Almindelig bruger")
            activate = st.form_submit_button("Aktivér portaladgang")
        if activate:
            if not pending_by_id[target]["confirmed"]:
                st.error("Brugeren skal først acceptere invitationen.")
            else:
                try:
                    save_member(target, new_role, True, {})
                except Exception:
                    st.error("Adgangen kunne ikke bekræftes. Genindlæs oversigten og kontrollér, at invitationen er accepteret.")
                else:
                    st.session_state["user_admin_saved"] = "Portaladgangen er aktiveret. Brugeren kan logge ind."
                    st.rerun()

    create_column, edit_column = st.columns(2)
    with create_column:
        st.subheader("Invitér bruger")
        st.caption("Modtageren vælger selv sin adgangskode. Aktivér derefter adgangen ovenfor.")
        with st.form("user_admin_invite_form", clear_on_submit=False):
            invite_name = st.text_input("Navn", max_chars=100, key="user_admin_invite_name")
            invite_email = st.text_input("E-mail", max_chars=254, key="user_admin_invite_email")
            send = st.form_submit_button("Send invitation", type="primary")
        if send:
            try:
                invite_portal_user(invite_name, invite_email)
            except InvitationInputError as error:
                st.error(str(error))
            except Exception:
                st.error("Invitationen kunne ikke bekræftes. Genindlæs oversigten og kontrollér Supabase, "
                         "før du prøver igen; kontoen kan allerede være oprettet.")
            else:
                st.session_state["user_admin_saved"] = (
                    f"Supabase har accepteret invitationen til {invite_email.strip()}. "
                    "Bed modtageren kontrollere sin indbakke og spammappe. Portaladgangen afventer aktivering."
                )
                st.rerun()

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
            member = user["membership"]
            snapshot_key = f"user_access_snapshot_{selected}"
            previous = st.session_state.get(snapshot_key, dict(member))
            with st.form(f"user_access_{selected}"):
                role = st.selectbox("Adgangsrolle", ["user", "admin"], index=1 if member["role"] == "admin" else 0,
                                    format_func=lambda value: "Administrator" if value == "admin" else "Almindelig bruger")
                active = st.checkbox("Aktiv portaladgang", value=member["active"])
                save_access = st.form_submit_button("Gem rolle og adgang")
            if save_access:
                try:
                    save_member(selected, role, active, previous)
                except Exception:
                    st.session_state.pop(snapshot_key, None)
                    st.error("Adgangen kunne ikke ændres. Den sidste aktive administrator skal bevares. Genindlæs også siden, hvis en anden administrator har ændret brugeren.")
                else:
                    st.session_state.pop(snapshot_key, None)
                    st.session_state["user_admin_saved"] = "Rolle og adgang er gemt i Supabase."
                    st.rerun()
            else:
                st.session_state[snapshot_key] = dict(member)
        else:
            st.caption("Hent brugeroversigten for at redigere et navn.")
        st.button("Send nulstillingsmail", disabled=True, key="user_admin_reset")

    st.caption(
        "Almindelige brugere kan arbejde med bookinger og morgenmad. "
        "Administratorer har desuden adgang til Setup, Booking.com-afstemning, "
        "gæsteregistreringer og permanent sletning af bookinger."
    )
