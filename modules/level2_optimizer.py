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

        room7_blocker_move_options.extend(options)

    coverage = []

    room7_bookings = eligible[
        eligible["room_number"] == 7
        ]

    for _, candidate in room7_bookings.iterrows():
        coverage_item = analyze_period_coverage(
            candidate,
            season_bookings
        )

        coverage_item["target_room_scores"] = choose_target_rooms(
            coverage_item
        )

        coverage.append(coverage_item)

    target_blocks = []

    for coverage_item in coverage:
        target_blocks.append(
            find_target_block(
                coverage_item,
                room_blocks
            )
        )

    block_move_options = []

    for target in target_blocks:

        if target is None:
            continue

        options = can_block_move(
            target_block=target["block"],
            all_bookings=season_bookings
        )

        block_move_options.append({
            "booking_number": target["booking_number"],
            "target_room": target["target_room"],
            "block_move_options": options
        })
        destination_periods = []

        for target in target_blocks:

            if target is None:
                continue

            destination_periods.append({
                "booking_number": target["booking_number"],
                "target_room": target["target_room"],
                "target_block": target["block"],
                "destination_periods": analyze_destination_periods(
                    target["block"],
                    room_blocks
                )
            })
    return {
        "coverage_count": len(coverage),
        "coverage": coverage,
        "target_blocks": target_blocks,
        "block_move_options": block_move_options,
        "destination_periods": destination_periods
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
            "length": int((block_end - block_start).days),
            "count": len(block)
        })

    return result


def choose_target_rooms(coverage):

    daily_free_rooms = coverage["daily_free_rooms"]

    days = list(daily_free_rooms.keys())

    if not days:
        return []

    first_day = days[0]
    first_day_rooms = daily_free_rooms[first_day]

    room_scores = []

    for room in first_day_rooms:

        free_days = sum(
            room in rooms
            for rooms in daily_free_rooms.values()
        )

        room_scores.append({
            "room": int(room),
            "free_days": int(free_days),
            "total_days": int(len(days)),
            "missing_days": int(len(days) - free_days)
        })

    room_scores = sorted(
        room_scores,
        key=lambda x: x["missing_days"]
    )

    return room_scores


def find_target_block(
        coverage_item,
        room_blocks
):

    if not coverage_item["target_room_scores"]:
        return None

    best_target = coverage_item["target_room_scores"][0]

    target_room = best_target["room"]
    checkin = pd.to_datetime(
        coverage_item["checkin_date"]
    )
    checkout = pd.to_datetime(
        coverage_item["checkout_date"]
    )

    blocks = room_blocks.get(
        str(target_room),
        []
    )

    for block in blocks:

        block_start = pd.to_datetime(
            block["start"]
        )
        block_end = pd.to_datetime(
            block["end"]
        )

        overlaps = (
            block_start < checkout
            and
            block_end > checkin
        )

        if overlaps:
            return {
                "booking_number": coverage_item["booking_number"],
                "target_room": int(target_room),
                "missing_days": int(best_target["missing_days"]),
                "block": block
            }

    return None


def can_block_move(target_block, all_bookings):

    source_room = target_block["room_number"]
    target_rooms = [1, 2, 3, 4, 5]

    block_ids = target_block["booking_ids"]

    block_rows = all_bookings[
        all_bookings["id"].isin(block_ids)
    ]

    options = []

    for new_room in target_rooms:

        if new_room == source_room:
            continue

        room_bookings = all_bookings[
            ~all_bookings["id"].isin(block_ids)
        ]

        room_bookings = room_bookings[
            room_bookings["room_number"] == new_room
        ]

        conflict_found = False

        for _, block_booking in block_rows.iterrows():

            overlaps = room_bookings[
                (room_bookings["checkin_date"] < block_booking["checkout_date"])
                &
                (room_bookings["checkout_date"] > block_booking["checkin_date"])
            ]

            if not overlaps.empty:
                conflict_found = True
                break

        if not conflict_found:
            options.append({
                "move_block_from_room": int(source_room),
                "move_block_to_room": int(new_room),
                "booking_ids": [int(x) for x in block_ids],
                "booking_numbers": target_block["booking_numbers"],
                "start": target_block["start"],
                "end": target_block["end"]
            })

    return options


def analyze_destination_periods(
        target_block,
        room_blocks
):

    source_room = target_block["room_number"]
    target_start = pd.to_datetime(target_block["start"])
    target_end = pd.to_datetime(target_block["end"])

    target_rooms = [1, 2, 3, 4, 5]

    results = []

    for room in target_rooms:

        if room == source_room:
            continue

        room_result = {
            "room": int(room),
            "period_start": str(target_start.date()),
            "period_end": str(target_end.date()),
            "blocking_blocks": []
        }

        for block in room_blocks.get(str(room), []):

            block_start = pd.to_datetime(block["start"])
            block_end = pd.to_datetime(block["end"])

            overlaps = (
                block_start < target_end
                and
                block_end > target_start
            )

            if overlaps:
                room_result["blocking_blocks"].append(block)

        room_result["blocking_count"] = len(
            room_result["blocking_blocks"]
        )

        results.append(room_result)

    return results


