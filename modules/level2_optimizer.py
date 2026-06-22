def analyze_improvements(bookings, season):
    season_bookings = bookings[
        bookings["season"] == season
        ]

    movable_bookings = season_bookings[
        season_bookings["movable"] == True
        ]

    return {
        "season": season,
        "total_bookings": len(season_bookings),
        "movable_bookings": len(movable_bookings)
    }

