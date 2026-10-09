import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pandas as pd

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
        self.load = self.stack.enter_context(patch("modules.calendar_save.load_calendar_rows",
                                                  return_value=pd.DataFrame([self.row])))
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

    def test_single_calendar_uses_shared_figure(self):
        app = self.app()
        self.assertEqual(len(app.get("plotly_chart")), 0)
        self.assertEqual(self.render.call_count, 1)
        figure = self.render.call_args.kwargs["figure"]
        self.assertTrue(figure.layout.xaxis.rangeslider.visible)
        self.assertEqual(figure.data[0].y[0], "Værelse 3")
        self.assertFalse(any(title.value == "Afprøv værelsesflytning" for title in app.subheader))

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

    def test_preflight_overlap_restores_saved_position(self):
        neighbour = {**self.row, "id": 2, "booking_number": 222, "room_number": 3}
        self.load.return_value = pd.DataFrame([self.row, neighbour])
        app = self.app()
        self.save_button(app).click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["calendar_moves_2027"], {})
        self.assertEqual(app.session_state["calendar_sources_2027"], {})
        self.assertEqual(self.render.call_args.args[0].room_number.tolist(), [1])
        self.assertTrue(app.error)
        self.save.assert_not_called()

    def test_database_rejection_restores_saved_position(self):
        error = RuntimeError("Overlap at save")
        error.code = "P0001"
        self.save.side_effect = error
        app = self.app()
        self.save_button(app).click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.session_state["calendar_save_pending"])
        self.assertEqual(app.session_state["calendar_moves_2027"], {})
        self.assertEqual(self.render.call_args.args[0].room_number.tolist(), [1])
        self.assertTrue(app.error)

    def test_cancel_button_below_draft_restores_saved_position(self):
        app = self.app()
        next(b for b in app.button if b.label == "Annuller flytninger").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["calendar_moves_2027"], {})
        self.assertEqual(self.render.call_args.args[0].room_number.tolist(), [1])
        self.save.assert_not_called()

    def clean_app(self):
        app = AppTest.from_file("pages/kalender.py")
        app.session_state["calendar_season"] = 2027
        app.run(timeout=30)
        self.assertFalse(app.exception)
        return app

    def test_booking_tools_present_without_what_if(self):
        app = self.clean_app()
        self.assertTrue(any(title.value == "Administrer bookinger" for title in app.subheader))
        self.assertTrue(any(title.value == "Niveau 2 optimering" for title in app.subheader))
        self.assertFalse(any("What if" in checkbox.label for checkbox in app.checkbox))
        self.assertEqual(len(app.get("plotly_chart")), 0)
        self.client.table.return_value.insert.assert_not_called()
        self.client.table.return_value.update.assert_not_called()

    def test_edit_rejection_does_not_write(self):
        app = self.clean_app()
        with patch("modules.calendar_tools.validate_timeline_edit", side_effect=ValueError("Overlap")):
            app.button("calendar_admin_save_1").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("Overlap" in error.value for error in app.error))
        self.client.table.return_value.update.assert_not_called()

    def test_removing_movable_saves_locked_booking(self):
        table = self.client.table.return_value
        table.select.return_value.order.return_value.range.return_value.execute.return_value.data = [self.row.copy()]
        locked = {**self.row, "movable": False}
        table.update.return_value.eq.return_value.execute.return_value.data = [locked]
        app = self.clean_app()
        app.checkbox("calendar_admin_movable_1").uncheck()
        # The next page load reads the persisted lock from the database.
        table.select.return_value.eq.return_value.execute.return_value.data = [locked]
        app.button("calendar_admin_save_1").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.error, [error.value for error in app.error])
        table.update.assert_called_once()
        self.assertIs(table.update.call_args.args[0]["movable"], False)
        self.assertTrue(any("Ændringer gemt" in success.value for success in app.success))
        self.assertFalse(self.render.call_args.args[0].iloc[0].movable)

    def test_single_booking_swap_has_no_partner(self):
        app = self.clean_app()
        app.button("calendar_admin_open_swap_1").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("Ingen anden booking" in info.value for info in app.info))
        self.client.table.return_value.update.assert_not_called()

    def test_optimizer_state_does_not_clear_timeline_selection(self):
        from modules.calendar_tools import CalendarToolState
        from modules.optimizer_workflow import clear_selection
        original = {"optimizer_choice": {"source": "timeline"},
                    "calendar_tools_optimizer_choice": {"source": "calendar"}}
        clear_selection(CalendarToolState(original))
        self.assertEqual(original["optimizer_choice"], {"source": "timeline"})
        self.assertNotIn("calendar_tools_optimizer_choice", original)


if __name__ == "__main__":
    unittest.main()
