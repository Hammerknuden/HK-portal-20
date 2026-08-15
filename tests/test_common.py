import pandas as pd

from common import exclude_cancelled_bookings


def test_excludes_all_rooms_when_booking_master_row_is_cancelled():
    bookings = pd.DataFrame([
        {"booking_number": 54, "room_number": 7, "web": "cansl"},
        {"booking_number": 54, "room_number": 6, "web": "web"},
        {"booking_number": 55, "room_number": 5, "web": "bc"},
    ])

    result = exclude_cancelled_bookings(bookings)

    assert result["booking_number"].tolist() == [55]


def test_normalizes_cancelled_status_and_booking_number():
    bookings = pd.DataFrame([
        {"booking_number": "54", "room_number": 7, "web": " CAN-SL "},
        {"booking_number": 54.0, "room_number": 6, "web": "web"},
    ])

    assert exclude_cancelled_bookings(bookings).empty


def test_excludes_only_cancelled_row_without_booking_number_column():
    rows = pd.DataFrame([
        {"room_number": 6, "web": "cansl"},
        {"room_number": 5, "web": "web"},
    ])

    result = exclude_cancelled_bookings(rows)

    assert result["room_number"].tolist() == [5]
