import pandas as pd
from datetime import date


def analyze_improvements(bookings, season):

    today = date.today()

    season_bookings = bookings[
        bookings["season"] == season
    ].copy()

    season_bookings["checkin_date"] = pd.to_datetime(
        season_bookings["checkin_date"]
    )
    season_bookings["checkout_date"] = pd.to_datetime(
        season_bookings["checkout_date"]
    )
    movable = season_bookings[
        season_bookings["movable"] == True
    ]

    checked_in = season_bookings[
        season_bookings["checkin_date"].dt.date <= today
    ]

    eligible = season_bookings[
        (season_bookings["movable"] == True)
        &
        (season_bookings["checkin_date"].dt.date > today)
    ]

    groupby_result = (
        eligible
        .groupby("room_number")
        .size()
    )

    room_distribution = {
        str(int(room)): int(count)
        for room, count in groupby_result.items()
    }
    room7_suggestions = find_room7_move_options(
        candidates=eligible,
        all_bookings=season_bookings
    )

    room7_blockers = find_room7_blockers(
        candidates=eligible,
        all_bookings=season_bookings
    )
    room_blocks = {
        str(room): find_connected_blocks(
            season_bookings,
            room
        )
        for room in [1, 2, 3, 4, 5]
    }
    room7_blocker_move_options = []

    for item in room7_blockers:
        options = find_block_relocation_options(
            candidate=item,
            blockers=item["blockers"],
            all_bookings=season_bookings
        )
        room_blocks = {
            str(room): find_connected_blocks(
                season_bookings,
                room
            )
            for room in [1, 2, 3, 4, 5]
        }
        room7_blocker_move_options.extend(options)

    coverage = []

    room7_bookings = eligible[
        eligible["room_number"] == 7
        ]

    for _, candidate in room7_bookings.iterrows():
        coverage.append(
            analyze_period_coverage(
                candidate,
                season_bookings
            )
        )

    return {
        "room7_candidates": [
            {
                "id": int(row["id"]),
                "booking_number": int(row["booking_number"]),
                "room_number": int(row["room_number"]),
                "checkin_date": str(row["checkin_date"].date()),
                "checkout_date": str(row["checkout_date"].date()),
                "movable": bool(row["movable"])
                "room_blocks": room_blocks
            }
            for _, row in room7_bookings.iterrows()
        ],
        "room7_blockers": room7_blockers,
        "room7_period_coverage": coverage
    }


def calculate_gaps(bookings):

    gaps = {}

    for room in sorted(bookings["room_number"].dropna().unique()):

        room_bookings = (
            bookings[
                bookings["room_number"] == room
            ]
            .sort_values("checkin_date")
        )

        room_gaps = []
        previous_checkout = None
        previous_booking = None

        for _, booking in room_bookings.iterrows():

            checkin = booking["checkin_date"]
            checkout = booking["checkout_date"]
            booking_number = booking["booking_number"]

            if previous_checkout is not None:
                gap = (checkin - previous_checkout).days

                if gap > 0:
                    room_gaps.append({
                        "gap_days": int(gap),
                        "from_booking": int(previous_booking),
                        "from_checkout": str(previous_checkout.date()),
                        "to_booking": int(booking_number),
                        "to_checkin": str(checkin.date())
                    })

            if previous_checkout is None or checkout > previous_checkout:
                previous_checkout = checkout
                previous_booking = booking_number

        gaps[str(int(room))] = room_gaps

    return gaps
#     return gaps


def find_room7_move_options(candidates, all_bookings):

    source_room = 7
    target_rooms = [1, 2, 3, 4, 5]

    suggestions = []

    room7_bookings = candidates[
        candidates["room_number"] == source_room
    ].sort_values("checkin_date")

    for _, candidate in room7_bookings.iterrows():

        candidate_checkin = candidate["checkin_date"]
        candidate_checkout = candidate["checkout_date"]

        possible_rooms = []

        for room in target_rooms:

            room_bookings = all_bookings[
                all_bookings["room_number"] == room
            ]

            overlaps = room_bookings[
                (room_bookings["checkin_date"] < candidate_checkout)
                &
                (room_bookings["checkout_date"] > candidate_checkin)
            ]

            if overlaps.empty:
                possible_rooms.append(room)

        if possible_rooms:
            suggestions.append({
                "booking_number": int(candidate["booking_number"]),
                "from_room": source_room,
                "possible_rooms": possible_rooms,
                "checkin_date": str(candidate_checkin.date()),
                "checkout_date": str(candidate_checkout.date())
            })

    return suggestions


