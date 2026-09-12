import unittest
from unittest.mock import Mock, patch
from testing.auth_client import AuthClient


class TestPasswordRecovery(unittest.TestCase):
    def setUp(self):
        self.client = AuthClient("https://example.supabase.co", "sb_publishable_test")

    @patch.object(AuthClient, "_request")
    def test_request_is_anonymous_and_redirect_is_encoded(self, request):
        self.client.request_password_reset(" user@example.com ", "https://test.streamlit.app/")
        request.assert_called_once_with(
            "POST", "/recover?redirect_to=https%3A%2F%2Ftest.streamlit.app%2F",
            payload={"email": "user@example.com"})

    @patch.object(AuthClient, "_request")
    def test_invalid_redirect_does_not_send(self, request):
        for url in ("http://localhost:3000", "https://test.app/?token=abc"):
            with self.assertRaises(ValueError):
                self.client.request_password_reset("a@b.com", url)
        request.assert_not_called()

    @patch.object(AuthClient, "_request")
    def test_verify_only_recovery_tokens(self, request):
        self.client.verify_recovery("one-time-hash")
        request.assert_called_once_with("POST", "/verify", payload={
            "token_hash": "one-time-hash", "type": "recovery"})

    @patch.object(AuthClient, "_request")
    def test_update_uses_recovered_user_token(self, request):
        self.client.update_password("recovery-session", "Abcdefg1")
        request.assert_called_once_with("PUT", "/user", token="recovery-session",
                                        payload={"password": "Abcdefg1"})

    @patch.object(AuthClient, "_request")
    def test_missing_token_or_short_password_cannot_update(self, request):
        for token, password in [("", "Abcdefg1"), ("token", "Abcdef1"),
                                ("token", "abcdefgh1"), ("token", "ABCDEFGH1"),
                                ("token", "Abcdefgh"), ("token", "abcdefgh!")]:
            with self.assertRaises(ValueError):
                self.client.update_password(token, password)
        request.assert_not_called()

    def test_recovery_route_clears_login_and_url_without_verifying_automatically(self):
        import importlib.util
        from pathlib import Path
        import sys
        st = Mock()
        st.query_params = {"token_hash": "hash", "type": "recovery"}
        st.session_state = {"test_auth_access_token": "old-login", "guest_data": "old-data"}
        class Rerun(BaseException):
            pass
        st.rerun.side_effect = Rerun
        with patch.dict(sys.modules, {"streamlit": st}):
            spec = importlib.util.spec_from_file_location("recovery_test_module", Path(__file__).parents[1] / "testing/password_recovery.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            client = Mock()
            with self.assertRaises(Rerun):
                module.render_recovery(client, ["admin"], [])
            self.assertEqual(st.session_state, {"recovery_hash": "hash"})
            self.assertEqual(st.query_params, {})
            client.verify_recovery.assert_not_called()


if __name__ == "__main__":
    unittest.main()
