import unittest
from unittest.mock import MagicMock

import pandas as pd

from modules.calendar_save import build_move_request, save_move_request


class CalendarSaveTests(unittest.TestCase):
    def setUp(self):
        self.rows = pd.DataFrame([
            dict(id=1, booking_number=100, season=2027, room_number=1, movable=True,
                 web="web", checkin_date="2027-06-01", checkout_date="2027-06-05"),
            dict(id=2, booking_number=100, season=2027, room_number=2, movable=True,
                 web="web", checkin_date="2027-06-01", checkout_date="2027-06-05"),
        ])
        self.sources = {str(r["id"]): r for r in self.rows.to_dict("records")}

    def build(self, rows=None, moves=None, season=2027):
        return build_move_request(self.rows if rows is None else rows, self.sources,
                                  moves or {"1": 3}, season, today="2026-10-07")

    def test_fixed_dates_and_one_part_of_booking(self):
        self.rows.loc[1, "movable"] = False
        request = self.build()
        self.assertEqual(request["p_season"], 2027)
        self.assertEqual(request["p_moves"], [dict(id=1, from_room=1, to_room=3,
                         checkin_date="2027-06-01", checkout_date="2027-06-05")])

    def test_overlap_across_seasons_and_atomic_swap(self):
        with self.assertRaises(ValueError):
            self.build(moves={"1": 2})
        self.assertEqual(len(self.build(moves={"1": 2, "2": 1})["p_moves"]), 2)
        neighbour = self.rows.iloc[[1]].copy()
        neighbour["id"] = 3
        neighbour["season"] = 2026
        neighbour["room_number"] = 3
        with self.assertRaises(ValueError):
            self.build(rows=pd.concat([self.rows, neighbour]))

    def test_checkout_day_is_available_and_cancellation_is_scoped(self):
        neighbour = self.rows.iloc[[1]].copy()
        neighbour["room_number"] = 3
        neighbour["checkin_date"] = "2027-06-05"
        neighbour["checkout_date"] = "2027-06-07"
        self.build(rows=pd.concat([self.rows.iloc[[0]], neighbour]))
        neighbour = self.rows.iloc[[1]].copy()
        neighbour["season"] = 2026
        neighbour["web"] = "cansl"
        self.build(rows=pd.concat([self.rows.iloc[[0]], neighbour]))
        self.rows.loc[1, "web"] = "cansl"
        with self.assertRaises(ValueError):
            self.build()

    def test_stale_locked_missing_and_other_seasons_rejected(self):
        for field, value in [("room_number", 4), ("checkin_date", "2027-06-02"),
                             ("checkout_date", "2027-06-06"), ("booking_number", 999),
                             ("season", 2028), ("movable", False), ("movable", None)]:
            changed = self.rows.copy()
            if value is None:
                changed[field] = changed[field].astype(object)
            changed.loc[0, field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build(rows=changed)
        with self.assertRaises(ValueError):
            self.build(rows=self.rows.iloc[[1]])
        with self.assertRaises(ValueError):
            self.build(season=2026)
        with self.assertRaises(ValueError):
            build_move_request(self.rows, self.sources, {"1": 3}, 2027, today="2027-06-01")

    def client(self, request):
        client = MagicMock()
        client.rpc.return_value.execute.return_value.data = dict(
            status="saved", request_id=request["p_request_id"], moved_count=1)
        saved = self.rows.copy()
        saved.loc[0, "room_number"] = 3
        client.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value.data = saved.to_dict("records")
        return client

    def test_save_is_one_rpc_and_readback_and_retry_keeps_identity(self):
        request = self.build()
        client = self.client(request)
        save_move_request(client, request, authenticated=True)
        save_move_request(client, request, authenticated=True)
        self.assertEqual(client.rpc.call_count, 2)
        client.rpc.assert_called_with("apply_calendar_moves_authenticated", request)
        client.table.return_value.update.assert_not_called()

    def test_unconfirmed_receipt_and_bad_readback_rejected(self):
        request = self.build()
        client = self.client(request)
        client.rpc.return_value.execute.return_value.data = {}
        with self.assertRaises(RuntimeError):
            save_move_request(client, request)
        client = self.client(request)
        client.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value.data = self.rows.to_dict("records")
        with self.assertRaises(RuntimeError):
            save_move_request(client, request)


if __name__ == "__main__":
    unittest.main()
