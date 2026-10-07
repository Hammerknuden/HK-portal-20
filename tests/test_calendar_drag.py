import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from modules.calendar_drag import accept_move, drag_data, preview_moves, render_drag_calendar
from modules.calendar_view import build_calendar, prepare_bookings


class CalendarDragTests(unittest.TestCase):
    def setUp(self):
        self.rows = prepare_bookings(pd.DataFrame([
            dict(id=1, booking_number=145, room_number=1, movable=True,
                 checkin_date="2026-06-01", checkout_date="2026-06-05"),
            dict(id=2, booking_number=145, room_number=2, movable=False,
                 checkin_date="2026-06-01", checkout_date="2026-06-05"),
        ]), 2026)

    def test_move_changes_only_one_room_and_ignores_supplied_dates(self):
        original = self.rows.copy(deep=True)
        moves = accept_move(self.rows, {}, dict(id="1", room=7, checkin_date="2027-01-01"))
        preview = preview_moves(self.rows, moves)
        self.assertEqual(preview.room_number.tolist(), [7, 2])
        pd.testing.assert_frame_equal(preview.drop(columns="room_number"),
                                      original.drop(columns="room_number"))
        pd.testing.assert_frame_equal(self.rows, original)
        self.assertEqual(accept_move(self.rows, moves, dict(id="1", room=1)), {})

    def test_invalid_locked_and_ambiguous_moves_rejected(self):
        for request in [dict(id="2", room=3), dict(id="1", room=8),
                        dict(id="1", room=True), dict(id="missing", room=3), None]:
            with self.assertRaises(ValueError):
                accept_move(self.rows, {}, request)
        with self.assertRaises(ValueError):
            accept_move(pd.concat([self.rows, self.rows]), {}, dict(id="1", room=3))
        self.assertEqual(preview_moves(self.rows, {"2": 3}).room_number.tolist(), [1, 2])

    def test_payload_locks_and_row_identity(self):
        payload = drag_data(self.rows, "2026-01-01", "2027-01-01")
        self.assertEqual([b["locked"] for b in payload["items"]], [False, True])
        self.assertEqual([b["id"] for b in payload["items"]], ["1", "2"])
        payload = drag_data(self.rows.drop(columns="id"), "2026-01-01", "2027-01-01")
        self.assertTrue(all(b["locked"] for b in payload["items"]))

    def test_overlap_rejected_and_previous_draft_unchanged(self):
        moves = {"1": 3}
        with self.assertRaises(ValueError):
            accept_move(self.rows, moves, dict(id="1", room=2))
        self.assertEqual(moves, {"1": 3})
        self.assertEqual(preview_moves(self.rows, moves).room_number.tolist(), [3, 2])

    def test_adjacent_stays_and_room_freed_by_draft(self):
        rows = self.rows.copy()
        rows.loc[1, "movable"] = True
        moves = accept_move(rows, {}, dict(id="2", room=3))
        self.assertEqual(accept_move(rows, moves, dict(id="1", room=2)), {"2": 3, "1": 2})
        rows.loc[1, "checkin_date"] = pd.Timestamp("2026-06-05")
        rows.loc[1, "checkout_date"] = pd.Timestamp("2026-06-07")
        self.assertEqual(accept_move(rows, {}, dict(id="1", room=2)), {"1": 2})

    def test_other_season_overlap_and_fresh_lock_rejected(self):
        neighbour = self.rows.iloc[[1]].copy()
        neighbour["id"] = 3
        neighbour["room_number"] = 3
        occupancy = pd.concat([self.rows, neighbour])
        with self.assertRaises(ValueError):
            accept_move(self.rows, {}, dict(id="1", room=3), occupancy=occupancy)
        occupancy.loc[occupancy.id == 1, "movable"] = False
        with self.assertRaises(ValueError):
            accept_move(self.rows, {}, dict(id="1", room=7), occupancy=occupancy)

    def test_plotly_payload_keeps_dates_events_and_row_identity(self):
        events = pd.DataFrame([dict(start_date="2026-06-02", end_date="2026-06-03",
                                    event="Festival", color="orange")])
        figure = build_calendar(self.rows, events, 2026)
        original_range = list(figure.layout.xaxis.range)
        state = {"chart": SimpleNamespace(viewport=dict(
            view_key="2026:False", range=["2026-06-02", "2026-06-04"]))}
        with patch("modules.calendar_drag.st.session_state", state), \
                patch("modules.calendar_drag._drag_component") as renderer:
            render_drag_calendar(self.rows, *original_range, key="chart", figure=figure,
                                 view_key="2026:False")
            data = renderer.call_args.kwargs["data"]
        self.assertEqual(data["figure"]["layout"]["xaxis"]["range"],
                         ["2026-06-02", "2026-06-04"])
        self.assertEqual([pd.Timestamp(value) for value in data["default_range"]], original_range)
        self.assertTrue(data["figure"]["layout"]["xaxis"]["rangeslider"]["visible"])
        self.assertTrue(data["figure"]["layout"]["yaxis"]["fixedrange"])
        self.assertTrue(any(a["text"] == "Festival" for a in data["figure"]["layout"]["annotations"]))
        self.assertEqual({str(custom[0]) for trace in data["figure"]["data"]
                          for custom in trace["customdata"]}, {"1", "2"})
        for trace in data["figure"]["data"]:
            self.assertEqual(trace["x"], [4 * 86400000])
            self.assertEqual(trace["base"], ["2026-06-01T00:00:00"])
        self.assertEqual(list(figure.layout.xaxis.range), original_range)

    def test_changed_zoom_resets_view_and_pending_disables_drag(self):
        figure = build_calendar(self.rows, pd.DataFrame(), 2026)
        state = {"chart": SimpleNamespace(viewport=dict(
            view_key="2026:False", range=["2026-06-02", "2026-06-04"]))}
        with patch("modules.calendar_drag.st.session_state", state), \
                patch("modules.calendar_drag._drag_component") as renderer:
            render_drag_calendar(self.rows, *figure.layout.xaxis.range, key="chart", figure=figure,
                                 view_key="2026:True", disabled=True)
            data = renderer.call_args.kwargs["data"]
        self.assertNotEqual(data["figure"]["layout"]["xaxis"]["range"],
                            ["2026-06-02", "2026-06-04"])
        self.assertTrue(all(item["locked"] for item in data["items"]))


if __name__ == "__main__":
    unittest.main()
