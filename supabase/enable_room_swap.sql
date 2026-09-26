-- Install as postgres. Does not move bookings by itself.
BEGIN;
CREATE OR REPLACE FUNCTION public.swap_booking_rooms(
 p_a bigint[], p_b bigint[], p_room_a integer, p_room_b integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER
SET search_path=pg_catalog SET lock_timeout='5s'
AS $$
DECLARE ids bigint[]; expected integer; affected integer;
BEGIN
 IF auth.uid() IS NULL OR auth.uid() NOT IN (
 'c8fb3b6c-00ed-4883-a52f-ef182f10ec3e'::uuid,
 '74acf117-be21-4460-877d-4f50993ac6da'::uuid,
 '4399ca28-e347-43c5-b22f-6e8be0772f61'::uuid) THEN
   RAISE EXCEPTION 'Ingen adgang til bytte';
 END IF;
 IF coalesce(cardinality(p_a),0)=0 OR coalesce(cardinality(p_b),0)=0
 OR p_room_a IS NULL OR p_room_b IS NULL OR p_room_a=p_room_b
 OR p_room_a NOT BETWEEN 1 AND 7 OR p_room_b NOT BETWEEN 1 AND 7 THEN
   RAISE EXCEPTION 'Ugyldigt bytte';
 END IF;
 ids := p_a || p_b; expected := cardinality(ids);
 IF expected>1000 OR (SELECT count(DISTINCT x) FROM unnest(ids) x)<>expected THEN
   RAISE EXCEPTION 'Ugyldige booking-IDer';
 END IF;
 LOCK TABLE public.hk_dtb IN SHARE ROW EXCLUSIVE MODE;
 IF (SELECT count(*) FROM public.hk_dtb WHERE id=ANY(ids))<>expected
 OR (SELECT count(DISTINCT season) FROM public.hk_dtb WHERE id=ANY(ids))<>1
 OR EXISTS(SELECT 1 FROM public.hk_dtb WHERE id=ANY(ids) AND (
   movable IS DISTINCT FROM true
   OR checkin_date <= (statement_timestamp() AT TIME ZONE 'Europe/Copenhagen')::date
   OR season IS NULL OR checkin_date IS NULL OR checkout_date IS NULL OR checkout_date<=checkin_date
   OR lower(btrim(coalesce(web,'')))='cansl'
   OR room_number IS DISTINCT FROM CASE WHEN id=ANY(p_a) THEN p_room_a ELSE p_room_b END)) THEN
   RAISE EXCEPTION 'Bookingerne er ændret eller ugyldige. Genindlæs før nyt bytte';
 END IF;
 -- Compare the projected placement of all affected rows with all other active rows.
 IF EXISTS (
   SELECT 1 FROM public.hk_dtb a JOIN public.hk_dtb b ON a.id<>b.id
   WHERE a.id=ANY(ids) AND lower(btrim(coalesce(b.web,'')))<>'cansl'
   AND (CASE WHEN a.id=ANY(p_a) THEN p_room_b ELSE p_room_a END)
       = (CASE WHEN b.id=ANY(p_a) THEN p_room_b WHEN b.id=ANY(p_b) THEN p_room_a ELSE b.room_number END)
   AND a.checkin_date<b.checkout_date AND b.checkin_date<a.checkout_date
 ) THEN RAISE EXCEPTION 'Bytte afvist: et værelse er optaget i perioden'; END IF;
 UPDATE public.hk_dtb SET room_number=CASE WHEN id=ANY(p_a) THEN p_room_b ELSE p_room_a END
 WHERE id=ANY(ids);
 GET DIAGNOSTICS affected=ROW_COUNT;
 IF affected<>expected THEN RAISE EXCEPTION 'Byttet blev ikke gemt samlet'; END IF;
 RETURN jsonb_build_object('success',true,'updated',affected);
END $$;
REVOKE ALL ON FUNCTION public.swap_booking_rooms(bigint[],bigint[],integer,integer) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.swap_booking_rooms(bigint[],bigint[],integer,integer) TO authenticated;
COMMIT;
