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


if __name__ == "__main__":
    unittest.main()
