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

    room_gaps = calculate_gaps(season_bookings)

    return {
        "season": int(season),
        "eligible_for_optimization": int(len(eligible)),
        "room_distribution": room_distribution,
        "room_gaps": room_gaps
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
def find_room7_move_options(bookings):

    source_room = 7
    target_rooms = [1, 2, 3, 4, 5]

    suggestions = []

    room7_bookings = bookings[
        bookings["room_number"] == source_room
    ].sort_values("checkin_date")

    for _, candidate in room7_bookings.iterrows():

        candidate_checkin = candidate["checkin_date"]
        candidate_checkout = candidate["checkout_date"]

        possible_rooms = []

        for room in target_rooms:

            room_bookings = bookings[
                bookings["room_number"] == room
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