import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from modules.auth_client import AuthClient, resolve_role
from modules.user_invitation import (
    send_invitation, pending_invitations, invite_portal_user,
    render_invitation, InvitationInputError,
)

UID = "4399ca28-e347-43c5-b22f-6e8be0772f61"

class Stop(BaseException):
    pass


class InvitationTests(unittest.TestCase):
    def settings(self):
        return {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_AUTH_URL": "https://example.supabase.co",
                "SUPABASE_KEY": "server-test-key", "ADMIN_USER_IDS": [], "USER_IDS": [],
                "PASSWORD_RESET_URL": "https://portal.example.com/"}

    def factory(self):
        factory = Mock()
        factory.return_value.auth.admin.list_users.return_value = []
        factory.return_value.auth.admin.invite_user_by_email.return_value.user = SimpleNamespace(id=UID, email="new@example.com")
        return factory

    def state(self):
        st = MagicMock(); st.session_state = {}; st.query_params = {}
        st.stop.side_effect = Stop; st.rerun.side_effect = Stop
        st.button.return_value = False
        return st

    def test_invites_with_name_only_and_no_role(self):
        factory = self.factory()
        self.assertEqual(send_invitation(self.settings(), factory, " New User ", " new@example.com "), UID)
        factory.return_value.auth.admin.invite_user_by_email.assert_called_once_with(
            "new@example.com", options={"redirect_to": "https://portal.example.com/", "data": {"display_name": "New User"}})
        self.assertIsNone(resolve_role({"id": UID, "user_metadata": {"display_name": "New User"}}, [], []))

    def test_duplicate_on_later_page_prevents_send(self):
        factory = self.factory()
        factory.return_value.auth.admin.list_users.side_effect = [
            [SimpleNamespace(email=f"person{i}@example.com") for i in range(100)],
            [SimpleNamespace(email="NEW@example.com")],
        ]
        with self.assertRaises(InvitationInputError):
            send_invitation(self.settings(), factory, "New", "new@example.com")
        factory.return_value.auth.admin.invite_user_by_email.assert_not_called()

    def test_bad_input_does_not_create_client(self):
        for name, email in [("", "new@example.com"), ("a" * 101, "new@example.com"), ("Name", "bad"), ("Name", "a@example.com\nBcc: other@example.com")]:
            factory = self.factory()
            with self.assertRaises(InvitationInputError): send_invitation(self.settings(), factory, name, email)
            factory.assert_not_called()

    def test_project_mismatch_and_bad_redirect_block_send(self):
        for key, value in [("SUPABASE_URL", "https://other.supabase.co"), ("PASSWORD_RESET_URL", "http://localhost/"), ("PASSWORD_RESET_URL", "https://portal.example.com/?token=x")]:
            settings = self.settings(); settings[key] = value
            factory = self.factory()
            with self.assertRaises(ValueError): send_invitation(settings, factory, "New", "new@example.com")
            factory.return_value.auth.admin.invite_user_by_email.assert_not_called()

    def test_pending_list_excludes_existing_portal_users_and_noninvited_accounts(self):
        factory = self.factory(); settings = self.settings(); settings["USER_IDS"] = [UID]
        factory.return_value.auth.admin.list_users.return_value = [
            SimpleNamespace(id=UID, email="active@example.com", invited_at="date", email_confirmed_at="date", user_metadata={}),
            SimpleNamespace(id="pending", email="pending@example.com", invited_at="date", email_confirmed_at="date", user_metadata={"display_name": "New"}),
            SimpleNamespace(id="other", email="other@example.com", invited_at=None, user_metadata={}),
        ]
        self.assertEqual(pending_invitations(settings, factory, members={UID: {"role": "user", "active": True}}), [{"Navn": "New", "E-mail": "pending@example.com", "Status": "Afventer portaladgang", "uid": "pending", "confirmed": True}])

    def test_only_admin_can_send(self):
        auth = Mock(); auth.require_admin.side_effect = PermissionError()
        sdk = Mock()
        with patch.dict("sys.modules", {"auth": auth, "streamlit": Mock(), "portal_access": Mock(), "supabase": sdk}):
            with self.assertRaises(PermissionError): invite_portal_user("Name", "new@example.com")
            sdk.create_client.assert_not_called()

    def test_invitation_link_clears_previous_identity_but_waits_for_click(self):
        st = self.state(); st.session_state = {"auth_access_token": "old", "authentication_status": True}
        st.query_params = {"token_hash": "hash", "type": "invite"}
        client = Mock()
        with self.assertRaises(Stop): render_invitation(st, client)
        self.assertEqual(st.session_state, {"invitation_hash": "hash"})
        self.assertEqual(st.query_params, {})
        client.verify_invitation.assert_not_called()

    def test_accept_stores_separate_session_without_portal_login(self):
        st = self.state(); st.session_state = {"invitation_hash": "hash"}
        st.button.side_effect = lambda label, **kwargs: label == "Accepter invitation"
        client = Mock(); client.verify_invitation.return_value = {"access_token": "invite-token"}
        client.get_user.return_value = {"id": UID, "email": "new@example.com"}
        with self.assertRaises(Stop): render_invitation(st, client)
        self.assertEqual(st.session_state["invitation_access"], "invite-token")
        self.assertNotIn("auth_access_token", st.session_state)
        self.assertNotIn("authentication_status", st.session_state)

    def test_password_save_never_promotes_session(self):
        st = self.state(); st.session_state = {"invitation_access": "invite-token", "invitation_user_id": UID}
        st.text_input.side_effect = ["Abcdefg1", "Abcdefg1"]
        st.form_submit_button.return_value = True
        client = Mock(); client.get_user.return_value = {"id": UID}
        with self.assertRaises(Stop): render_invitation(st, client)
        client.update_password.assert_called_once_with("invite-token", "Abcdefg1")
        client.sign_out.assert_called_once_with("invite-token")
        self.assertEqual(st.session_state, {"invitation_success": True})

    def test_expired_invitation_does_not_create_session(self):
        st = self.state(); st.session_state = {"invitation_hash": "expired"}
        st.button.side_effect = lambda label, **kwargs: label == "Accepter invitation"
        client = Mock(); client.verify_invitation.side_effect = ValueError("expired")
        with self.assertRaises(Stop): render_invitation(st, client)
        self.assertEqual(st.session_state, {"invitation_invalid": True})
        client.update_password.assert_not_called()

    def test_invitation_api_cannot_verify_as_recovery(self):
        client = AuthClient("https://example.supabase.co", "sb_publishable_test")
        with patch.object(client, "_request") as request:
            client.verify_invitation("hash")
            request.assert_called_once_with("POST", "/verify", payload={"token_hash": "hash", "type": "invite"})
