import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from testing.auth_client import resolve_role


class Stopped(BaseException):
    pass


class TestPortalAccess(unittest.TestCase):
    def setUp(self):
        self.st = Mock()
        self.st.secrets = {}
        self.st.session_state = {}
        self.st.stop.side_effect = Stopped
        self.sdk = Mock()
        self.httpx = Mock()
        self.modules = patch.dict(sys.modules, {
            "streamlit": self.st, "supabase": self.sdk, "httpx": self.httpx,
        })
        self.modules.start()
        spec = importlib.util.spec_from_file_location("access_under_test", Path(__file__).parents[1] / "portal_access.py")
        self.access = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.access)

    def tearDown(self):
        self.modules.stop()

    def test_legacy_remains_default(self):
        self.st.secrets = {"SUPABASE_URL": "legacy-url", "SUPABASE_KEY": "legacy-key"}
        self.access.get_database_client()
        self.sdk.create_client.assert_called_once_with("legacy-url", "legacy-key")

    def configure_restore(self):
        self.st.secrets = {"APP_ENV": "restore_test", "AUTH_MODE": "legacy",
                           "SUPABASE_URL": self.access.RESTORE_TEST_URL,
                           "SUPABASE_KEY": "test-only", "RESTORE_TEST_COOKIE_KEY": "separate-cookie"}

    def test_restore_uses_only_fixed_test_project(self):
        self.configure_restore()
        self.access.get_database_client()
        self.sdk.create_client.assert_called_once_with(self.access.RESTORE_TEST_URL, "test-only")

    def test_restore_rejects_production_and_wrong_auth_mode(self):
        for name, value in (("SUPABASE_URL", "https://production.supabase.co"),
                            ("AUTH_MODE", "supabase"), ("RESTORE_TEST_COOKIE_KEY", "")):
            self.configure_restore()
            self.st.secrets[name] = value
            with self.assertRaises(Stopped):
                self.access.get_database_client()
        self.sdk.create_client.assert_not_called()

    def test_restore_entrypoint_requires_explicit_environment(self):
        with self.assertRaises(Stopped):
            self.access.validate_restore_test(required=True)

    def test_mail_suppressed_only_in_restore_test(self):
        self.assertFalse(self.access.suppress_test_email())
        self.configure_restore()
        self.assertTrue(self.access.suppress_test_email())

    def test_both_mail_functions_skip_smtp_in_restore_test(self):
        import ast
        self.configure_restore()
        for filename in ("data_email.py", "confirmation_email.py"):
            tree = ast.parse((Path(__file__).parents[1] / "config" / filename).read_text(encoding="utf-8"))
            function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "send_email")
            smtp = Mock()
            namespace = {"smtplib": smtp, "ssl": Mock(), "smtp_server": "unused", "port": 587, "admin_email": "unused"}
            with patch.dict(sys.modules, {"portal_access": self.access}):
                exec(compile(ast.Module(body=[function], type_ignores=[]), filename, "exec"), namespace)
                namespace["send_email"]("unused-password", Mock())
            smtp.SMTP.assert_not_called()

    def test_unknown_mode_stops(self):
        self.st.secrets = {"AUTH_MODE": "typo"}
        with self.assertRaises(Stopped):
            self.access.get_database_client()
        self.sdk.create_client.assert_not_called()

    def configure_test(self):
        self.st.secrets = {"AUTH_MODE": "supabase", "APP_ENV": "test",
                           "SUPABASE_TEST_URL": "https://test.supabase.co",
                           "SUPABASE_TEST_PUBLISHABLE_KEY": "sb_publishable_test",
                           "TEST_ADMIN_USER_IDS": ["admin"], "TEST_USER_IDS": ["ordinary"]}
        self.st.session_state = {"test_auth_access_token": "user-token"}

    @patch("testing.auth_client.AuthClient.get_user")
    def test_ordinary_user_cannot_pass_admin_guard(self, get_user):
        self.configure_test()
        get_user.return_value = {"id": "ordinary", "email": "user@example.com"}
        self.access.require_test_user()
        with self.assertRaises(Stopped):
            self.access.require_test_user(admin=True)

    @patch("testing.auth_client.AuthClient.get_user")
    def test_test_client_uses_user_token_and_blocks_writes(self, get_user):
        self.configure_test()
        get_user.return_value = {"id": "ordinary", "email": "user@example.com"}
        self.access.get_database_client()
        options = self.sdk.ClientOptions.call_args.kwargs
        self.assertEqual(options["headers"]["Authorization"], "Bearer user-token")
        self.assertEqual(self.sdk.create_client.call_args.args[1], "sb_publishable_test")
        hook = self.httpx.Client.call_args.kwargs["event_hooks"]["request"][0]
        hook(Mock(method="GET"))
        for method in ("POST", "PATCH", "DELETE", "PUT"):
            with self.assertRaises(RuntimeError):
                hook(Mock(method=method))

    def test_only_explicit_users_have_roles(self):
        self.assertEqual(resolve_role({"id": "ordinary"}, ["admin"], ["ordinary"]), "user")
        self.assertEqual(resolve_role({"id": "admin"}, ["admin"], []), "admin")
        self.assertIsNone(resolve_role({"id": "stranger", "user_metadata": {"role": "admin"}}, ["admin"], []))

    @patch("testing.auth_client.AuthClient.get_user")
    def test_comment_exception_requires_admin_flag_and_explicit_client_option(self, get_user):
        import json
        from urllib.parse import urlencode
        from testing.write_probe import TEST_NAME
        self.configure_test()
        self.st.secrets["ENABLE_BOOKING_WRITE_PROBE"] = True
        self.st.secrets["ENABLE_BOOKING_300_TEST"] = True
        query = urlencode({"id": "eq.217", "season": "eq.2099", "booking_number": "eq.99999",
                           "navn": "eq." + TEST_NAME, "web": "eq.cansl"}).encode()
        request = Mock(method="PATCH", content=json.dumps({"comments": "Test"}).encode())
        request.url.path = "/rest/v1/hk_dtb"
        request.url.query = query
        for uid, flag, option, permitted in [("admin", True, True, True),
                                            ("ordinary", True, True, False),
                                            ("admin", False, True, False),
                                            ("admin", True, False, False)]:
            get_user.return_value = {"id": uid, "email": "user@example.com"}
            self.st.secrets["ENABLE_BOOKING_WRITE_PROBE"] = flag
            self.access.get_database_client(allow_booking_comment=option)
            hook = self.httpx.Client.call_args.kwargs["event_hooks"]["request"][0]
            if permitted:
                hook(request)
            else:
                with self.assertRaises(RuntimeError):
                    hook(request)


    @patch("testing.auth_client.AuthClient.get_user")
    def test_booking_300_allows_approved_users_only_with_flags_and_page_opt_in(self, get_user):
        import json
        from urllib.parse import urlencode
        self.configure_test()
        payload = dict.fromkeys(["booking_number", "familie_navn", "email", "telefon",
            "checkin_date", "checkout_date", "nation", "web", "ankomst", "bed",
            "morgenmad", "room_number", "season"], "")
        payload.update(booking_number="300", season="2026",
                       checkin_date="2026-10-01", checkout_date="2026-10-04")
        request = Mock(method="PATCH", content=json.dumps(payload).encode())
        request.url.path = "/rest/v1/hk_dtb"
        request.url.query = urlencode({"id": "eq.218", "season": "eq.2026",
            "booking_number": "eq.300", "navn": "eq.NN"}).encode()
        for uid, probe, october, option, permitted in [
            ("ordinary", True, True, True, True), ("admin", True, True, True, True),
            ("ordinary", False, True, True, False), ("ordinary", True, False, True, False),
            ("ordinary", True, True, False, False)]:
            with self.subTest(uid=uid, probe=probe, october=october, option=option):
                get_user.return_value = {"id": uid, "email": "user@example.com"}
                self.st.secrets.update(ENABLE_BOOKING_WRITE_PROBE=probe,
                                       ENABLE_BOOKING_300_TEST=october)
                self.access.get_database_client(allow_booking_comment=option)
                hook = self.httpx.Client.call_args.kwargs["event_hooks"]["request"][0]
                if permitted:
                    hook(request)
                    for method in ("POST", "DELETE"):
                        with self.assertRaises(RuntimeError):
                            hook(Mock(method=method, url=request.url, content=request.content))
                else:
                    with self.assertRaises(RuntimeError):
                        hook(request)
        get_user.return_value = {"id": "stranger", "email": "user@example.com"}
        with self.assertRaises(Stopped):
            self.access.get_database_client(allow_booking_comment=True)

    @patch("testing.auth_client.AuthClient.get_user")
    def test_timeline_300_allows_approved_users_only_with_flags_and_page_opt_in(self, get_user):
        import json
        from urllib.parse import urlencode
        self.configure_test()
        payload = {"room_number": 7, "checkin_date": "2026-10-01",
                   "checkout_date": "2026-10-04", "booking_number": 300,
                   "navn": "NN", "web": "dir", "comments": "Test", "movable": True}
        request = Mock(method="PATCH", content=json.dumps(payload).encode())
        request.url.path = "/rest/v1/hk_dtb"
        request.url.query = urlencode({"id": "eq.218", "season": "eq.2026",
            "booking_number": "eq.300", "navn": "eq.NN"}).encode()
        for uid, probe, october, option, permitted in [
            ("ordinary", True, True, True, True), ("admin", True, True, True, True),
            ("ordinary", False, True, True, False), ("ordinary", True, False, True, False),
            ("ordinary", True, True, False, False)]:
            with self.subTest(uid=uid, probe=probe, october=october, option=option):
                get_user.return_value = {"id": uid, "email": "user@example.com"}
                self.st.secrets.update(ENABLE_BOOKING_WRITE_PROBE=probe,
                                       ENABLE_BOOKING_300_TEST=october)
                self.access.get_database_client(allow_timeline_test=option)
                hook = self.httpx.Client.call_args.kwargs["event_hooks"]["request"][0]
                if permitted:
                    hook(request)
                    for method in ("POST", "DELETE"):
                        with self.assertRaises(RuntimeError):
                            hook(Mock(method=method, url=request.url, content=request.content))
                else:
                    with self.assertRaises(RuntimeError):
                        hook(request)
        get_user.return_value = {"id": "stranger", "email": "user@example.com"}
        with self.assertRaises(Stopped):
            self.access.get_database_client(allow_timeline_test=True)


if __name__ == "__main__":
    unittest.main()
