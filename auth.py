"""Supabase login for the portal; isolated secret-based login for restore testing."""
import streamlit as st
from portal_access import is_restore_test, validate_restore_test


def _restore_authenticator():
    validate_restore_test(required=True)
    import streamlit_authenticator as stauth
    credentials = st.secrets.get("RESTORE_CREDENTIALS")
    if not credentials or not credentials.get("usernames"):
        st.error("Restore-testappen mangler RESTORE_CREDENTIALS i sine egne Secrets.")
        st.stop()
    # Convert nested Secrets mappings to ordinary dictionaries for the authenticator.
    users = {username: dict(values) for username, values in credentials["usernames"].items()}
    return stauth.Authenticate({"usernames": users}, "hk_restore_login_v2",
                              st.secrets["RESTORE_TEST_COOKIE_KEY"], cookie_expiry_days=1)


def require_login():
    if not is_restore_test():
        from modules.portal_login import supabase_login
        supabase_login()
        return
    authenticator = _restore_authenticator()
    authenticator.login(location="main")
    if st.session_state.get("authentication_status") is not True:
        st.info("Log ind med restore-testappens bruger.")
        st.stop()
    authenticator.logout("Log ud", "sidebar")


def is_admin():
    if not is_restore_test():
        from portal_access import require_portal_user
        user = require_portal_user()
        return user["portal_role"] == "admin"
    validate_restore_test(required=True)
    return (st.session_state.get("authentication_status") is True
            and st.session_state.get("username") in st.secrets.get("RESTORE_ADMIN_USERNAMES", []))


def require_admin():
    if not is_restore_test():
        from portal_access import require_portal_user
        require_portal_user(admin=True)
        return
    if not is_admin():
        st.error("Kun administratorer har adgang til denne side.")
        st.stop()
