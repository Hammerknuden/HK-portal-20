"""Invitation onboarding only; never grants a portal role or login session."""
import re
from urllib.parse import urlparse

from modules.auth_client import PASSWORD_REQUIREMENT, valid_new_password
from modules.user_directory import directory_client


class InvitationInputError(ValueError):
    """Safe validation messages that may be shown to the administrator."""


def list_auth_users(client):
    # The admin API is paginated. Refuse a truncated directory rather than
    # overlooking an existing account and sending an unintended invitation.
    for page in range(1, 101):
        users = client.auth.admin.list_users(page=page, per_page=100)
        yield from users
        if len(users) < 100:
            return
    raise ValueError("User directory exceeds supported size")


def pending_invitations(secrets, client_factory, members=None):
    if members is None:
        raise ValueError("Database membership required")
    client, _ = directory_client(secrets, client_factory)
    roles = members
    rows = []
    for user in list_auth_users(client):
        if str(user.id) not in roles and user.invited_at:
            metadata = user.user_metadata or {}
            rows.append({"Navn": metadata.get("display_name") or "Navn mangler",
                         "E-mail": user.email or "", "Status": "Afventer portaladgang",
                         "uid": str(user.id), "confirmed": bool(user.email_confirmed_at)})
    return sorted(rows, key=lambda row: row["E-mail"].casefold())


def send_invitation(secrets, client_factory, name, email):
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise InvitationInputError("Indtast et navn på 1–100 tegn.")
    if not isinstance(email, str) or len(email.strip()) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email.strip()):
        raise InvitationInputError("Indtast en gyldig e-mailadresse.")
    email = email.strip()
    redirect = secrets.get("PASSWORD_RESET_URL", "")
    parsed = urlparse(redirect)
    if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment or parsed.username:
        raise InvitationInputError("PASSWORD_RESET_URL skal være hovedappens HTTPS-adresse.")
    client, _ = directory_client(secrets, client_factory)
    if any((user.email or "").casefold() == email.casefold() for user in list_auth_users(client)):
        raise InvitationInputError("E-mailadressen findes allerede i Supabase. Der er ikke sendt en ny invitation.")
    result = client.auth.admin.invite_user_by_email(email, options={
        "redirect_to": redirect,
        "data": {"display_name": name.strip()},
    })
    if not result.user or (result.user.email or "").casefold() != email.casefold():
        raise RuntimeError("Invitation result could not be confirmed")
    return str(result.user.id)


def _admin_context():
    import streamlit as st
    from auth import require_admin
    from portal_access import is_restore_test
    require_admin()
    if is_restore_test():
        raise ValueError("Invitationer er ikke tilgængelige i restore-testappen.")
    from supabase import create_client, ClientOptions
    return st.secrets, lambda url, key: create_client(
        url, key, options=ClientOptions(persist_session=False, auto_refresh_token=False))


def invite_portal_user(name, email):
    secrets, factory = _admin_context()
    return send_invitation(secrets, factory, name, email)


def load_pending_invitations():
    secrets, factory = _admin_context()
    from modules.portal_roles import load_members
    return pending_invitations(secrets, factory, members=load_members())


def render_invitation(st, client):
    if st.query_params.get("type") == "invite":
        token_hash = st.query_params.get("token_hash")
        st.session_state.clear()
        st.query_params.clear()
        if token_hash:
            st.session_state["invitation_hash"] = token_hash
        else:
            st.session_state["invitation_invalid"] = True
        st.rerun()
    if st.session_state.pop("invitation_success", False):
        st.success("Din adgangskode er gemt. En administrator skal aktivere din portaladgang, før du kan logge ind.")
    if not any(key in st.session_state for key in ("invitation_hash", "invitation_access", "invitation_invalid")):
        return
    st.subheader("Velkommen til Hammerknuden")
    st.info("Vælg din adgangskode. Portaladgangen aktiveres separat af en administrator.")
    if st.button("Tilbage til login", key="invitation_back"):
        token = st.session_state.get("invitation_access")
        if token:
            try:
                client.sign_out(token)
            except Exception:
                pass
        st.session_state.clear()
        st.rerun()
    if st.session_state.get("invitation_invalid"):
        st.error("Invitationen er ugyldig eller udløbet. Kontakt administratoren.")
        st.stop()
    if "invitation_access" not in st.session_state:
        if st.button("Accepter invitation", key="invitation_accept"):
            try:
                result = client.verify_invitation(st.session_state.pop("invitation_hash"))
                token = result["access_token"]
                user = client.get_user(token)
                if not user.get("id"):
                    raise ValueError("Missing user")
                st.session_state["invitation_access"] = token
                st.session_state["invitation_user_id"] = user["id"]
                st.session_state["invitation_email"] = user.get("email", "")
            except Exception:
                st.session_state["invitation_invalid"] = True
            st.rerun()
        st.stop()
    st.write("Konto:", st.session_state.get("invitation_email", ""))
    with st.form("invitation_password", clear_on_submit=True):
        password = st.text_input("Vælg adgangskode", type="password", help=PASSWORD_REQUIREMENT)
        confirmation = st.text_input("Gentag adgangskode", type="password")
        submitted = st.form_submit_button("Gem adgangskode")
    if submitted:
        if password != confirmation:
            st.error("Adgangskoderne er ikke ens.")
        elif not valid_new_password(password):
            st.error(PASSWORD_REQUIREMENT)
        else:
            token = st.session_state["invitation_access"]
            try:
                user = client.get_user(token)
                if user.get("id") != st.session_state["invitation_user_id"]:
                    raise ValueError("Invitation user changed")
                client.update_password(token, password)
            except Exception:
                st.error("Adgangskoden kunne ikke gemmes. Prøv en ny kode, eller kontakt administratoren, hvis invitationen er udløbet.")
            else:
                try:
                    client.sign_out(token)
                except Exception:
                    pass
                st.session_state.clear()
                st.session_state["invitation_success"] = True
                st.rerun()
    st.stop()
