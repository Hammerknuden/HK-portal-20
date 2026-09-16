"""Read-only search for complete room assignments; stays are never split."""

from collections import deque
from time import monotonic

import pandas as pd

from common import exclude_cancelled_bookings


ROOMS = (1, 2, 3, 4, 5)


def prepare_bookings(bookings):
    if bookings.empty:
        return bookings.copy()
    required = {"id", "booking_number", "season", "room_number",
                "checkin_date", "checkout_date", "movable"}
    if not required.issubset(bookings.columns):
        raise ValueError("Bookingdata mangler nødvendige felter.")
    # Booking numbers can repeat between seasons. Cancellation grouping must
    # not cancel an unrelated booking from another year's conflict baseline.
    rows = pd.concat([
        exclude_cancelled_bookings(group)
        for _, group in bookings.groupby("season", dropna=False)
    ]).copy()
    for column in ("id", "room_number"):
        values = pd.to_numeric(rows[column], errors="coerce")
        if values.isna().any() or (values % 1 != 0).any():
            raise ValueError("Bookingdata har ugyldigt ID eller værelsesnummer.")
        rows[column] = values.astype(int)
    if rows["id"].duplicated().any():
        raise ValueError("Bookingdata indeholder samme database-ID flere gange.")
    rows["season"] = pd.to_numeric(rows["season"], errors="coerce")
    for column in ("checkin_date", "checkout_date"):
        rows[column] = pd.to_datetime(rows[column], errors="coerce")
    relevant = rows[rows["room_number"].isin((*ROOMS, 7))]
    if relevant[["checkin_date", "checkout_date"]].isna().any().any():
        raise ValueError("Bookingdata indeholder ugyldige opholdsdatoer.")
    if (relevant["checkout_date"] <= relevant["checkin_date"]).any():
        raise ValueError("Afrejse skal ligge efter ankomst.")
    if any(relevant[c].ne(relevant[c].dt.normalize()).any()
           for c in ("checkin_date", "checkout_date")):
        raise ValueError("Analysen kræver opholdsdatoer uden klokkeslæt.")
    return rows


def movable_ids(rows, today):
    return set(rows.loc[
        rows["movable"].eq(True).fillna(False)
        & (rows["checkin_date"].dt.date > today), "id"
    ])


def overlaps(a, b):
    return a["checkin_date"] < b["checkout_date"] and b["checkin_date"] < a["checkout_date"]


def assignment_conflicts(records, assignments, rooms=ROOMS):
    conflicts = []
    for room in rooms:
        ordered = sorted(
            (r for r in records.values() if assignments.get(r["id"], r["room_number"]) == room),
            key=lambda r: (r["checkin_date"], r["id"]),
        )
        active = []
        for row in ordered:
            active = [a for a in active if a["checkout_date"] > row["checkin_date"]]
            conflicts.extend((a["id"], row["id"]) for a in active)
            active.append(row)
    return conflicts


def _validate(records, allowed, candidate_id, assignments):
    candidate = records.get(candidate_id)
    if not candidate or candidate["room_number"] != 7 or candidate_id not in assignments:
        return False
    for identifier, destination in assignments.items():
        row = records.get(identifier)
        if row is None or identifier not in allowed or destination not in ROOMS:
            return False
        if row["room_number"] == destination:
            return False
        if identifier != candidate_id and row["room_number"] not in ROOMS:
            return False
    touched = set(assignments.values()) | {
        records[i]["room_number"] for i in assignments if i != candidate_id
    }
    return not assignment_conflicts(records, assignments, touched)


