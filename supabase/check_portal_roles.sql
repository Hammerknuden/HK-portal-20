-- Optional installation checks. Run immediately after enable_portal_roles.sql as postgres.
-- Temporary role changes are in ONE transaction and always rolled back.
BEGIN;
SET LOCAL lock_timeout='5s';
DO $$ DECLARE denied boolean := false;
BEGIN
 IF current_user <> 'postgres' THEN RAISE EXCEPTION 'Run as postgres'; END IF;
 LOCK TABLE public.portal_members IN SHARE ROW EXCLUSIVE MODE;
 PERFORM set_config('request.jwt.claim.sub','c8fb3b6c-00ed-4883-a52f-ef182f10ec3e',true);
 IF public.portal_current_role() IS DISTINCT FROM 'admin' THEN RAISE EXCEPTION 'Finn not active admin'; END IF;
 UPDATE public.portal_members SET active=false WHERE role='admin' AND user_id<>auth.uid();
 BEGIN
  PERFORM public.portal_set_member(auth.uid(),'user',true,'admin',true);
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM='Cannot remove the last active administrator' THEN denied:=true; ELSE RAISE; END IF;
 END;
 IF NOT denied THEN RAISE EXCEPTION 'Last administrator protection FAILED'; END IF;
 PERFORM set_config('request.jwt.claim.sub','4399ca28-e347-43c5-b22f-6e8be0772f61',true);
 UPDATE public.portal_members SET role='user',active=true WHERE user_id=auth.uid();
 denied:=false;
 BEGIN
  PERFORM public.portal_set_member(auth.uid(),'admin',true,'user',true);
 EXCEPTION WHEN insufficient_privilege THEN denied:=true;
 END;
 IF NOT denied THEN RAISE EXCEPTION 'User self-promotion protection FAILED'; END IF;
 UPDATE public.portal_members SET active=false WHERE user_id=auth.uid();
 IF public.portal_current_role() IS NOT NULL THEN RAISE EXCEPTION 'Disabled role still active'; END IF;
END $$;
SET LOCAL ROLE authenticated;
DO $$ DECLARE t text; n bigint; denied boolean := false;
BEGIN
 FOREACH t IN ARRAY ARRAY['hk_dtb','historie_new','bookin_pace','high_season','breakfast_notes','Events','statistik_historik'] LOOP
  EXECUTE format('SELECT count(*) FROM public.%I',t) INTO n;
  IF n<>0 THEN RAISE EXCEPTION 'Disabled user can read %',t; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM storage.objects WHERE bucket_id='guest-registrations') THEN
 RAISE EXCEPTION 'Disabled user can read guest documents'; END IF;
 BEGIN
  PERFORM public.apply_calendar_moves_authenticated(gen_random_uuid(),2027,'[]'::jsonb);
 EXCEPTION WHEN insufficient_privilege THEN denied:=true;
 END;
 IF NOT denied THEN RAISE EXCEPTION 'Disabled user can call calendar RPC'; END IF;
END $$;
ROLLBACK;
SELECT 'Kontrol bestået. Alle midlertidige rolleændringer er rullet tilbage.' AS resultat;
