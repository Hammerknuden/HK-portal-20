def execute_room_swap(
    supabase,
    table_name,
    booking_a_ids,
    booking_b_ids,
    room_a,
    room_b,
):
    """
    Bytter værelser mellem to bookingblokke.

    booking_a_ids og booking_b_ids er lister,
    så funktionen også senere kan bruges til blokke
    med flere database-rækker.
    """

    booking_a_ids = [int(x) for x in booking_a_ids]
    booking_b_ids = [int(x) for x in booking_b_ids]

    room_a = int(room_a)
    room_b = int(room_b)

    result_a = (
        supabase
        .table(table_name)
        .update({"room_number": room_b})
        .in_("id", booking_a_ids)
        .execute()
    )

    result_b = (
        supabase
        .table(table_name)
        .update({"room_number": room_a})
        .in_("id", booking_b_ids)
        .execute()
    )

    return {
        "success": True,
        "booking_a_ids": booking_a_ids,
        "booking_b_ids": booking_b_ids,
        "room_a_before": room_a,
        "room_b_before": room_b,
        "room_a_after": room_b,
        "room_b_after": room_a,
        "result_a": result_a.data,
        "result_b": result_b.data,
    }