def validate_plan(bookings, plan, today):
    """Revalidate a displayed plan against fresh rows, including stale dates/rooms."""
    try:
        rows = prepare_bookings(bookings)
        records = {r["id"]: r for r in rows.to_dict("records")
                   if r["room_number"] in (*ROOMS, 7) and r["checkout_date"] > pd.Timestamp(today)}
        assignments = {}
        for move in plan["moves"]:
            identifier = move["id"]
            row = records.get(identifier)
            if row is None or identifier in assignments:
                return False
            if row["room_number"] != move["from_room"]:
                return False
            if any(row[c].date().isoformat() != move[c] for c in ("checkin_date", "checkout_date")):
                return False
            assignments[identifier] = move["to_room"]
        if assignments.get(plan["candidate_id"]) != plan["target_room"]:
            return False
        season = records[plan["candidate_id"]]["season"]
        allowed = movable_ids(rows[rows["season"] == season], today)
        return _validate(records, allowed, plan["candidate_id"], assignments)
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def _plan(records, candidate_id, assignments, kind, window=None):
    moves = []
    for identifier in sorted(assignments, key=lambda i: (i == candidate_id, records[i]["checkin_date"], i)):
        row = records[identifier]
        moves.append({
            "id": identifier, "booking_number": row["booking_number"],
            "from_room": row["room_number"], "to_room": assignments[identifier],
            "checkin_date": row["checkin_date"].date().isoformat(),
            "checkout_date": row["checkout_date"].date().isoformat(),
        })
    return {
        "candidate_id": candidate_id, "target_room": assignments[candidate_id],
        "moves": moves, "kind": kind, "window": window,
        "moved_existing": len(assignments) - 1,
        "affected_rooms": sorted({m["from_room"] for m in moves if m["from_room"] != 7} | set(assignments.values())),
    }


