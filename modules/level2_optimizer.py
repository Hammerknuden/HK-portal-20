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

    room7_blocker_move_options = []

    for item in room7_blockers:
        options = find_block_relocation_options(
            candidate=item,
            blockers=item["blockers"],
            all_bookings=season_bookings
        )

        room7_blocker_move_options.extend(options)

    room_gaps = calculate_gaps(season_bookings)

    return {
        "eligible_for_optimization": int(len(eligible)),
        "room_distribution": room_distribution,
        "room7_suggestions": room7_suggestions,
        "room7_blockers": room7_blockers,
        "room7_blocker_move_options": room7_blocker_move_options
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

        blocker_numbers = [
            b["booking_number"]
            for b in room_blockers
        ]

        blocker_rows = all_bookings[
            all_bookings["booking_number"].isin(blocker_numbers)
        ]

        for new_room in target_rooms:

            if new_room == int(target_room):
                continue

            room_bookings = all_bookings[
                ~all_bookings["booking_number"].isin(blocker_numbers)
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
                    "move_blockers": blocker_numbers,
                    "move_blockers_to_room": int(new_room)
                })

    return options