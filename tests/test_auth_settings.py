import unittest
from modules.auth_settings import auth_settings

class SettingsTests(unittest.TestCase):
    def test_old_settings_still_work(self):
        values = auth_settings({"SUPABASE_TEST_URL": "old-url", "SUPABASE_TEST_PUBLISHABLE_KEY": "public-key", "TEST_ADMIN_USER_IDS": ["a"], "TEST_USER_IDS": ["u"]})
        self.assertEqual(values, {"SUPABASE_AUTH_URL": "old-url", "SUPABASE_PUBLISHABLE_KEY": "public-key", "ADMIN_USER_IDS": ["a"], "USER_IDS": ["u"]})

    def test_explicit_new_values_win_even_when_empty(self):
        values = auth_settings({"USER_IDS": [], "TEST_USER_IDS": ["old-user"], "SUPABASE_KEY": "privileged-key"})
        self.assertEqual(values["USER_IDS"], [])
        self.assertEqual(values["SUPABASE_PUBLISHABLE_KEY"], "")
