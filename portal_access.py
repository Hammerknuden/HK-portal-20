"""Shared access boundary; production defaults to the existing legacy path."""
import streamlit as st


def uses_supabase_auth():
    mode = st.secrets.get("AUTH_MODE", "legacy")
    if mode not in ("legacy", "supabase"):
        st.error("Ukendt AUTH_MODE.")
        st.stop()
    return mode == "supabase"


def require_test_user(admin=False):
    from testing.auth_client import AuthClient, resolve_role
    if st.secrets.get("APP_ENV") != "test":
        st.error("Supabase-sporet er foreløbig kun til testmiljøet.")
        st.stop()
    token = st.session_state.get("test_auth_access_token")
    try:
        client = AuthClient(st.secrets["SUPABASE_TEST_URL"], st.secrets["SUPABASE_TEST_PUBLISHABLE_KEY"])
        user = client.get_user(token) if token else None
        role = resolve_role(user, st.secrets["TEST_ADMIN_USER_IDS"], st.secrets.get("TEST_USER_IDS", []))
    except Exception:
        user, role = None, None
    if not role or (admin and role != "admin"):
        st.error("Ingen adgang. Log ind via testappens startside med en godkendt bruger.")
        st.stop()
    st.session_state.update(authentication_status=True, username=user["email"], name=user["email"])
    return user


def get_database_client():
    from supabase import create_client, ClientOptions
    if not uses_supabase_auth():
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    require_test_user()
    import httpx

    def read_only(request):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            raise RuntimeError("Testmiljøet er i læsetilstand. Ændringer er ikke aktiveret.")

    token = st.session_state["test_auth_access_token"]
    return create_client(
        st.secrets["SUPABASE_TEST_URL"], st.secrets["SUPABASE_TEST_PUBLISHABLE_KEY"],
        options=ClientOptions(
            headers={"Authorization": "Bearer " + token},
            persist_session=False, auto_refresh_token=False,
            httpx_client=httpx.Client(event_hooks={"request": [read_only]}),
        ),
    )
