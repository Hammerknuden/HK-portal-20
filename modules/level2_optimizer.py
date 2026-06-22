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
    room_distribution = (
        eligible
        .groupby("room_number")
        .size()
        .to_dict()
    )

    return {
        "season": season,
        "total_bookings": len(season_bookings),
        "movable": len(movable),
        "checked_in": len(checked_in),
        "eligible_for_optimization": len(eligible),
        "room_distribution": room_distribution
    }
