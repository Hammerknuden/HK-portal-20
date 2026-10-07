import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest


class CalendarPageTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id=1, season=2027, booking_number=145, room_number=1,
                        movable=True, checkin_date="2027-06-01", checkout_date="2027-06-05")
        self.client = MagicMock()
        self.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [self.row]
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("auth.require_login"))
        self.stack.enter_context(patch("portal_access.get_database_client", return_value=self.client))
        self.stack.enter_context(patch("portal_access.uses_supabase_auth", return_value=False))
        # AppTest has no browser frontend for custom components. Test page flow
        # with its renderer stubbed; real mounting has a separate smoke check.
        self.render = self.stack.enter_context(patch("modules.calendar_drag.render_drag_calendar"))
        self.stack.enter_context(patch("modules.calendar_save.load_calendar_rows",
                                       return_value=__import__("pandas").DataFrame([self.row])))
        self.save = self.stack.enter_context(patch("modules.calendar_save.save_move_request"))

    def app(self, season=2027):
        app = AppTest.from_file("pages/kalender.py")
        app.session_state["calendar_season"] = season
        app.session_state[f"calendar_moves_{season}"] = {"1": 3}
        app.session_state[f"calendar_sources_{season}"] = {"1": self.row.copy()}
        app.run(timeout=30)
        self.assertFalse(app.exception)
        return app

    def save_button(self, app):
        return next(button for button in app.button if button.label == "Gem flytninger i 2027")

    def test_save_only_enabled_in_2027(self):
        app = self.app(season=2026)
        self.assertTrue(self.save_button(app).disabled)
        self.save.assert_not_called()

    def test_success_clears_draft_after_readback(self):
        app = self.app()
        self.save_button(app).click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["calendar_moves_2027"], {})
        self.assertFalse(app.session_state["calendar_save_pending"])
        self.assertTrue(app.success)
        self.save.assert_called_once()

    def test_uncertain_save_freezes_draft_and_retries_same_request(self):
        self.save.side_effect = RuntimeError("Connection lost")
        app = self.app()
        self.save_button(app).click().run(timeout=30)
        self.assertFalse(app.exception)
        request = app.session_state["calendar_save_request"].copy()
        self.assertTrue(app.session_state["calendar_save_pending"])
        self.assertTrue(app.selectbox[0].disabled)
        self.assertTrue(next(b for b in app.button if b.label == "Nulstil flytninger").disabled)
        self.assertTrue(self.render.call_args.kwargs["disabled"])
        self.save.side_effect = None
        self.save_button(app).click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(self.save.call_args.args[1], request)
        self.assertFalse(app.session_state["calendar_save_pending"])

    def test_missing_rpc_keeps_draft_and_releases_pending(self):
        error = RuntimeError("Not installed")
        error.code = "PGRST202"
        self.save.side_effect = error
        app = self.app()
        self.save_button(app).click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["calendar_save_pending"])
        self.assertEqual(app.session_state["calendar_moves_2027"], {"1": 3})
        self.assertTrue(app.error)


if __name__ == "__main__":
    unittest.main()
