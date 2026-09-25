# Overgang med to loginmetoder

Kode: auth.py, portal_access.py, modules/portal_login.py, pages/1_Booking.py.
Indstillingen er opt-in; legacy er stadig standard. Ingen Cloud Secrets er ændret af agenten.

I den almindelige portals Cloud Secrets:
- Behold alle eksisterende legacy-felter og servernøglen.
- Kopiér SUPABASE_TEST_URL, SUPABASE_TEST_PUBLISHABLE_KEY, TEST_ADMIN_USER_IDS
  og TEST_USER_IDS fra Supabase-testappen. Navnene bevares foreløbig for kompatibilitet.
- Ret den eksisterende AUTH_MODE til "dual" (kun én forekomst).
- Kopiér ikke APP_ENV="test" eller de gamle ENABLE_BOOKING-testflag.

Deploy koden samlet, gem Secrets og reboot. Sidebar viser Nuværende login/Supabase.
Begge valg kræver deres eget login. Skift rydder sessionsdata; legacy-cookie
logges ud gennem authenticator, Supabase-sessionen forsøges afsluttet på serveren.
Ved netværksfejl ryddes lokal adgang stadig, men serverens token kan leve til udløb.

Test begge roller og direkte sideadgang samt skift i begge retninger.
Tilbagefald: AUTH_MODE="legacy" og reboot; øvrige secrets kan blive stående.

Dette flytter login og den allerede testede bookingadgang til hovedportalen.
Mail, optimering, byt værelse, Setup-skrivning og dokumentupload er stadig
begrænset i Supabase-sporet. Nulstilling foretages fortsat via testappens
fungerende mailflow. Testappen skal derfor beholdes under denne overgang.
Der er ingen påstand om fuld drift eller live-verifikation af loginvælgeren endnu.
