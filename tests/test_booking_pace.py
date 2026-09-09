from datetime import date
import unittest

from modules.booking_pace import build_booking_pace


def live(year, number=1, status='web', booked='2026-12-10T12:00:00Z'):
    return dict(season=year, booking_number=number, web=status,
                booking_date=booked, checkin_date=f'{year}-06-01',
                checkout_date=f'{year}-06-04')


class BookingPaceTests(unittest.TestCase):
    def build(self, history=None, current=None, archived=False, today=date(2027, 2, 1)):
        return build_booking_pace([], history or [], current or [],
                                  [dict(season=2027, pace_archived=archived)], today)

    def test_missing_season_does_not_break_valid_live_curve(self):
        for bad_year in (None, "", "unknown", float("nan"), 2027.5):
            with self.subTest(year=bad_year):
                invalid = {**live(2027), "season": bad_year}
                result, messages = self.build(current=[live(2027), invalid])
                self.assertEqual(result.iloc[-1].sold_nights, 3)
                self.assertTrue(any("sæsonår" in m for m in messages))

    def test_missing_season_in_history_and_settings(self):
        history = [dict(season=2027, booking_nr=1, web="web",
                        booking_date="2026-12-10T12:00:00Z", room_nights=8),
                   dict(season=None)]
        result, messages = build_booking_pace([], history, [],
            [dict(season=None, pace_archived=True), dict(season="2027", pace_archived=True)])
        self.assertEqual(result.iloc[-1].sold_nights, 8)
        self.assertEqual(len(messages), 2)

    def test_open_season_without_bookings_shows_zero_curve(self):
        result, messages = self.build()
        self.assertFalse(result.empty)
        self.assertTrue(result.sold_nights.eq(0).all())
        self.assertEqual(messages, [])

    def test_future_empty_season_does_not_break_other_seasons(self):
        result, messages = build_booking_pace([], [], [live(2027)],
            [dict(season=2027, pace_archived=False),
             dict(season=2028, pace_archived=False)], today=date(2027, 2, 1))
        self.assertEqual(result[result.season_year.eq("2027")].iloc[-1].sold_nights, 3)
        self.assertEqual(result[result.season_year.eq("2028")].sold_nights.tolist(), [0])
        self.assertEqual(messages, [])

    def test_future_season_opening_balance_and_rollover(self):
        rows = [live(2027), live(2027, 2, booked='2027-01-15T12:00:00Z')]
        before, _ = self.build(current=rows, today=date(2026, 12, 31))
        self.assertEqual(before.sold_nights.tolist(), [3])
        after, _ = self.build(current=rows)
        self.assertEqual(after.iloc[0].sold_nights, 3)
        self.assertEqual(after.iloc[-1].sold_nights, 6)

    def test_cancellation_removes_entire_booking_but_only_its_season(self):
        rows = [live(2027), live(2027, status=' CAN-SL '), live(2028)]
        result, _ = self.build(current=rows)
        self.assertEqual(result[result.season_year.eq('2027')].sold_nights.sum(), 0)
        self.assertEqual(result[result.season_year.eq('2028')].iloc[0].sold_nights, 3)

    def test_archive_is_exclusive_and_static(self):
        history = [dict(season=2027, booking_nr=1, web='web',
                        booking_date='2026-12-10T12:00:00Z', room_nights=8)]
        result, _ = self.build(history=history, current=[live(2027)], archived=True)
        self.assertEqual(result.iloc[-1].sold_nights, 8)
        self.assertGreaterEqual(result.iloc[-1].week_number, 52)
        dynamic, _ = self.build(history=history, current=[live(2027)])
        self.assertEqual(dynamic.iloc[-1].sold_nights, 3)

    def test_missing_room_booking_date_inherits_master(self):
        result, messages = self.build(current=[live(2027), live(2027, booked=None)])
        self.assertEqual(result.iloc[-1].sold_nights, 6)
        self.assertEqual(messages, [])

    def test_missing_data_is_reported_without_inventing_nights(self):
        history = [dict(season=2027, booking_nr=1, web='web',
                        booking_date=None, room_nights=None)]
        result, messages = self.build(history=history, archived=True)
        self.assertEqual(result.iloc[-1].sold_nights, 0)
        self.assertEqual(len(messages), 1)

    def test_legacy_only_through_2025_latest_id_wins(self):
        legacy = [dict(id=2, season_year=2025, week_number=10, sold_nights=20),
                  dict(id=1, season_year=2025, week_number=10, sold_nights=10),
                  dict(id=3, season_year=2026, week_number=10, sold_nights=99)]
        result, _ = build_booking_pace(legacy, [], [], [])
        self.assertEqual(result.sold_nights.tolist(), [20])

    def test_missing_archive_does_not_fall_back_to_live(self):
        result, messages = self.build(current=[live(2027)], archived=True)
        self.assertTrue(result.empty)
        self.assertEqual(len(messages), 1)

    def test_new_year_does_not_wrap_december_to_week_one(self):
        result, _ = self.build(current=[live(2027)], today=date(2028, 1, 1))
        self.assertEqual(result.iloc[-1].sold_nights, 3)
        self.assertGreaterEqual(result.iloc[-1].week_number, 52)


if __name__ == '__main__':
    unittest.main()
