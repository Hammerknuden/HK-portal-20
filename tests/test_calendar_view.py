import unittest

import pandas as pd

from modules.calendar_view import ROOMS, build_calendar, prepare_bookings
from modules.timeline_colors import booking_color


class CalendarViewTests(unittest.TestCase):
    def bookings(self):
        return pd.DataFrame([
            dict(booking_number=145, room_number=1, web="web", movable=True,
                 checkin_date="2026-06-01", checkout_date="2026-06-05"),
            dict(booking_number=145, room_number=2, web="web", movable=False,
                 checkin_date="2026-06-01", checkout_date="2026-06-05"),
        ])

    def test_colours_rooms_events_and_zoom(self):
        bookings = prepare_bookings(self.bookings(), 2026)
        original = bookings.copy(deep=True)
        events = pd.DataFrame([dict(start_date="2026-06-02", end_date="2026-06-03",
                                    event="Festival", color="orange", opacity=0.1)])
        fig = build_calendar(bookings, events, 2026, True, today="2026-06-02")
        self.assertEqual({trace.marker.color for trace in fig.data},
                         {booking_color(145, "web", True), booking_color(145, "web", False)})
        self.assertEqual(list(fig.layout.yaxis.categoryarray), list(ROOMS.values()))
        self.assertEqual(pd.Timestamp(fig.layout.xaxis.range[0]), pd.Timestamp("2026-05-26"))
        self.assertTrue(any(a.text == "Festival" for a in fig.layout.annotations))
        self.assertTrue(any(a.text == "23" for a in fig.layout.annotations))
        self.assertTrue(fig.layout.xaxis.rangeslider.visible)
        pd.testing.assert_frame_equal(bookings, original)

    def test_cancelled_booking_excluded_as_a_group(self):
        rows = self.bookings()
        rows.loc[1, "web"] = "cansl"
        self.assertTrue(prepare_bookings(rows, 2026).empty)

    def test_zoom_before_and_after_booking_period(self):
        rows = self.bookings()
        rows.loc[1, "checkout_date"] = "2026-09-01"
        bookings = prepare_bookings(rows, 2026)
        for today, expected_start, expected_end in (
            ("2026-01-01", "2026-06-01", "2026-06-29"),
            ("2026-12-01", "2026-08-04", "2026-09-01"),
            ("2026-06-01", "2026-05-25", "2026-06-22"),
            ("2026-09-01", "2026-08-25", "2026-09-22"),
        ):
            with self.subTest(today=today):
                fig = build_calendar(bookings, pd.DataFrame(), 2026, True, today=today)
                self.assertEqual(tuple(pd.Timestamp(value) for value in fig.layout.xaxis.range),
                                 (pd.Timestamp(expected_start), pd.Timestamp(expected_end)))

    def test_zoom_off_shows_entire_booking_period(self):
        bookings = prepare_bookings(self.bookings(), 2026)
        fig = build_calendar(bookings, pd.DataFrame(), 2026, False, today="2026-12-01")
        self.assertEqual(tuple(pd.Timestamp(value) for value in fig.layout.xaxis.range),
                         (pd.Timestamp("2026-06-01"), pd.Timestamp("2026-06-05")))

    def test_empty_or_unassigned_bookings_still_show_calendar(self):
        for rows in (pd.DataFrame(), self.bookings().assign(room_number=None)):
            fig = build_calendar(prepare_bookings(rows, 2026), pd.DataFrame(), 2026,
                                 today="2026-06-02")
            self.assertEqual(len(fig.data), 0)
            self.assertEqual(len(fig.layout.yaxis.tickvals), 7)
            self.assertEqual(pd.Timestamp(fig.layout.xaxis.range[0]), pd.Timestamp("2026-01-01"))


if __name__ == "__main__":
    unittest.main()
