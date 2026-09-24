> Arkiveret vejledning fra afsluttet skrivetest. Se README.md i denne mappe.

# Booking 301 creation test

Run testing/archive/booking_write_tests/enable_booking_301_test.sql once in the original Supabase project.
It requires RLS, the three existing users, and no booking 301 in season 2026.
It adds a bounded INSERT policy and partial unique index, preventing concurrent duplicates.
Existing SELECT policies provide readback. No booking is created by this SQL.

Deploy pages/1_Booking.py, portal_access.py and testing/write_probe.py together.
Add ENABLE_BOOKING_301_TEST = true at top level of the test app Secrets.
Keep ENABLE_BOOKING_WRITE_PROBE = true. Reboot after deployment.

In Booking / 2026 / Ny booking, use number 301, name AA, October 2–6, one room.
Fill the usual form and click Opret testbooking 301 near the mail section.
No SMTP, Excel export or data email executes on this test branch.
Room 7 follows the current creation form; this test affects the shared live database.
The app checks for an existing booking, inserts once, and confirms identity/dates by readback.
The success message remains on screen. Reload to check the booking in the overview.

All three approved users may create it, but only one row may exist. To repeat with a
second user, first remove the test row through legacy. Editing 301 is not enabled;
booking 300 remains the editing test.

When finished, set ENABLE_BOOKING_301_TEST = false and use the cleanup SQL comments.
The feature is not deployed and the SQL is not executed by the coding agent.
