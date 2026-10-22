"""Role administration through user-JWT RPCs, never through a service key."""
from modules.auth_settings import auth_settings, access_token
from modules.auth_client import AuthClient


def role_client():
    import streamlit as st
    from auth import require_admin
    from portal_access import is_restore_test
    require_admin()
    if is_restore_test():
        raise ValueError("Role administration unavailable in restore testing")
    settings = auth_settings(st.secrets)
    return AuthClient(settings["SUPABASE_AUTH_URL"], settings["SUPABASE_PUBLISHABLE_KEY"]), access_token(st.session_state)


def load_members():
    client, token = role_client()
    rows = client.portal_rpc("portal_list_members", token)
    if not isinstance(rows, list):
        raise ValueError("Invalid members response")
    return {row["user_id"]: row for row in rows}


def save_member(uid, role, active, previous):
    if role not in ("admin", "user") or type(active) is not bool:
        raise ValueError("Invalid role/status")
    client, token = role_client()  # Fresh administrator check at click time.
    result = client.portal_rpc("portal_set_member", token, {
        "p_user_id": uid, "p_role": role, "p_active": active,
        "p_expected_role": previous.get("role"), "p_expected_active": previous.get("active"),
    })
    if not isinstance(result, dict) or result.get("user_id") != uid or result.get("role") != role or result.get("active") is not active:
        raise ValueError("Role change not confirmed")
    return result
