"""Recovery sessions never become portal login sessions."""
import streamlit as st
from testing.auth_client import resolve_role


def render_recovery(client, admin_ids, user_ids):
    incoming = st.query_params.get("token_hash")
    if incoming:
        recovery_type = st.query_params.get("type")
        st.session_state.clear()
        st.query_params.clear()
        if recovery_type == "recovery":
            st.session_state["recovery_hash"] = incoming
        else:
            st.session_state["recovery_invalid"] = True
        st.rerun()

    if st.session_state.pop("recovery_success", False):
        st.success("Adgangskoden er ændret. Log ind med din nye adgangskode.")

    if not any(k in st.session_state for k in ("recovery_hash", "recovery_access", "recovery_invalid")):
        return

    st.subheader("Vælg ny adgangskode")
    if st.button("Tilbage til login"):
        st.session_state.clear()
        st.rerun()
    if st.session_state.get("recovery_invalid"):
        st.error("Linket er ugyldigt eller udløbet. Bed om en ny nulstillingsmail.")
        st.stop()

    if "recovery_access" not in st.session_state:
        st.write("Bekræft, at du vil nulstille din adgangskode.")
        if st.button("Fortsæt med nulstilling"):
            try:
                result = client.verify_recovery(st.session_state.pop("recovery_hash"))
                token = result["access_token"]
                user = client.get_user(token)
                if not resolve_role(user, admin_ids, user_ids):
                    try:
                        client.sign_out(token)
                    finally:
                        raise ValueError("Not a portal user")
                st.session_state["recovery_access"] = token
                st.session_state["recovery_email"] = user.get("email", "")
            except Exception:
                st.session_state["recovery_invalid"] = True
            st.rerun()
        st.stop()

    st.write("Konto:", st.session_state.get("recovery_email", ""))
    with st.form("new_password", clear_on_submit=True):
        password = st.text_input("Ny adgangskode (mindst 12 tegn)", type="password")
        confirmation = st.text_input("Gentag ny adgangskode", type="password")
        submitted = st.form_submit_button("Gem ny adgangskode")
    if submitted:
        if password != confirmation:
            st.error("Adgangskoderne er ikke ens.")
        elif len(password) < 12:
            st.error("Brug mindst 12 tegn.")
        else:
            token = st.session_state["recovery_access"]
            try:
                user = client.get_user(token)
                if not resolve_role(user, admin_ids, user_ids):
                    raise ValueError("Not a portal user")
                client.update_password(token, password)
            except Exception:
                st.error("Adgangskoden kunne ikke ændres. Vælg en stærkere, ny kode, eller bed om et nyt link, hvis sessionen er udløbet.")
            else:
                try:
                    client.sign_out(token)
                except Exception:
                    pass
                st.session_state.clear()
                st.session_state["recovery_success"] = True
                st.rerun()
    st.stop()


def render_forgot_password(client):
    with st.expander("Glemt adgangskode?"):
        redirect_url = st.secrets.get("PASSWORD_RESET_URL", "")
        if not redirect_url:
            st.info("Nulstilling er endnu ikke konfigureret i testappen.")
            return
        with st.form("forgot_password", clear_on_submit=True):
            email = st.text_input("Din login-e-mail")
            submitted = st.form_submit_button("Send nulstillingsmail")
        if submitted:
            if not email.strip() or "@" not in email:
                st.error("Indtast din e-mailadresse.")
            else:
                try:
                    client.request_password_reset(email, redirect_url)
                except Exception:
                    st.error("Mailen kunne ikke bestilles lige nu. Vent et minut og prøv igen.")
                else:
                    st.success("Hvis adressen er registreret, modtager du en mail. Se også i spam.")
