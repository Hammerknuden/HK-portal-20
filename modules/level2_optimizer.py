import pandas as pd
from datetime import date


def analyze_improvements(bookings, season):

    today = date.today()

    season_bookings = bookings[
        bookings["season"] == season
    ]

    movable = season_bookings[
        season_bookings["movable"] == True
    ]

    checked_in = season_bookings[
        pd.to_datetime(
            season_bookings["checkin_date"]
        ).dt.date <= today
    ]

    eligible = season_bookings[
        (season_bookings["movable"] == True)
        &
        (
            pd.to_datetime(
                season_bookings["checkin_date"]
            ).dt.date > today
        )
    ]
    raw_distribution = (
        eligible
        .groupby("room_number")
        .size()
        .to_dict()
    )
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
        "eligible_for_optimization": int(len(eligible)),
        "room_distribution": room_distribution
    }