import unittest
from unittest.mock import patch, Mock

from testing.auth_client import AuthClient, is_test_admin, validate_config

UID = "12345678-1234-1234-1234-123456789abc"


class TestIsolatedAuth(unittest.TestCase):
    def test_privileged_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_config("https://example.supabase.co", "sb_secret_test", [UID])

    def test_admin_requires_server_allowlist(self):
        ids = validate_config("https://example.supabase.co", "sb_publishable_test", [UID])
        self.assertTrue(is_test_admin({"id": UID}, ids))
        self.assertFalse(is_test_admin({"id": "other", "user_metadata": {"role": "admin"}}, ids))
        self.assertFalse(is_test_admin(None, ids))

    def test_missing_admin_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_config("https://example.supabase.co", "sb_publishable_test", [])

    @patch("testing.auth_client.requests.request")
    def test_user_is_verified_by_auth_server(self, request):
        response = Mock(content=b"{}")
        response.json.return_value = {"id": UID}
        request.return_value = response
        client = AuthClient("https://example.supabase.co", "sb_publishable_test")
        self.assertEqual(client.get_user("user-token"), {"id": UID})
        args, kwargs = request.call_args
        self.assertEqual(args, ("GET", "https://example.supabase.co/auth/v1/user"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer user-token")
        response.raise_for_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
