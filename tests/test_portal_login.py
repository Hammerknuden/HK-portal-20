import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

class Rerun(BaseException): pass
class LoginTransitionTests(unittest.TestCase):
    def test_switch_clears_previous_identity_and_logs_out_legacy(self):
        st=Mock(); st.query_params={}; st.session_state={'portal_login_method':'legacy','authentication_status':True,'guest_data':'old'}
        st.sidebar.radio.return_value='supabase'; st.rerun.side_effect=Rerun
        with patch.dict('sys.modules',{'streamlit':st}):
            spec=importlib.util.spec_from_file_location('login_transition',Path('modules/portal_login.py'))
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            auth=Mock()
            with self.assertRaises(Rerun): module.choose_login(auth)
            auth.logout.assert_called_once_with(location='unrendered')
            self.assertEqual(st.session_state,{'portal_login_method':'supabase'})
    def test_same_method_preserves_session(self):
        st=Mock(); st.query_params={}; st.session_state={'portal_login_method':'legacy','authentication_status':True}
        st.sidebar.radio.return_value='legacy'
        with patch.dict('sys.modules',{'streamlit':st}):
            spec=importlib.util.spec_from_file_location('login_transition',Path('modules/portal_login.py'))
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            auth=Mock(); module.choose_login(auth)
            auth.logout.assert_not_called(); self.assertTrue(st.session_state['authentication_status'])

    def test_new_session_defaults_to_secure_login(self):
        st = Mock(); st.query_params = {}; st.session_state = {}
        st.sidebar.radio.return_value = 'supabase'
        with patch.dict('sys.modules', {'streamlit': st}):
            spec = importlib.util.spec_from_file_location('login_transition', Path('modules/portal_login.py'))
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            auth = Mock(); module.choose_login(auth)
            args, kwargs = st.sidebar.radio.call_args
            self.assertEqual(args[1], ['supabase', 'legacy'])
            self.assertEqual(kwargs['index'], 0)
            self.assertEqual(kwargs['format_func']('supabase'), 'Secure login')
            self.assertEqual(st.session_state['portal_login_method'], 'supabase')
            auth.logout.assert_not_called()
            st.rerun.assert_not_called()

    def test_recovery_link_routes_before_legacy_choice(self):
        st = Mock(); st.query_params = {"token_hash": "recovery-hash", "type": "recovery"}
        st.session_state = {"portal_login_method": "legacy"}
        with patch.dict('sys.modules', {'streamlit': st}):
            spec = importlib.util.spec_from_file_location('login_transition', Path('modules/portal_login.py'))
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with patch.object(module, 'supabase_login') as login:
                module.choose_login(Mock())
                login.assert_called_once()
                st.sidebar.radio.assert_not_called()
