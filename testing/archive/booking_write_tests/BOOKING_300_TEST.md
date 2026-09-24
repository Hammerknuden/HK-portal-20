> Arkiveret vejledning fra afsluttet skrivetest. Se README.md i denne mappe.

# Booking 300: October write test

Original Supabase Auth test app, shared production database. Legacy remains unchanged.

1. Run testing/archive/booking_write_tests/enable_booking_300_test.sql once in the original Supabase project. It validates RLS, exactly one existing 2026 booking 300 named NN with dates October 1–4, and expected existing write policies. The policy captures that row ID; no booking is inserted or deleted. Unexpected state aborts the transaction.
2. Deploy portal_access.py, testing/write_probe.py, testing/app.py and pages/1_Booking.py together. Include tests/test_booking_300_scope.py and the SQL file in version control.
3. Keep ENABLE_BOOKING_WRITE_PROBE = true and add ENABLE_BOOKING_300_TEST = true at the top level of the test app's Secrets.
4. Reboot the test app after deployment (legacy too if it reports a stale import).
5. As Finn or Naja, select Booking, 2026, Rediger booking, booking 300 / NN. Change breakfast or arrival time and save. Reload and verify persisted values, also using the other admin account.

Dates must stay within October 2026, checkout at latest November 1. Booking number stays 300 and name NN. The original setup grants UPDATE to administrators; the additional ordinary-user setup is described below. This enables the normal edit form only, not creation, deletion, room swapping, uploads or other tables. Timeline editing is now covered below. The database policy permits UPDATE of the captured test row; the app additionally restricts columns to the edit form. Changes affect live occupancy/statistics.

After testing, set ENABLE_BOOKING_300_TEST = false and run:

```sql
DROP POLICY auth_booking_300_update ON public.hk_dtb;
```

Remove the test booking through legacy when no longer needed. The 2099 test is separate.

Validation: 34 local unit tests passed; SQL and live UPDATE require the user's Cloud/Supabase steps above.

## Ordinary booking user

Run `testing/archive/booking_write_tests/enable_booking_300_user_test.sql` once to add the existing ordinary test
user (4399ca28-e347-43c5-b22f-6e8be0772f61) to the same bounded UPDATE test.
The original administrator policy stays in place. No admin role or Storage access
is granted. Keep both existing feature flags true, and the UID in TEST_USER_IDS.
Deploy portal_access.py, pages/1_Booking.py and testing/app.py together, then reboot.
Test saving and reloading booking 300 as this user; verify Setup, Booking.com and
private document download remain unavailable. The 2099 probe remains admin only.
Creation remains unfinished. Timeline editing is now covered below.
For cleanup also run `DROP POLICY auth_booking_300_user_update ON public.hk_dtb;`.

## Timeline editing

Timeline now uses the existing booking-300 policies and both existing flags.
No additional SQL is required. Approved ordinary users and admins can edit booking
300 / NN via Administrer bookinger. Keep the name and number; dates stay in October.
Test comments, room and dates, then save. The app checks one updated row, reads back
all submitted fields, and preserves the success message across reruns.
Other bookings, deletion, room swaps and optimizer writes remain blocked in this
Supabase test. Legacy follows its existing access path.
