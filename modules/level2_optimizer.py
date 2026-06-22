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

    return {
        "season": int(season),
        "total_bookings": int(len(season_bookings)),
        "movable": int(len(movable)),
        "checked_in": int(len(checked_in)),
        "eligible_for_optimization": int(len(eligible)),
        "room_distribution": room_distribution
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

        for _, booking in room_bookings.iterrows():

            if previous_checkout is not None:

                gap = (
                    booking["checkin_date"]
                    - previous_checkout
                ).days

                if gap > 0:
                    room_gaps.append(gap)

            previous_checkout = booking["checkout_date"]

        gaps[int(room)] = room_gaps

    return gaps