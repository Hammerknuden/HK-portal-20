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

    return {
        "season": season,
        "eligible_for_optimization": len(eligible),
        "groupby_index": groupby_result.index.tolist(),
        "groupby_values": groupby_result.values.tolist()
    }
    # return {
    #     "season": int(season),
    #     "eligible_for_optimization": int(len(eligible)),
    #     "room_distribution": room_distribution
    # }

    # return {
    #     "season": season,
    #     "eligible_for_optimization": len(eligible),
    #     "groupby_result": (
    #         eligible
    #         .groupby("room_number")
    #         .size()
    #         .to_dict()
    #     )
    # }
    # return {
    #     "season": season,
    #     "eligible_for_optimization": len(eligible),
    #     "room_numbers_sample": eligible["room_number"].head(10).tolist()
    # }
    # return {
    #     "season": season,
    #     "total_bookings": len(season_bookings),
    #     "movable": len(movable),
    #     "checked_in": len(checked_in),
    #     "eligible_for_optimization": len(eligible),
    #     "room_distribution": room_distribution
    # }
