from copy import deepcopy
from datetime import date
from unittest.mock import Mock, patch
import unittest

import pandas as pd

from test_level2_optimizer import booking, preview, workflow


TODAY = date(2026, 9, 17)


class Rerun(BaseException):
    pass


class OptimizerPreviewTests(unittest.TestCase):
    def setUp(self):
        self.rows = pd.DataFrame([
            booking(1, 7), booking(2, 1, start=22, end=26),
            booking(3, 2, start=19, end=22, movable=False),
        ])
        self.plan = {"candidate_id": 1, "target_room": 1, "moves": []}
        for identifier, destination in ((2, 2), (1, 1)):
            row = self.rows[self.rows["id"] == identifier].iloc[0]
            self.plan["moves"].append({
                "id": identifier, "booking_number": int(row["booking_number"]),
                "from_room": int(row["room_number"]), "to_room": destination,
                "checkin_date": row["checkin_date"].date().isoformat(),
                "checkout_date": row["checkout_date"].date().isoformat(),
            })
        self.choice = preview.select_plan(self.plan, 2026)
        self.st = Mock()
        self.st.session_state = {"optimizer_choice": self.choice}
        self.st.rerun.side_effect = Rerun
        self.client = Mock()
        self.loader = Mock(return_value=self.rows)

    def render(self, pressed=None, read_only=False, season=2026):
        self.st.button.side_effect = lambda label, **kw: not kw.get("disabled", False) and kw.get("key") == pressed
        with patch.object(preview, "booking_today", return_value=TODAY), \
             patch.object(workflow, "preview_figure", return_value="figure"):
            try:
                workflow.render_selected_solution(self.st, self.client, season, self.loader, read_only=read_only)
            except Rerun:
                pass

    def prepare_preview(self):
        self.render("optimizer_preview_button")
        self.assertIn("optimizer_preview", self.st.session_state)

    def saved_response(self):
        return {"request_id": self.choice["request_id"], "status": "saved", "moved_count": 2}

    def test_selection_is_independent_copy(self):
        self.plan["moves"][0]["to_room"] = 5
        self.assertEqual(self.choice["plan"]["moves"][0]["to_room"], 2)

    def test_preview_moves_entire_stays_and_keeps_unchanged_neighbour(self):
        before = self.rows.copy(deep=True)
        plan_before = deepcopy(self.choice)
        p = preview.build_preview(self.rows, self.choice, TODAY)
        pd.testing.assert_frame_equal(self.rows, before)
        self.assertEqual(self.choice, plan_before)
        frame = p["timeline"]
        self.assertEqual(set(frame["id"]), {1, 2, 3})
        after = frame[frame["Visning"] == "Efter (forslag)"].set_index("id")
        self.assertEqual(after["room_number"].to_dict(), {1: 1, 2: 2, 3: 2})
        self.assertEqual(after.loc[3, "Ændring"], "Uændret")
        for _, row in self.rows.iterrows():
            self.assertEqual(after.loc[row["id"], "checkin_date"], row["checkin_date"])
            self.assertEqual(after.loc[row["id"], "checkout_date"], row["checkout_date"])

    def test_preview_rejects_stale_lock_and_season(self):
        for column, value in (("movable", False), ("season", 2027)):
            changed = self.rows.copy()
            changed.loc[changed["id"] == 2, column] = value
            with self.assertRaises(ValueError):
                preview.build_preview(changed, self.choice, TODAY)

    def test_select_and_preview_do_not_write(self):
        self.render()
        self.client.rpc.assert_not_called()
        self.prepare_preview()
        self.client.rpc.assert_not_called()

    def test_cancel_preview_discards_only_local_state(self):
        self.prepare_preview()
        self.render("optimizer_cancel")
        self.assertNotIn("optimizer_choice", self.st.session_state)
        self.assertNotIn("optimizer_preview", self.st.session_state)
        self.client.rpc.assert_not_called()

    def test_save_only_after_preview_and_calls_one_rpc(self):
        self.render("optimizer_save")
        self.client.rpc.assert_not_called()
        self.prepare_preview()
        self.client.rpc.return_value.execute.return_value.data = self.saved_response()
        self.render("optimizer_save")
        self.client.rpc.assert_called_once()
        self.assertEqual(self.client.rpc.call_args.args[0], "apply_optimizer_plan")
        self.assertEqual(len(self.client.rpc.call_args.args[1]["p_moves"]), 2)
        self.assertNotIn("optimizer_preview", self.st.session_state)
        self.assertIn("optimizer_saved_message", self.st.session_state)
        self.st.cache_data.clear.assert_called_once()

    def test_supabase_save_uses_authenticated_endpoint_and_same_request_id(self):
        self.prepare_preview()
        prepared = self.st.session_state["optimizer_preview"]
        self.client.rpc.return_value.execute.return_value.data = self.saved_response()
        for _ in range(2):
            preview.save_preview(self.client, prepared, rpc_name="apply_optimizer_plan_authenticated")
        self.assertEqual(self.client.rpc.call_args_list[0], self.client.rpc.call_args_list[1])
        self.assertEqual(self.client.rpc.call_args.args[0], "apply_optimizer_plan_authenticated")
        self.client.table.assert_not_called()

    def test_network_failure_keeps_request_and_disables_cancel_until_retry(self):
        self.prepare_preview()
        self.client.rpc.return_value.execute.side_effect = TimeoutError()
        self.render("optimizer_save")
        self.assertTrue(self.st.session_state["optimizer_preview"]["save_pending"])
        self.render("optimizer_cancel")
        self.assertIn("optimizer_preview", self.st.session_state)
        self.client.rpc.return_value.execute.side_effect = None
        self.client.rpc.return_value.execute.return_value.data = self.saved_response()
        self.render("optimizer_save")
        self.assertEqual(self.client.rpc.call_args_list[0], self.client.rpc.call_args_list[1])
        self.assertNotIn("optimizer_preview", self.st.session_state)

    def test_definite_rejection_allows_cancel(self):
        self.prepare_preview()
        error = RuntimeError("rejected")
        error.code = "P0001"
        self.client.rpc.return_value.execute.side_effect = error
        self.render("optimizer_save")
        self.assertFalse(self.st.session_state["optimizer_preview"]["save_pending"])
        self.assertNotIn("optimizer_saved_message", self.st.session_state)
        self.render("optimizer_cancel")
        self.assertNotIn("optimizer_choice", self.st.session_state)

    def test_read_only_test_environment_never_saves(self):
        self.prepare_preview()
        self.render("optimizer_save", read_only=True)
        self.client.rpc.assert_not_called()

    def test_switching_season_discards_unsaved_preview(self):
        self.prepare_preview()
        self.render(season=2027)
        self.assertNotIn("optimizer_choice", self.st.session_state)

    def test_invalid_response_keeps_save_unconfirmed(self):
        self.prepare_preview()
        self.client.rpc.return_value.execute.return_value.data = None
        self.render("optimizer_save")
        self.assertTrue(self.st.session_state["optimizer_preview"]["save_pending"])
        self.assertNotIn("optimizer_saved_message", self.st.session_state)


if __name__ == "__main__":
    unittest.main()
