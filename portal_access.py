"""Shared access boundary; production defaults to the existing legacy path."""
import streamlit as st

RESTORE_TEST_URL = "https://ycasinssaffzpsyhgzgf.supabase.co"


def is_restore_test():
    return st.secrets.get("APP_ENV") == "restore_test"


def validate_restore_test(required=False):
    if not is_restore_test():
        if required:
            st.error("Testappen krÃ¦ver APP_ENV = restore_test i sine egne Secrets.")
            st.stop()
        return
    if (st.secrets.get("AUTH_MODE", "legacy") != "legacy"
            or st.secrets.get("SUPABASE_URL", "").rstrip("/") != RESTORE_TEST_URL
            or not st.secrets.get("SUPABASE_KEY")
            or not st.secrets.get("RESTORE_TEST_COOKIE_KEY")):
        st.error("Testappen krÃ¦ver legacy-login, backup-testprojektets URL og nÃ¸gle samt RESTORE_TEST_COOKIE_KEY.")
        st.stop()


def suppress_test_email():
    if is_restore_test():
        validate_restore_test()
        st.info("TEST: Mailafsendelse sprunget over. Ingen mail er sendt.")
        return True
    return False


def uses_supabase_auth():
    mode = st.secrets.get("AUTH_MODE", "legacy")
    if mode == "dual":
        mode = st.session_state.get("portal_login_method", "legacy")
    if mode not in ("legacy", "supabase"):
        st.error("Ukendt AUTH_MODE.")
        st.stop()
    return mode == "supabase"


def require_test_user(admin=False):
    from testing.auth_client import AuthClient, resolve_role
    if st.secrets.get("APP_ENV") != "test" and st.secrets.get("AUTH_MODE") != "dual":
        st.error("Supabase-sporet er forelÃ¸big kun til testmiljÃ¸et.")
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


def booking_301_test_enabled():
    if (st.secrets.get("APP_ENV") != "test" or not uses_supabase_auth()
            or st.secrets.get("ENABLE_BOOKING_WRITE_PROBE") is not True
            or st.secrets.get("ENABLE_BOOKING_301_TEST") is not True):
        return False
    require_test_user()
    return True


def get_database_client(allow_booking_comment=False, allow_timeline_test=False, allow_booking_writes=False, allow_guest_upload=False):
    validate_restore_test()
    from supabase import create_client, ClientOptions
    if not uses_supabase_auth():
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    user = require_test_user()
    booking_admin = user["id"] in st.secrets.get("TEST_ADMIN_USER_IDS", [])
    import httpx
    comment_test = allow_booking_comment and booking_comment_test_enabled()
    october_test = (allow_booking_comment or allow_timeline_test) and booking_300_test_enabled()

    create_test = allow_booking_comment and booking_301_test_enabled()

    def read_only(request):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if allow_guest_upload and booking_admin and request.method == "POST":
                import re
                if (re.fullmatch(r"/storage/v1/object/guest-registrations/([0-9]{4})/\1-[0-9]+[.]pdf", request.url.path)
                        and request.headers.get("x-upsert", "false").lower() == "false"):
                    return
            # The statistics RPC is STABLE/SECURITY INVOKER and only reads source rows.
            if (request.method == "POST"
                    and request.url.path == "/rest/v1/rpc/calculate_season_statistics"):
                import json
                try:
                    payload = json.loads(request.content)
                    if (isinstance(payload, dict) and set(payload) == {"p_season"}
                            and type(payload["p_season"]) is int
                            and 1900 <= payload["p_season"] <= 9999):
                        return
                except (ValueError, UnicodeError):
                    pass
            if allow_booking_writes and request.url.path == "/rest/v1/hk_dtb":
                if request.method in ("POST", "PATCH"):
                    return
                if request.method == "DELETE" and booking_admin:
                    return
            if comment_test or october_test or create_test:
                import json
                from urllib.parse import parse_qs
                from testing.write_probe import is_scoped_comment_patch, is_booking_300_patch, is_booking_301_insert
                try:
                    params = parse_qs(request.url.query.decode("utf-8"), keep_blank_values=True)
                    payload = json.loads(request.content)
                    if create_test and is_booking_301_insert(request.method, request.url.path, params, payload):
                        return
                    if comment_test and is_scoped_comment_patch(request.method, request.url.path, params, payload):
                        return
                    if (october_test
                            and is_booking_300_patch(request.method, request.url.path, params, payload,
                                                     timeline=allow_timeline_test)):
                        return
                except (ValueError, UnicodeError):
                    pass
            raise RuntimeError("Denne skrivehandling er ikke aktiveret for din adgang.")

    token = st.session_state["test_auth_access_token"]
    return create_client(
        st.secrets["SUPABASE_TEST_URL"], st.secrets["SUPABASE_TEST_PUBLISHABLE_KEY"],
        options=ClientOptions(
            headers={"Authorization": "Bearer " + token},
            persist_session=False, auto_refresh_token=False,
            httpx_client=httpx.Client(event_hooks={"request": [read_only]}),
        ),
    )
