"""Shared access boundary; production defaults to the existing legacy path."""
import streamlit as st
from modules.auth_settings import auth_settings, access_token

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
        mode = st.session_state.get("portal_login_method", "supabase")
    if mode not in ("legacy", "supabase"):
        st.error("Ukendt AUTH_MODE.")
        st.stop()
    return mode == "supabase"


def require_portal_user(admin=False):
    from modules.auth_client import AuthClient, resolve_role
    token = access_token(st.session_state)
    try:
        client = AuthClient(auth_settings(st.secrets)["SUPABASE_AUTH_URL"], auth_settings(st.secrets)["SUPABASE_PUBLISHABLE_KEY"])
        user = client.get_user(token) if token else None
        role = resolve_role(user, auth_settings(st.secrets)["ADMIN_USER_IDS"], auth_settings(st.secrets)["USER_IDS"])
    except Exception:
        user, role = None, None
    if not role or (admin and role != "admin"):
        st.error("Ingen adgang. Log ind via appens startside med en godkendt bruger.")
        st.stop()
    st.session_state.update(authentication_status=True, username=user["email"], name=user["email"])
    return user


# Compatibility for the separately deployed diagnostic app.
require_test_user = require_portal_user

# Retired diagnostic flags; kept as no-op imports for older diagnostic pages.
def booking_comment_test_enabled():
    return False


def booking_300_test_enabled():
    return False


def booking_301_test_enabled():
    return False


def get_database_client(allow_booking_comment=False, allow_timeline_test=False, allow_booking_writes=False, allow_guest_upload=False, allow_setup_writes=False, allow_breakfast_writes=False):
    validate_restore_test()
    from supabase import create_client, ClientOptions
    if not uses_supabase_auth():
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    user = require_portal_user()
    booking_admin = user["id"] in auth_settings(st.secrets)["ADMIN_USER_IDS"]
    import httpx
    def read_only(request):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if (allow_breakfast_writes and request.method in ("POST", "PATCH")
                    and request.url.path == "/rest/v1/breakfast_notes"):
                import json
                try:
                    data = json.loads(request.content)
                    fields = {"dato", "ekstra_gæster", "assistance", "comments"}
                    if isinstance(data, dict) and data and set(data) <= fields:
                        return
                except (ValueError, UnicodeError):
                    pass
            if allow_setup_writes and booking_admin:
                if request.url.path == "/rest/v1/high_season" and request.method == "PATCH":
                    import json
                    try:
                        data = json.loads(request.content)
                        fields = {"enk_low", "enk_high", "dobb_low", "dobb_high", "pris_morgenmad"}
                        if isinstance(data, dict) and data and set(data) <= fields:
                            return
                    except (ValueError, UnicodeError):
                        pass
                if request.url.path == "/rest/v1/Events" and request.method in ("POST", "PATCH", "DELETE"):
                    return
                if request.url.path == "/rest/v1/rpc/close_booking_season_authenticated" and request.method == "POST":
                    return
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
            if (allow_booking_writes and request.method == "POST"
                    and request.url.path in ("/rest/v1/rpc/swap_booking_rooms",
                                            "/rest/v1/rpc/apply_optimizer_plan_authenticated")):
                return
            if allow_booking_writes and request.url.path == "/rest/v1/hk_dtb":
                if request.method in ("POST", "PATCH"):
                    return
                if request.method == "DELETE" and booking_admin:
                    return
            raise RuntimeError("Denne skrivehandling er ikke aktiveret for din adgang.")

    token = access_token(st.session_state)
    return create_client(
        auth_settings(st.secrets)["SUPABASE_AUTH_URL"], auth_settings(st.secrets)["SUPABASE_PUBLISHABLE_KEY"],
        options=ClientOptions(
            headers={"Authorization": "Bearer " + token},
            persist_session=False, auto_refresh_token=False,
            httpx_client=httpx.Client(event_hooks={"request": [read_only]}),
        ),
    )
