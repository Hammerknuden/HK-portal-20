"""Shared access boundary; production defaults to the existing legacy path."""
import streamlit as st

RESTORE_TEST_URL = "https://ycasinssaffzpsyhgzgf.supabase.co"


def is_restore_test():
    return st.secrets.get("APP_ENV") == "restore_test"


def validate_restore_test(required=False):
    if not is_restore_test():
        if required:
            st.error("Testappen kræver APP_ENV = restore_test i sine egne Secrets.")
            st.stop()
        return
    if (st.secrets.get("AUTH_MODE", "legacy") != "legacy"
            or st.secrets.get("SUPABASE_URL", "").rstrip("/") != RESTORE_TEST_URL
            or not st.secrets.get("SUPABASE_KEY")
            or not st.secrets.get("RESTORE_TEST_COOKIE_KEY")):
        st.error("Testappen kræver legacy-login, backup-testprojektets URL og nøgle samt RESTORE_TEST_COOKIE_KEY.")
        st.stop()


def suppress_test_email():
    if is_restore_test():
        validate_restore_test()
        st.info("TEST: Mailafsendelse sprunget over. Ingen mail er sendt.")
        return True
    return False


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


def booking_comment_test_enabled():
    if (st.secrets.get("APP_ENV") != "test" or not uses_supabase_auth()
            or st.secrets.get("ENABLE_BOOKING_WRITE_PROBE") is not True):
        return False
    user = require_test_user()
    return user["id"] in st.secrets.get("TEST_ADMIN_USER_IDS", [])


def booking_300_test_enabled():
    if (st.secrets.get("APP_ENV") != "test" or not uses_supabase_auth()
            or st.secrets.get("ENABLE_BOOKING_WRITE_PROBE") is not True
            or st.secrets.get("ENABLE_BOOKING_300_TEST") is not True):
        return False
    require_test_user()
    return True


def get_database_client(allow_booking_comment=False):
    validate_restore_test()
    from supabase import create_client, ClientOptions
    if not uses_supabase_auth():
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    require_test_user()
    import httpx
    comment_test = allow_booking_comment and booking_comment_test_enabled()
    october_test = allow_booking_comment and booking_300_test_enabled()

    def read_only(request):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if comment_test or october_test:
                import json
                from urllib.parse import parse_qs
                from testing.write_probe import is_scoped_comment_patch, is_booking_300_patch
                try:
                    params = parse_qs(request.url.query.decode("utf-8"), keep_blank_values=True)
                    payload = json.loads(request.content)
                    if comment_test and is_scoped_comment_patch(request.method, request.url.path, params, payload):
                        return
                    if (october_test
                            and is_booking_300_patch(request.method, request.url.path, params, payload)):
                        return
                except (ValueError, UnicodeError):
                    pass
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
