import unittest

import pandas as pd

from modules.booking_comparison import compare_bookings, prepare_booking_com, prepare_database


class BookingComparisonRoomTests(unittest.TestCase):
    def _booking_com(self, rooms):
        return prepare_booking_com(
            pd.DataFrame(
                [
                    {
                        "Bookingnummer": "5490828207",
                        "Gæstens navn": "Anna Jensen",
                        "Indtjekning": "2026-08-01",
                        "Udtjekning": "2026-08-04",
                        "Booket den": "2026-07-01",
                        "Status": "ok",
                        "Værelser": rooms,
                        "Personer": 4,
                    }
                ]
            )
        )

    def _database(self, row_count):
        rows = []
        for index in range(row_count):
            rows.append(
                {
                    "booking_number": "46",
                    "season": 2026,
                    "navn": "Anna Jensen",
                    "checkin_date": "2026-08-01",
                    "checkout_date": "2026-08-04",
                    "booking_date": "2026-07-01" if index == 0 else None,
                    "numb_rooms": 2 if index == 0 else None,
                    "numb_guests": 4 if index == 0 else None,
                }
            )
        return prepare_database(pd.DataFrame(rows))

    def test_multiple_database_room_rows_are_one_exact_booking(self):
        result = compare_bookings(self._booking_com(2), self._database(2))

        self.assertEqual(len(result["exact"]), 1)
        self.assertTrue(result["changed"].empty)
        self.assertTrue(result["only_db"].empty)

    def test_missing_database_room_is_reported_as_room_difference(self):
        result = compare_bookings(self._booking_com(2), self._database(1))

        self.assertEqual(len(result["changed"]), 1)
        self.assertEqual(
            result["changed"].iloc[0]["Forskel"],
            "værelser (Booking.com: 2, hk_dtb: 1)",
        )
        self.assertEqual(result["changed"].iloc[0]["Værelser"], 2)
        self.assertEqual(result["changed"].iloc[0]["hk_dtb bookingnr."], "46")
        self.assertTrue(result["only_db"].empty)

    def test_internal_room_row_is_attached_by_stay_and_not_listed_separately(self):
        master = self._database(1)
        extra_room = prepare_database(
            pd.DataFrame(
                [
                    {
                        "booking_number": "28",
                        "season": 2026,
                        "navn": "Alex Nielsen",
                        "checkin_date": "2026-08-01",
                        "checkout_date": "2026-08-04",
                        "booking_date": None,
                        "numb_rooms": None,
                        "numb_guests": None,
                    }
                ]
            )
        )
        database = pd.concat([master, extra_room], ignore_index=True)

        result = compare_bookings(self._booking_com(2), database)

        self.assertEqual(len(result["exact"]), 1)
        self.assertTrue(result["only_db"].empty)

    def test_internal_room_row_never_appears_as_only_database(self):
        database = prepare_database(
            pd.DataFrame(
                [
                    {
                        "booking_number": "26",
                        "season": 2026,
                        "navn": "Henrik Tillebeck",
                        "checkin_date": "2026-07-06",
                        "checkout_date": "2026-07-09",
                        "booking_date": None,
                        "numb_rooms": None,
                        "numb_guests": None,
                    }
                ]
            )
        )

        result = compare_bookings(self._booking_com(1), database)

        self.assertTrue(result["only_db"].empty)

    def test_same_internal_number_in_another_season_is_not_grouped_together(self):
        database = prepare_database(
            pd.DataFrame(
                [
                    {
                        "booking_number": "46",
                        "season": 2026,
                        "navn": "Anna Jensen",
                        "checkin_date": "2026-08-01",
                        "checkout_date": "2026-08-04",
                        "booking_date": "2026-07-01",
                        "numb_rooms": 1,
                        "numb_guests": 4,
                    },
                    {
                        "booking_number": "46",
                        "season": 2025,
                        "navn": "En anden gæst",
                        "checkin_date": "2025-08-01",
                        "checkout_date": "2025-08-04",
                        "booking_date": "2025-07-01",
                        "numb_rooms": 1,
                        "numb_guests": 2,
                    },
                ]
            )
        )

        self.assertEqual(len(database), 2)


if __name__ == "__main__":
    unittest.main()
