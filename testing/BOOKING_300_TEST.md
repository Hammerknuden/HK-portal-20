# Booking 300: October write test

Original Supabase Auth test app, shared production database. Legacy remains unchanged.

1. Run testing/enable_booking_300_test.sql once in the original Supabase project. It validates RLS, exactly one existing 2026 booking 300 named NN with dates October 1–4, and expected existing write policies. The policy captures that row ID; no booking is inserted or deleted. Unexpected state aborts the transaction.
2. Deploy portal_access.py, testing/write_probe.py, testing/app.py and pages/1_Booking.py together. Include tests/test_booking_300_scope.py and the SQL file in version control.
3. Keep ENABLE_BOOKING_WRITE_PROBE = true and add ENABLE_BOOKING_300_TEST = true at the top level of the test app's Secrets.
4. Reboot the test app after deployment (legacy too if it reports a stale import).
5. As Finn or Naja, select Booking, 2026, Rediger booking, booking 300 / NN. Change breakfast or arrival time and save. Reload and verify persisted values, also using the other admin account.

Dates must stay within October 2026, checkout at latest November 1. Booking number stays 300 and name NN. Ordinary users are not granted UPDATE. This enables the normal edit form only, not creation, deletion, room swapping, uploads or other tables. The database policy permits UPDATE of the captured test row; the app additionally restricts columns to the edit form. Changes affect live occupancy/statistics.

After testing, set ENABLE_BOOKING_300_TEST = false and run:

```sql
DROP POLICY auth_booking_300_update ON public.hk_dtb;
```

Remove the test booking through legacy when no longer needed. The 2099 test is separate.

Validation: 34 local unit tests passed; SQL and live UPDATE require the user's Cloud/Supabase steps above.