def search_improvements(bookings, season, today, *, max_moves=3,
                        max_states=2000, seconds_per_phase=1.0, max_options=25):
    """Short conflict-driven chains plus two-room exchanges at whole-stay boundaries.

    Each target gets its own budget, so a difficult first room cannot hide a
    direct option in another room. Long two-room exchanges are not limited by
    max_moves. Results are independent alternatives for one temp booking.
    """
    if max_moves < 0 or max_states < 1 or seconds_per_phase <= 0 or max_options < 1:
        raise ValueError("Søgegrænser skal være positive (max_moves kan være 0).")
    output = {"schema_version": 3, "recommendations": [], "errors": [],
              "analysis_date": today.isoformat(),
              "limits": {"max_chain_moves": max_moves, "max_states_per_phase": max_states,
                         "seconds_per_phase": seconds_per_phase, "max_options_per_target": max_options}}
    try:
        rows = prepare_bookings(bookings)
    except ValueError as exc:
        output["errors"].append(str(exc))
        return output
    if rows.empty:
        return output
    records = {r["id"]: r for r in rows.to_dict("records")
               if r["room_number"] in (*ROOMS, 7) and r["checkout_date"] > pd.Timestamp(today)}
    # Other seasons remain occupied, but may never be moved by this analysis.
    allowed = movable_ids(rows[rows["season"] == season], today)
    candidates = rows[(rows["room_number"] == 7) & (rows["season"] == season) & rows["id"].isin(allowed)]
    physical = {i: r for i, r in records.items() if r["room_number"] in ROOMS}
    # Existing overlaps make daily room capacity ambiguous. Do not optimize corrupt data.
    if assignment_conflicts(physical, {}):
        output["errors"].append("Der er allerede overlap på værelse 1–5 i datagrundlaget. Ret dem før analysen.")
        return output
    for candidate in candidates.sort_values(["checkin_date", "id"]).to_dict("records"):
        cid = candidate["id"]
        days = list(pd.date_range(candidate["checkin_date"], candidate["checkout_date"], inclusive="left"))
        daily = {
            day.date().isoformat(): [room for room in ROOMS if not any(
                r["room_number"] == room and r["checkin_date"] <= day < r["checkout_date"]
                for r in physical.values()
            )] for day in days
        }
        rec = {"candidate_id": cid, "booking_number": candidate["booking_number"],
               "checkin_date": candidate["checkin_date"].date().isoformat(),
               "checkout_date": candidate["checkout_date"].date().isoformat(),
               "period_possible": all(daily.values()), "daily_free_rooms": daily,
               "no_capacity_dates": [d for d, free in daily.items() if not free],
               "options": [], "target_results": []}
        output["recommendations"].append(rec)
        if not rec["period_possible"]:
            rec["status"] = "no_capacity"
            continue
        for target in ROOMS:
            found = {}
            visited = set()
            examined = 0
            limited = False
            deadline = monotonic() + seconds_per_phase
            initial_blockers = [i for i, r in physical.items() if r["room_number"] == target and overlaps(candidate, r)]

            def accept(assignments, kind, window=None):
                if _validate(records, allowed, cid, assignments):
                    key = tuple(sorted(assignments.items()))
                    found.setdefault(key, _plan(records, cid, assignments, kind, window))

            def budget():
                nonlocal examined, limited
                if examined >= max_states or monotonic() >= deadline:
                    limited = True
                    return False
                examined += 1
                return True

            if not initial_blockers:
                accept({cid: target}, "direct")
            elif all(i in allowed for i in initial_blockers):
                # Enumerate common cut points, including exchange to the last
                # checkout in supplied data. No stay may straddle either cut.
                for other in ROOMS:
                    if other == target:
                        continue
                    pair = [r for r in physical.values() if r["room_number"] in (target, other)]
                    dates = sorted({r[c] for r in pair if r["season"] == season
                                    for c in ("checkin_date", "checkout_date") if r[c].date() > today})
                    cuts = [d for d in dates if not any(r["checkin_date"] < d < r["checkout_date"] for r in pair)]
                    starts = [d for d in cuts if d <= min(records[i]["checkin_date"] for i in initial_blockers)]
                    ends = [d for d in cuts if d >= max(records[i]["checkout_date"] for i in initial_blockers)]
                    for start in reversed(starts):
                        for end in ends:
                            if not budget():
                                break
                            assignments = {cid: target}
                            for r in pair:
                                if start <= r["checkin_date"] and r["checkout_date"] <= end:
                                    assignments[r["id"]] = other if r["room_number"] == target else target
                            accept(assignments, "block_exchange", [start.date().isoformat(), end.date().isoformat()])
                        if limited:
                            break
                    if limited:
                        break

                # Independent budget for short chains: large window searches
                # must not crowd out a small delblock relocation.
                examined = 0
                deadline = monotonic() + seconds_per_phase
                queue = deque([{cid: target}])
                while queue:
                    if not budget():
                        break
                    assignment = queue.popleft()
                    key = tuple(sorted(assignment.items()))
                    if key in visited:
                        continue
                    visited.add(key)
                    conflicts = assignment_conflicts({**physical, cid: candidate}, assignment)
                    if not conflicts:
                        accept(assignment, "relocation")
                        continue
                    if len(assignment) - 1 >= max_moves:
                        limited = True
                        continue
                    a, b = conflicts[0]
                    # Moved rows have their final destination; only an unmoved
                    # blocker can resolve a new conflict. Both choices are tried.
                    for identifier in (a, b):
                        if identifier in assignment or identifier not in allowed:
                            continue
                        row = records[identifier]
                        if row["room_number"] not in ROOMS:
                            continue
                        for destination in ROOMS:
                            if destination == row["room_number"]:
                                continue
                            if any(destination == dest and overlaps(row, records[i]) for i, dest in assignment.items()):
                                continue
                            queue.append({**assignment, identifier: destination})

            ordered = sorted(found.values(), key=lambda p: (p["moved_existing"], len(p["affected_rooms"]),
                             tuple((m["id"], m["to_room"]) for m in p["moves"])))
            omitted = max(0, len(ordered) - max_options)
            for plan in ordered[:max_options]:
                plan["missing_dates"] = [d for d, free in daily.items() if target not in free]
            rec["options"].extend(ordered[:max_options])
            rec["target_results"].append({"room": target, "limited": limited,
                "omitted_options": omitted, "found": len(ordered),
                "locked_blocker_ids": [i for i in initial_blockers if i not in allowed]})
        rec["options"].sort(key=lambda p: (p["moved_existing"], len(p["affected_rooms"]), p["target_room"]))
        rec["status"] = ("ready" if any(p["moved_existing"] == 0 for p in rec["options"])
                         else "rearrangement" if rec["options"] else "not_found")
    return output
