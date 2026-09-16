import itertools
import random
import unittest
from datetime import date

import pandas as pd

from test_level2_optimizer import booking, search

search_improvements = search.search_improvements
validate_plan = search.validate_plan


TODAY = date(2026, 9, 16)


class OptimizerSearchTests(unittest.TestCase):
    def search(self, rows, **limits):
        self.rows = pd.DataFrame(rows)
        result = search_improvements(self.rows, 2026, TODAY, **limits)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["recommendations"]), 1)
        rec = result["recommendations"][0]
        for plan in rec["options"]:
            self.assertTrue(validate_plan(self.rows, plan, TODAY))
            # Independent pairwise overlap check, without production validator.
            moved = {m["id"]: m["to_room"] for m in plan["moves"]}
            for a, b in itertools.combinations(rows, 2):
                room = moved.get(a["id"], a["room_number"])
                if room not in range(1, 6) or room != moved.get(b["id"], b["room_number"]):
                    continue
                self.assertFalse(a["checkin_date"] < b["checkout_date"] and b["checkin_date"] < a["checkout_date"])
        return rec

    def test_all_five_direct_targets(self):
        rec = self.search([booking(1, 7)])
        self.assertEqual({p["target_room"] for p in rec["options"]}, {1, 2, 3, 4, 5})
        self.assertTrue(all(p["moved_existing"] == 0 for p in rec["options"]))

    def test_target_can_be_occupied_on_first_night(self):
        rec = self.search([booking(1, 7, start=19, end=22), booking(2, 1, start=19, end=20)])
        self.assertNotIn(1, rec["daily_free_rooms"]["2026-09-19"])
        self.assertTrue(any(p["target_room"] == 1 for p in rec["options"]))

    def test_middle_booking_moves_without_locked_neighbours(self):
        rec = self.search([
            booking(1, 7, start=19, end=22),
            booking(2, 1, start=18, end=19, movable=False),
            booking(3, 1, start=19, end=22),
            booking(4, 1, start=22, end=24, movable=False),
        ])
        self.assertTrue(any(p["target_room"] == 1 and {m["id"] for m in p["moves"]} == {1, 3}
                            for p in rec["options"]))

    def test_separated_blockers_can_move_to_different_rooms(self):
        rec = self.search([
            booking(1, 7, start=19, end=22),
            booking(2, 1, start=19, end=20), booking(3, 1, start=21, end=22),
            booking(4, 2, start=20, end=23, movable=False),
            booking(5, 3, start=18, end=21, movable=False),
            booking(6, 4, start=18, end=24, movable=False),
            booking(7, 5, start=18, end=24, movable=False),
        ])
        self.assertTrue(any({m["id"]: m["to_room"] for m in p["moves"]} == {1: 1, 2: 2, 3: 3}
                            for p in rec["options"]))

    def test_short_chain_through_third_room(self):
        rec = self.search([
            booking(1, 7, start=19, end=22), booking(2, 1, start=20, end=24),
            booking(3, 2, start=22, end=26), booking(4, 1, start=25, end=28, movable=False),
            booking(5, 3, start=19, end=22, movable=False),
            booking(6, 4, start=19, end=29, movable=False),
            booking(7, 5, start=19, end=29, movable=False),
        ])
        self.assertTrue(any({m["id"]: m["to_room"] for m in p["moves"]} == {1: 1, 2: 2, 3: 3}
                            for p in rec["options"]))

    def test_long_tail_exchange_is_not_limited_by_short_chain_depth(self):
        rows = [booking(1, 7, start=19, end=21)]
        rows += [booking(10 + i, 1, start=20 + 2*i, end=22 + 2*i) for i in range(4)]
        rows += [booking(20 + i, 2, start=21 + 2*i, end=23 + 2*i) for i in range(4)]
        rows += [booking(30+r, r, start=19, end=30, movable=False) for r in (3, 4, 5)]
        rec = self.search(rows, max_moves=1)
        self.assertTrue(any(p["target_room"] == 1 and p["moved_existing"] == 8
                            and p["window"] == ["2026-09-20", "2026-09-29"] for p in rec["options"]))

    def test_missing_night_capacity_stops_search(self):
        rec = self.search([booking(1, 7)] + [booking(10+r, r) for r in range(1, 6)])
        self.assertEqual(rec["status"], "no_capacity")
        self.assertEqual(rec["options"], [])
        self.assertEqual(len(rec["no_capacity_dates"]), 4)

    def test_locked_stays_never_move_even_with_daily_capacity(self):
        rec = self.search([
            booking(1, 7, start=19, end=22),
            booking(2, 1, start=20, end=22, movable=False),
            booking(3, 2, start=19, end=20, movable=False),
        ] + [booking(10+r, r, start=19, end=22, movable=False) for r in (3, 4, 5)])
        self.assertTrue(rec["period_possible"])
        self.assertEqual(rec["options"], [])

    def test_budget_does_not_hide_other_direct_targets(self):
        rec = self.search([booking(1, 7), booking(2, 1)], max_states=1)
        self.assertTrue({2, 3, 4, 5}.issubset({p["target_room"] for p in rec["options"]}))
        self.assertTrue(rec["target_results"][0]["limited"])

    def test_duplicate_booking_numbers_still_use_ids(self):
        rec = self.search([booking(1, 7), booking(2, 1), {**booking(3, 2), "booking_number": 1002}])
        self.assertTrue(rec["options"])
        for p in rec["options"]:
            self.assertEqual(len(p["moves"]), len({m["id"] for m in p["moves"]}))

    def test_other_season_rows_are_conflict_constraints(self):
        rec = self.search([booking(1, 7), {**booking(2, 1, movable=False), "season": 2027}])
        self.assertNotIn(1, {p["target_room"] for p in rec["options"]})

    def test_other_season_is_fixed_even_when_marked_movable(self):
        rec = self.search([booking(1, 7), {**booking(2, 1), "season": 2027}])
        self.assertNotIn(1, {p["target_room"] for p in rec["options"]})

    def test_booking300_does_not_extend_exchange_to_booking502_in_2027(self):
        rows = [
            {**booking(300, 7, start=19, end=22), "booking_number": 300},
            {**booking(146, 3, start=20, end=23), "booking_number": 146},
            {**booking(502, 3), "booking_number": 502, "season": 2027,
             "checkin_date": pd.Timestamp("2027-05-01"), "checkout_date": pd.Timestamp("2027-05-02")},
        ]
        rec = self.search(rows)
        plans = [p for p in rec["options"] if p["target_room"] == 3]
        self.assertTrue(plans)
        for plan in rec["options"]:
            self.assertNotIn(502, {m["id"] for m in plan["moves"]})
            if plan["window"]:
                self.assertLess(plan["window"][1], "2027-01-01")

    def test_validator_rejects_plan_after_booking_season_changes(self):
        rec = self.search([booking(1, 7), booking(2, 1)])
        plan = next(p for p in rec["options"] if p["target_room"] == 1)
        changed = self.rows.copy()
        changed.loc[changed["id"] == 2, "season"] = 2027
        self.assertFalse(validate_plan(changed, plan, TODAY))

    def test_cancellation_does_not_leak_between_seasons(self):
        rows = [booking(1, 7), {**booking(2, 1, movable=False), "booking_number": 22},
                {**booking(3, 2), "booking_number": 22, "season": 2027, "web": "cansl"}]
        result = search_improvements(pd.DataFrame(rows), 2026, TODAY)
        self.assertEqual(result["errors"], [])
        self.assertNotIn(1, {p["target_room"] for p in result["recommendations"][0]["options"]})
        self.assertIn(2, {p["target_room"] for p in result["recommendations"][0]["options"]})

    def test_invalid_or_duplicate_data_produces_explanation(self):
        for rows in ([booking(1, 7), booking(1, 1)],
                     [booking(1, 7, start=24, end=20)],
                     [booking(1, 7), booking(2, 1), booking(3, 1)]):
            with self.subTest(rows=rows):
                result = search_improvements(pd.DataFrame(rows), 2026, TODAY)
                self.assertTrue(result["errors"])
                self.assertEqual(result["recommendations"], [])

    def test_empty_input(self):
        result = search_improvements(pd.DataFrame(), 2026, TODAY)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["recommendations"], [])

    def test_finished_historical_overlaps_do_not_block_future_analysis(self):
        rows = [booking(1, 7), booking(2, 1, start=10, end=12), booking(3, 1, start=10, end=12)]
        result = search_improvements(pd.DataFrame(rows), 2026, TODAY)
        self.assertEqual(result["errors"], [])
        plans = result["recommendations"][0]["options"]
        self.assertEqual({p["target_room"] for p in plans}, {1, 2, 3, 4, 5})
        self.assertTrue(all(validate_plan(pd.DataFrame(rows), p, TODAY) for p in plans))

    def test_fresh_validation_rejects_changed_room_dates_and_lock(self):
        rec = self.search([booking(1, 7), booking(2, 1)])
        plan = next(p for p in rec["options"] if p["target_room"] == 1)
        for column, value in (("room_number", 5), ("movable", False),
                              ("checkout_date", pd.Timestamp("2026-09-25"))):
            with self.subTest(column=column):
                changed = self.rows.copy()
                changed.loc[changed["id"] == 2, column] = value
                self.assertFalse(validate_plan(changed, plan, TODAY))
        self.assertFalse(validate_plan(self.rows, plan, date(2026, 9, 20)))

    def test_multiple_candidates_are_independent_alternatives(self):
        rows = pd.DataFrame([booking(1, 7), booking(2, 7)])
        result = search_improvements(rows, 2026, TODAY)
        self.assertEqual(len(result["recommendations"]), 2)
        for rec in result["recommendations"]:
            for p in rec["options"]:
                self.assertEqual({m["id"] for m in p["moves"]}, {rec["candidate_id"]})

    def test_small_scenarios_match_exhaustive_minimum_move_oracle(self):
        rng = random.Random(156300)
        for case in range(12):
            rows = [booking(1, 7, start=19, end=23)]
            for room in (1, 2, 3):
                start = rng.randint(18, 23)
                rows.append(booking(10 + room, room, start=start,
                                    end=start + rng.randint(1, 4), movable=rng.choice([True, True, False])))
            expected = {}
            # Independently enumerate every final room assignment for all stays.
            for destinations in itertools.product(range(1, 6), repeat=4):
                if any(not row["movable"] and dest != row["room_number"]
                       for row, dest in zip(rows, destinations)):
                    continue
                conflict = any(
                    destinations[a] == destinations[b]
                    and rows[a]["checkin_date"] < rows[b]["checkout_date"]
                    and rows[b]["checkin_date"] < rows[a]["checkout_date"]
                    for a, b in itertools.combinations(range(4), 2)
                )
                if conflict:
                    continue
                cost = sum(dest != row["room_number"] for row, dest in zip(rows[1:], destinations[1:]))
                expected[destinations[0]] = min(expected.get(destinations[0], 99), cost)
            with self.subTest(case=case):
                rec = self.search(rows)
                actual = {}
                for plan in rec["options"]:
                    target = plan["target_room"]
                    actual[target] = min(actual.get(target, 99), plan["moved_existing"])
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
