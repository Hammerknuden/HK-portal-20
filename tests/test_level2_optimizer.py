"""Contract tests using synthetic bookings only; no database access.

These assertions describe the agreed rules for every booking in a move.
"""

import sys
import unittest
from datetime import date
from unittest.mock import patch
from types import ModuleType

import pandas as pd

try:
    import streamlit  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "streamlit":
        raise
    # The optimizer imports Streamlit but does not use it in these functions.
    with patch.dict(sys.modules, {"streamlit": ModuleType("streamlit")}):
        from modules import level2_optimizer as optimizer
        from modules import optimizer_search as search
else:
    from modules import level2_optimizer as optimizer
    from modules import optimizer_search as search


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 15)


def booking(identifier, room, start=20, end=24, movable=True):
    return {
        "id": identifier,
        "booking_number": 1000 + identifier,
        "room_number": room,
        "season": 2026,
        "checkin_date": pd.Timestamp(2026, 9, start),
        "checkout_date": pd.Timestamp(2026, 9, end),
        "movable": movable,
    }


class Level2ContractTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(optimizer, "date", FixedDate)
        clock.start()
        self.addCleanup(clock.stop)

    def analyze(self, rows):
        return optimizer.analyze_improvements(pd.DataFrame(rows), 2026)["recommendations"]

    def test_future_movable_candidate_is_ready(self):
        self.assertEqual(self.analyze([booking(1, 7)])[0]["status"], "ready")

    def test_locked_candidate_has_no_suggestions(self):
        self.assertEqual(self.analyze([booking(1, 7, movable=False)]), [])

    def test_candidate_arriving_today_has_no_suggestions(self):
        self.assertEqual(self.analyze([booking(1, 7, start=15)]), [])

    def test_checked_in_candidate_has_no_suggestions(self):
        self.assertEqual(self.analyze([booking(1, 7, start=14)]), [])

    def test_room6_does_not_count_as_capacity(self):
        rows = [booking(1, 7)] + [booking(10 + r, r) for r in range(1, 6)]
        result = self.analyze(rows)
        self.assertFalse(result[0]["period_possible"])
        self.assertNotIn(result[0]["status"], ("ready", "rearrangement"))

    def test_direct_options_only_include_rooms_1_to_5(self):
        rows = pd.DataFrame([booking(1, 7)])
        result = optimizer.find_room7_move_options(rows, rows)
        self.assertEqual(result[0]["possible_rooms"], [1, 2, 3, 4, 5])

    def test_departure_day_can_be_reused(self):
        rows = pd.DataFrame([booking(1, 7), booking(2, 1, start=16, end=20)])
        result = optimizer.find_room7_move_options(rows, rows)
        self.assertIn(1, result[0]["possible_rooms"])

    def test_analysis_does_not_change_input(self):
        rows = pd.DataFrame([booking(1, 7), booking(2, 1)])
        before = rows.copy(deep=True)
        optimizer.analyze_improvements(rows, 2026)
        pd.testing.assert_frame_equal(rows, before)

    def test_locked_block_cannot_be_relocated(self):
        rows = pd.DataFrame([booking(1, 1, movable=False)])
        block = optimizer.find_connected_blocks(rows, 1)[0]
        self.assertEqual(optimizer.can_block_move(block, rows), [])

    def test_block_arriving_today_cannot_be_relocated(self):
        rows = pd.DataFrame([booking(1, 1, start=15)])
        block = optimizer.find_connected_blocks(rows, 1)[0]
        self.assertEqual(optimizer.can_block_move(block, rows), [])

    def test_checked_in_block_cannot_be_relocated(self):
        rows = pd.DataFrame([booking(1, 1, start=14)])
        block = optimizer.find_connected_blocks(rows, 1)[0]
        self.assertEqual(optimizer.can_block_move(block, rows), [])

    def test_swap_cannot_move_locked_booking(self):
        rows = pd.DataFrame([booking(1, 1), booking(2, 2, movable=False)])
        a = optimizer.find_connected_blocks(rows, 1)[0]
        b = optimizer.find_connected_blocks(rows, 2)[0]
        self.assertFalse(optimizer.can_swap_blocks(a, b, rows)["possible"])

    def test_recommendations_do_not_move_locked_block(self):
        # Room 1 is free Sep 20-22; room 2 is free Sep 22-24.
        # The only blockers are locked, so no rearrangement can be proposed.
        rows = [
            booking(1, 7),
            booking(2, 1, start=22, end=24, movable=False),
            booking(3, 2, start=20, end=22, movable=False),
        ] + [booking(10 + r, r, movable=False) for r in (3, 4, 5)]
        result = self.analyze(rows)
        self.assertTrue(result)
        self.assertNotIn(result[0]["status"], ("ready", "rearrangement"))

    def test_future_movable_block_can_still_move(self):
        rows = pd.DataFrame([booking(1, 1)])
        block = optimizer.find_connected_blocks(rows, 1)[0]
        self.assertEqual(
            [o["move_block_to_room"] for o in optimizer.can_block_move(block, rows)],
            [2, 3, 4, 5],
        )

    def test_future_movable_swap_is_still_possible(self):
        rows = pd.DataFrame([booking(1, 1), booking(2, 2)])
        a = optimizer.find_connected_blocks(rows, 1)[0]
        b = optimizer.find_connected_blocks(rows, 2)[0]
        self.assertTrue(optimizer.can_swap_blocks(a, b, rows)["possible"])

    def test_swap_rejects_today_and_checked_in_bookings_on_either_side(self):
        for start in (14, 15):
            for locked_room in (1, 2):
                with self.subTest(start=start, room=locked_room):
                    rows = pd.DataFrame([
                        booking(r, r, start=start if r == locked_room else 20)
                        for r in (1, 2)
                    ])
                    a = optimizer.find_connected_blocks(rows, 1)[0]
                    b = optimizer.find_connected_blocks(rows, 2)[0]
                    self.assertFalse(optimizer.can_swap_blocks(a, b, rows)["possible"])

    def test_partial_block_and_relocation_respect_lock_and_date(self):
        for start, movable in ((20, False), (15, True), (14, True)):
            with self.subTest(start=start, movable=movable):
                rows = pd.DataFrame([booking(1, 1, start=start, movable=movable)])
                partial = {
                    "booking_ids": [1], "booking_numbers": [1001], "size": 1,
                }
                self.assertEqual(optimizer.analyze_partial_block_move(partial, rows, [2]), [])
                self.assertEqual(optimizer.find_block_relocation_options(
                    {"booking_number": 1002},
                    {"1": [{"id": 1, "movable": True}]}, rows,
                ), [])

    def test_all_rows_must_be_present_and_explicitly_movable(self):
        rows = pd.DataFrame([booking(1, 1)])
        self.assertFalse(optimizer.can_move_booking_ids(rows, []))
        self.assertFalse(optimizer.can_move_booking_ids(rows, [1, 2]))
        self.assertFalse(optimizer.can_move_booking_ids(pd.concat([rows, rows]), [1]))
        for flag in (None, pd.NA, "False", "True"):
            with self.subTest(flag=flag):
                unknown = pd.DataFrame([booking(1, 1, movable=flag)])
                self.assertFalse(optimizer.can_move_booking_ids(unknown, [1]))

    def test_return_block_in_recommendation_must_also_be_movable(self):
        # The target block extends beyond the temp booking; the return block
        # starts after the temp booking ends but still must pass the lock rule.
        for start, movable in ((25, False), (25, True)):
            rows = [
                booking(1, 7), booking(2, 1, start=22, end=28),
                booking(3, 2, start=20, end=22, movable=False),
                booking(4, 2, start=start, end=28, movable=movable),
            ] + [booking(10 + r, r, end=28, movable=False) for r in (3, 4, 5)]
            with self.subTest(movable=movable):
                result = self.analyze(rows)[0]
                self.assertEqual(result["status"], "rearrangement" if movable else "not_found")

    def test_saved_plan_is_rejected_when_date_or_lock_changes(self):
        rows = pd.DataFrame([booking(1, 7), booking(2, 1)])
        self.assertTrue(optimizer.can_move_booking_ids(rows, [1, 2]))
        rows.loc[rows["id"] == 2, "movable"] = False
        self.assertFalse(optimizer.can_move_booking_ids(rows, [1, 2]))
        rows.loc[rows["id"] == 2, "movable"] = True
        with patch.object(FixedDate, "today", return_value=date(2026, 9, 20)):
            self.assertFalse(optimizer.can_move_booking_ids(rows, [1, 2]))

    def test_booking300_return_to_room5_cannot_overlap(self):
        # Synthetic analogue of the report, not a copy of the user's bookings.
        rows = pd.DataFrame([
            {**booking(300, 7, start=19, end=22), "booking_number": 300},
            booking(301, 5, start=20, end=24),
            booking(302, 1, start=22, end=26),
            booking(303, 5, start=25, end=28),
        ])
        self.assertFalse(optimizer.validate_rearrangement(
            rows, 300, 5, [301], 1, [{"booking_ids": [302]}]
        ))
        # Without the later booking on room 5 this full swap is valid.
        self.assertTrue(optimizer.validate_rearrangement(
            rows[rows["id"] != 303], 300, 5, [301], 1,
            [{"booking_ids": [302]}],
        ))

    def test_return_block_cannot_overlap_temp_candidate(self):
        rows = pd.DataFrame([
            booking(1, 7), booking(2, 5, start=22, end=26),
            booking(3, 1, start=23, end=27),
        ])
        self.assertFalse(optimizer.validate_rearrangement(
            rows, 1, 5, [2], 1, [{"booking_ids": [3]}]
        ))

    def test_new_destination_booking_invalidates_previously_valid_plan(self):
        rows = pd.DataFrame([booking(1, 7), booking(2, 5, start=22, end=26)])
        self.assertTrue(optimizer.validate_rearrangement(rows, 1, 5, [2], 1, []))
        rows = pd.concat([rows, pd.DataFrame([booking(3, 1, start=25, end=27)])])
        self.assertFalse(optimizer.validate_rearrangement(rows, 1, 5, [2], 1, []))


if __name__ == "__main__":
    unittest.main()
