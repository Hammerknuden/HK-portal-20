"""Partial video replay. See fixture assumptions; no production connection."""

import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from test_level2_optimizer import optimizer, search


class Booking156VideoTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads(
            (Path(__file__).parent / "fixtures" / "booking_156_video.json").read_text()
        )
        self.rows = pd.DataFrame(fixture["bookings"])
        self.rows["season"] = 2026
        self.rows["movable"] = True
        for column in ("checkin_date", "checkout_date"):
            self.rows[column] = pd.to_datetime(self.rows[column])
        self.candidate = self.rows[self.rows["booking_number"] == 156].iloc[0]
        clock = patch.object(optimizer, "date")
        clock.start().today.return_value = date.fromisoformat(fixture["analysis_date"])
        self.addCleanup(clock.stop)

    def test_156_starts_in_temp_for_august_16_to_18(self):
        self.assertEqual(self.candidate["room_number"], 7)
        self.assertEqual(self.candidate["checkin_date"], pd.Timestamp("2026-08-16"))
        self.assertEqual(self.candidate["checkout_date"], pd.Timestamp("2026-08-18"))

    def test_rooms_1_and_5_both_need_the_second_night_freed(self):
        coverage = optimizer.analyze_period_coverage(self.candidate, self.rows)
        self.assertTrue(coverage["period_possible"])
        for room in (1, 5):
            self.assertIn(room, coverage["daily_free_rooms"]["2026-08-16"])
            self.assertNotIn(room, coverage["daily_free_rooms"]["2026-08-17"])
        blockers = optimizer.find_room7_blockers(self.rows, self.rows)[0]["blockers"]
        self.assertEqual([b["booking_number"] for b in blockers["1"]], [26])
        self.assertEqual([b["booking_number"] for b in blockers["5"]], [21])

    def test_no_direct_placement_for_the_whole_stay(self):
        self.assertEqual(optimizer.find_room7_move_options(self.rows, self.rows), [])

    def test_original_conflicting_option_is_not_offered(self):
        result = optimizer.analyze_improvements(self.rows, 2026)["recommendations"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["booking_number"], 156)
        invalid = {1: 1, 3: 2, 6: 1, 7: 1, 8: 1}
        self.assertTrue(result[0]["options"])
        self.assertNotIn(invalid, [
            {m["id"]: m["to_room"] for m in plan["moves"]}
            for plan in result[0]["options"]
        ])

    def test_expanded_search_finds_both_room1_and_room5_in_partial_fixture(self):
        result = optimizer.analyze_improvements(self.rows, 2026)["recommendations"][0]
        self.assertTrue({1, 5}.issubset({p["target_room"] for p in result["options"]}))
        for plan in result["options"]:
            self.assertTrue(search.validate_plan(self.rows, plan, date(2026, 7, 16)))

    def test_original_return_block_is_rejected(self):
        self.assertFalse(optimizer.validate_rearrangement(
            self.rows, 1, 1, [3], 2, [{"booking_ids": [6, 7, 8]}]
        ))


if __name__ == "__main__":
    unittest.main()
