from unittest.mock import Mock

import pytest

from modules.timeline_edit import validate_timeline_edit


def payload(**changes):
    return dict(room_number=2, checkin_date="2026-12-30",
                checkout_date="2027-01-03", booking_number=10, web="web", **changes)


def booking(id=2, **changes):
    row = dict(id=id, booking_number=20, room_number=2,
               checkin_date="2027-01-01", checkout_date="2027-01-04", web="bc")
    row.update(changes)
    return row


def client_for(rows):
    client = Mock()
    client.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value.data = rows
    return client


def test_move_blocks_overlap_across_year_boundary():
    with pytest.raises(ValueError, match="booking 20"):
        validate_timeline_edit(client_for([booking()]), 1, payload())


@pytest.mark.parametrize("changes", [
    {"checkin_date": "2027-01-03"},
    {"checkout_date": "2026-12-30"},
    {"room_number": 3},
    {"web": " CAN-SL "},
    {"id": 1},
])
def test_boundaries_other_rooms_cancelled_and_self_are_allowed(changes):
    validate_timeline_edit(client_for([booking(**changes)]), 1, payload())


def test_cancellation_of_another_room_releases_whole_booking():
    validate_timeline_edit(client_for([
        booking(), booking(id=3, room_number=7, web="cansl"),
    ]), 1, payload())


def test_reactivation_checks_occupancy():
    with pytest.raises(ValueError, match="allerede booket"):
        validate_timeline_edit(client_for([
            booking(id=1, booking_number=10, web="cansl"), booking(),
        ]), 1, payload())


@pytest.mark.parametrize("end", ["2026-12-30", "2026-12-29"])
def test_invalid_dates_are_rejected(end):
    proposed = payload()
    proposed["checkout_date"] = end
    with pytest.raises(ValueError, match="Afrejse"):
        validate_timeline_edit(client_for([]), 1, proposed)


def test_database_failure_prevents_validation():
    client = client_for([])
    client.table.return_value.select.return_value.order.return_value.range.return_value.execute.side_effect = RuntimeError("offline")
    with pytest.raises(RuntimeError):
        validate_timeline_edit(client, 1, payload())


def test_checks_rows_after_first_database_page():
    client = client_for([])
    execute = client.table.return_value.select.return_value.order.return_value.range.return_value.execute
    execute.side_effect = [Mock(data=[booking(id=i + 10, room_number=3) for i in range(1000)]),
                           Mock(data=[booking()])]
    with pytest.raises(ValueError, match="allerede booket"):
        validate_timeline_edit(client, 1, payload())
