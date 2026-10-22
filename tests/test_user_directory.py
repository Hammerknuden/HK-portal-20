import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from modules.user_directory import read_directory, load_user_directory, update_display_name, save_user_display_name

UID = "c8fb3b6c-00ed-4883-a52f-ef182f10ec3e"

class DirectoryTests(unittest.TestCase):
    def members(self):
        return {UID: {"role": "user", "active": True}}

    def settings(self):
        return {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_AUTH_URL": "https://example.supabase.co/",
                "SUPABASE_KEY": "server-test-key", "ADMIN_USER_IDS": [], "USER_IDS": [UID]}

    def test_profile_role_cannot_grant_admin(self):
        factory = Mock()
        factory.return_value.auth.admin.get_user_by_id.return_value.user = SimpleNamespace(
            id=UID, email="user@example.com", user_metadata={"display_name": " Finn ", "role": "admin"})
        self.assertEqual(read_directory(self.settings(), factory, members=self.members()), [
            {"Navn": "Finn", "E-mail": "user@example.com", "Rolle": "Almindelig bruger", "Status": "Aktiv"}])
        factory.return_value.auth.admin.get_user_by_id.assert_called_once_with(UID)

    def test_admin_wins_and_duplicate_ids_are_read_once(self):
        settings = self.settings(); settings["ADMIN_USER_IDS"] = [UID]
        factory = Mock()
        factory.return_value.auth.admin.get_user_by_id.return_value.user = SimpleNamespace(
            id=UID, email="user@example.com", user_metadata={})
        rows = read_directory(settings, factory, members={UID: {"role": "admin", "active": True}})
        self.assertEqual(rows[0]["Rolle"], "Administrator")
        self.assertEqual(rows[0]["Navn"], "Navn mangler")
        factory.return_value.auth.admin.get_user_by_id.assert_called_once()

    def test_project_mismatch_or_invalid_uid_stops_before_client_creation(self):
        for field, value in [("SUPABASE_URL", "https://other.supabase.co")]:
            settings = self.settings(); settings[field] = value
            factory = Mock()
            with self.assertRaises(ValueError): read_directory(settings, factory, members={UID: {"role": "admin", "active": True}})
            factory.assert_not_called()

    def test_denied_admin_never_creates_privileged_client(self):
        auth = Mock(); auth.require_admin.side_effect = PermissionError()
        sdk = Mock()
        with patch.dict("sys.modules", {"auth": auth, "streamlit": Mock(), "portal_access": Mock(), "supabase": sdk}):
            with self.assertRaises(PermissionError): load_user_directory()
            sdk.create_client.assert_not_called()

    def test_name_update_preserves_metadata_and_reads_back(self):
        factory = Mock()
        before = SimpleNamespace(id=UID, user_metadata={"display_name": "Old", "other": "keep"})
        after = SimpleNamespace(id=UID, user_metadata={"display_name": "Finn", "other": "keep"})
        factory.return_value.auth.admin.get_user_by_id.side_effect = [SimpleNamespace(user=before), SimpleNamespace(user=after)]
        self.assertEqual(update_display_name(self.settings(), factory, UID, " Finn ", members=self.members()), "Finn")
        factory.return_value.auth.admin.update_user_by_id.assert_called_once_with(
            UID, {"user_metadata": {"display_name": "Finn", "other": "keep"}})

    def test_invalid_names_and_unknown_users_never_write(self):
        for uid, name in [(UID, " "), (UID, "a" * 101), ("74acf117-be21-4460-877d-4f50993ac6da", "Test")]:
            factory = Mock()
            with self.assertRaises(ValueError): update_display_name(self.settings(), factory, uid, name, members=self.members())
            factory.assert_not_called()

    def test_save_requires_admin_again(self):
        auth = Mock(); auth.require_admin.side_effect = PermissionError()
        sdk = Mock()
        with patch.dict("sys.modules", {"auth": auth, "streamlit": Mock(), "portal_access": Mock(), "supabase": sdk}):
            with self.assertRaises(PermissionError): save_user_display_name(UID, "Finn")
            sdk.create_client.assert_not_called()

    def test_unconfirmed_update_is_not_reported_as_success(self):
        factory = Mock()
        factory.return_value.auth.admin.get_user_by_id.return_value.user = SimpleNamespace(id=UID, user_metadata={"display_name": "Old"})
        with self.assertRaises(ValueError): update_display_name(self.settings(), factory, UID, "Finn", members=self.members())

    def test_reset_uses_fresh_account_email(self):
        from modules.user_directory import send_user_password_reset
        st = Mock(); st.secrets = {"SUPABASE_AUTH_URL": "https://example.supabase.co", "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test", "PASSWORD_RESET_URL": "https://portal.example.com/"}
        rows = [{"uid": UID, "E-mail": "current@example.com", "membership": {"active": True}}]
        with patch.dict("sys.modules", {"streamlit": st}), patch("modules.user_directory.load_user_directory", return_value=rows) as load, patch("modules.auth_client.AuthClient.request_password_reset") as send:
            self.assertEqual(send_user_password_reset(UID), "current@example.com")
            load.assert_called_once_with(include_ids=True)
            send.assert_called_once_with("current@example.com", "https://portal.example.com/")

    def test_reset_rejects_disabled_missing_or_unauthorized_user(self):
        from modules.user_directory import send_user_password_reset
        for rows in ([], [{"uid": UID, "E-mail": "user@example.com", "membership": {"active": False}}]):
            with patch.dict("sys.modules", {"streamlit": Mock()}), patch("modules.user_directory.load_user_directory", return_value=rows), patch("modules.auth_client.AuthClient.request_password_reset") as send:
                with self.assertRaises(ValueError): send_user_password_reset(UID)
                send.assert_not_called()
        with patch.dict("sys.modules", {"streamlit": Mock()}), patch("modules.user_directory.load_user_directory", side_effect=PermissionError()), patch("modules.auth_client.AuthClient.request_password_reset") as send:
            with self.assertRaises(PermissionError): send_user_password_reset(UID)
            send.assert_not_called()
