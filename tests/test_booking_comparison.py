import unittest

import pandas as pd

from modules.booking_comparison import compare_bookings, prepare_booking_com, prepare_database


class BookingComparisonRoomTests(unittest.TestCase):
    def _booking_com(self, rooms):
        return prepare_booking_com(
            pd.DataFrame(
                [
                    {
                        "Bookingnummer": "BC-123",
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
                    "booking_number": "BC-123",
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
        self.assertTrue(result["only_db"].empty)


if __name__ == "__main__":
    unittest.main()
