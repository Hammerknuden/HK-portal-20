import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

class LoginTests(unittest.TestCase):
    def test_production_ignores_old_legacy_session(self):
        st = Mock(); st.session_state = {"authentication_status": True, "portal_login_method": "legacy"}
        access = Mock(); access.is_restore_test.return_value = False
        login = Mock()
        with patch.dict("sys.modules", {"streamlit": st, "portal_access": access, "modules.portal_login": login}):
            spec = importlib.util.spec_from_file_location("auth_under_test", Path("auth.py"))
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.require_login()
            login.supabase_login.assert_called_once()

    def test_restore_credentials_missing_stops_login(self):
        st = Mock(); st.secrets = {}
        st.stop.side_effect = RuntimeError("stopped")
        access = Mock(); access.is_restore_test.return_value = True
        sdk = Mock()
        with patch.dict("sys.modules", {"streamlit": st, "portal_access": access, "streamlit_authenticator": sdk}):
            spec = importlib.util.spec_from_file_location("auth_under_test", Path("auth.py"))
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with self.assertRaises(RuntimeError): module.require_login()
            sdk.Authenticate.assert_not_called()
