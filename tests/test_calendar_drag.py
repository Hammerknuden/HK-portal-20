import unittest

import pandas as pd

from modules.calendar_drag import accept_move, drag_data, preview_moves
from modules.calendar_view import prepare_bookings


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


if __name__ == "__main__":
    unittest.main()