# hvilke blokke blokerer for værelse 7 bookinger
def find_room7_blockers(candidates, all_bookings):

    source_room = 7
    target_rooms = [1, 2, 3, 4, 5]

    results = []

    room7_bookings = candidates[
        candidates["room_number"] == source_room
    ].sort_values("checkin_date")

    for _, candidate in room7_bookings.iterrows():

        candidate_checkin = candidate["checkin_date"]
        candidate_checkout = candidate["checkout_date"]

        target_room_blockers = {}

        for room in target_rooms:

            room_bookings = all_bookings[
                all_bookings["room_number"] == room
            ]

            blockers = room_bookings[
                (room_bookings["checkin_date"] < candidate_checkout)
                &
                (room_bookings["checkout_date"] > candidate_checkin)
            ].sort_values("checkin_date")

            target_room_blockers[str(room)] = [
                {
                    "id": int(row["id"]),
                    "booking_number": int(row["booking_number"]),
                    "checkin_date": str(row["checkin_date"].date()),
                    "checkout_date": str(row["checkout_date"].date()),
                    "movable": bool(row["movable"])
                }
                for _, row in blockers.iterrows()
            ]

        results.append({
            "booking_number": int(candidate["booking_number"]),
            "checkin_date": str(candidate_checkin.date()),
            "checkout_date": str(candidate_checkout.date()),
            "blockers": target_room_blockers
        })
        room7_blocker_move_options = []

    return results

#find_block_relocation_options(candidate, blockers, all_bookings)


def find_block_relocation_options(candidate, blockers, all_bookings):

    target_rooms = [1, 2, 3, 4, 5]
    options = []

    for target_room, room_blockers in blockers.items():

        if not room_blockers:
            continue

        if not all(b["movable"] for b in room_blockers):
            continue

        blocker_ids = [
            b["id"]
            for b in room_blockers
        ]

        blocker_rows = all_bookings[
            all_bookings["id"].isin(blocker_ids)
        ]

        for new_room in target_rooms:

            if new_room == int(target_room):
                continue

            room_bookings = all_bookings[
                ~all_bookings["id"].isin(blocker_ids)
            ]

            room_bookings = room_bookings[
                room_bookings["room_number"] == new_room
                ]

            conflict_found = False

            for _, blocker in blocker_rows.iterrows():

                overlaps = room_bookings[
                    (room_bookings["checkin_date"] < blocker["checkout_date"])
                    &
                    (room_bookings["checkout_date"] > blocker["checkin_date"])
                    ]

                if not overlaps.empty:
                    conflict_found = True
                    break

            if not conflict_found:
                options.append({
                    "make_room_for": int(candidate["booking_number"]),
                    "target_room_for_room7_booking": int(target_room),
                    "move_blocker_ids": [int(x) for x in blocker_ids],
                    "move_blockers": [
                        int(x)
                        for x in blocker_rows["booking_number"].tolist()
                    ],
                    "move_blockers_to_room": int(new_room)
                })

    return options


def analyze_period_coverage(
        candidate,
        all_bookings
):

    target_rooms = [1, 2, 3, 4, 5]

    result = {
        "booking_number": int(candidate["booking_number"]),
        "checkin_date": str(candidate["checkin_date"].date()),
        "checkout_date": str(candidate["checkout_date"].date()),
        "daily_free_rooms": {}
    }

    current_day = candidate["checkin_date"]

    while current_day < candidate["checkout_date"]:

        free_rooms = []

        for room in target_rooms:

            room_bookings = all_bookings[
                all_bookings["room_number"] == room
            ]

            overlaps = room_bookings[
                (room_bookings["checkin_date"] <= current_day)
                &
                (room_bookings["checkout_date"] > current_day)
            ]

            if overlaps.empty:
                free_rooms.append(room)

        result["daily_free_rooms"][
            str(current_day.date())
        ] = free_rooms

        current_day += pd.Timedelta(days=1)

    result["period_possible"] = all(
        len(rooms) > 0
        for rooms in result["daily_free_rooms"].values()
    )

    return result


def get_target_rooms(coverage):

    first_day = next(
        iter(coverage["daily_free_rooms"])
    )

    return coverage["daily_free_rooms"][first_day]


def find_connected_blocks(bookings, room_number):

    room_bookings = (
        bookings[
            bookings["room_number"] == room_number
        ]
        .sort_values("checkin_date")
    )

    blocks = []
    current_block = []

    for _, booking in room_bookings.iterrows():

        if not current_block:
            current_block = [booking]
            continue

        previous = current_block[-1]

        if booking["checkin_date"] == previous["checkout_date"]:
            current_block.append(booking)
        else:
            blocks.append(current_block)
            current_block = [booking]

    if current_block:
        blocks.append(current_block)

    result = []

    for block in blocks:

        block_ids = [
            int(row["id"])
            for row in block
        ]

        block_booking_numbers = [
            int(row["booking_number"])
            for row in block
        ]

        block_start = block[0]["checkin_date"]
        block_end = block[-1]["checkout_date"]

        block_movable = all(
            bool(row["movable"])
            for row in block
        )

        result.append({
            "room_number": int(room_number),
            "start": str(block_start.date()),
            "end": str(block_end.date()),
            "booking_ids": block_ids,
            "booking_numbers": block_booking_numbers,
            "movable": block_movable,
            "length": int((block_end - block_start).days)
        })

    return result