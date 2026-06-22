def analyze_improvements(bookings, season):

    from datetime import date

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

    return {
        "season": season,
        "total_bookings": len(season_bookings),
        "movable": len(movable),
        "checked_in": len(checked_in),
        "eligible_for_optimization": len(eligible)
    }
# def analyze_improvements(bookings, season):
#     season_bookings = bookings[
#         bookings["season"] == season
#         ]
#
#     movable_bookings = season_bookings[
#         season_bookings["movable"] == True
#         ]
#
#     return {
#         "season": season,
#         "total_bookings": len(season_bookings),
#         "movable_bookings": len(movable_bookings)
#     }

