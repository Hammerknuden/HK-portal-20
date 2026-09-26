def execute_room_swap(
    supabase,
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

    from portal_access import uses_supabase_auth
    if uses_supabase_auth():
        response = supabase.rpc("swap_booking_rooms", {
            "p_a": booking_a_ids, "p_b": booking_b_ids,
            "p_room_a": room_a, "p_room_b": room_b,
        }).execute()
        if not isinstance(response.data, dict) or response.data.get("success") is not True:
            raise ValueError("Byttet kunne ikke bekræftes. Genindlæs bookingerne.")
        return response.data

    result_a = (
        supabase
        .table("hk_dtb")
        .update({"room_number": room_b})
        .in_("id", booking_a_ids)
        .execute()
    )

    result_b = (
        supabase
        .table("hk_dtb")
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