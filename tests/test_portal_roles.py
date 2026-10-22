import unittest
from unittest.mock import Mock, patch
from modules.auth_client import AuthClient
from modules.portal_roles import save_member, load_members

class RoleTests(unittest.TestCase):
    def test_no_fallback_on_missing_role_or_rpc_failure(self):
        client = AuthClient("https://example.supabase.co", "sb_publishable_test")
        with patch.object(client, "portal_rpc", return_value=None):
            self.assertIsNone(client.portal_role("token"))
        with patch.object(client, "portal_rpc", side_effect=RuntimeError()):
            with self.assertRaises(RuntimeError): client.portal_role("token")
        with patch.object(client, "portal_rpc", return_value="owner"):
            with self.assertRaises(ValueError): client.portal_role("token")

    def test_role_mutation_uses_user_rpc_and_expected_state(self):
        client = Mock(); client.portal_rpc.return_value = {"user_id": "id", "role": "admin", "active": True}
        with patch("modules.portal_roles.role_client", return_value=(client, "user-token")):
            save_member("id", "admin", True, {"role": "user", "active": True})
        client.portal_rpc.assert_called_once_with("portal_set_member", "user-token", {
            "p_user_id": "id", "p_role": "admin", "p_active": True,
            "p_expected_role": "user", "p_expected_active": True})

    def test_new_member_is_not_silently_overwritten(self):
        client = Mock(); client.portal_rpc.side_effect = RuntimeError("stale")
        with patch("modules.portal_roles.role_client", return_value=(client, "user-token")):
            with self.assertRaises(RuntimeError): save_member("id", "user", True, {})
        self.assertIsNone(client.portal_rpc.call_args.args[2]["p_expected_role"])

    def test_deactivation_result_must_match(self):
        client = Mock(); client.portal_rpc.return_value = {"user_id": "id", "role": "user", "active": True}
        with patch("modules.portal_roles.role_client", return_value=(client, "user-token")):
            with self.assertRaises(ValueError): save_member("id", "user", False, {"role": "user", "active": True})

    def test_bad_roles_never_call_rpc(self):
        with patch("modules.portal_roles.role_client") as factory:
            with self.assertRaises(ValueError): save_member("id", "owner", True, {})
            factory.assert_not_called()

    @patch("modules.auth_client.requests.post")
    def test_rpc_uses_publishable_key_and_user_jwt(self, post):
        post.return_value.json.return_value = "user"
        client = AuthClient("https://example.supabase.co", "sb_publishable_test")
        self.assertEqual(client.portal_role("user-token"), "user")
        self.assertEqual(post.call_args.kwargs["headers"], {"apikey": "sb_publishable_test", "Authorization": "Bearer user-token"})
