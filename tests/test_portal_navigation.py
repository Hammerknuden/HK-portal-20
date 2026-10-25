"""Navigation must initialize even when a new session opens a direct page URL."""
from pathlib import Path
import runpy
import unittest
from unittest.mock import Mock, patch

from streamlit.runtime.pages_manager import PagesManager


class PortalNavigationTests(unittest.TestCase):
    def test_fresh_session_uses_entrypoint_for_direct_links(self):
        with patch.object(PagesManager, "uses_pages_directory", None):
            manager = PagesManager(str(Path("app.py").resolve()))
            self.assertFalse(manager.uses_pages_directory)

    def test_navigation_is_registered_before_selected_page_login(self):
        st = Mock()
        st.Page.side_effect = lambda source, **kwargs: (source, kwargs)
        auth = Mock()
        with patch.dict("sys.modules", {"streamlit": st, "auth": auth}):
            runpy.run_path("app.py")
        auth.require_login.assert_not_called()
        st.navigation.return_value.run.assert_called_once_with()
        pages = st.navigation.call_args.args[0]
        self.assertEqual([options["title"] for _, options in pages], [
            "Start", "Booking", "Kalender", "Opslag", "In & Out",
            "Breakfast", "Links", "Statistik", "Afstemning", "Setup",
        ])
        for source, _ in pages[1:]:
            self.assertTrue(Path(source).is_file())
            self.assertEqual(Path(source).parent, Path("portal_pages"))


if __name__ == "__main__":
    unittest.main()
