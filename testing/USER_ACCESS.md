# Test af almindelige portalsider

Testappen har nu en sidemenu. Booking, Databaseopslag, In and Out, Links,
Breakfast, Timeline og Statistik er tilgængelige for godkendte brugere.
Setup og Booking.com-afstemning er kun til administratorer; auth.py kontrollerer
også rollen på selve siden. Produktion bruger fortsat legacy som standard.

Tilføj i TESTAPPENS Secrets (bevar de eksisterende felter):

```toml
TEST_USER_IDS = ["4399ca28-e347-43c5-b22f-6e8be0772f61"]
```

Behold TEST_ADMIN_USER_IDS uændret. Brugere uden for begge lister afvises.
Udfyld samme UID i testing/enable_user_read_access.sql og kør filen manuelt
i Supabase SQL Editor. SQL-filen er ikke en automatisk migration. Den ændrer
kun SELECT-politikker for denne testbruger. Eksisterende administratorpolitikker
bevares. Kør kun med det UID, der faktisk skal kunne læse portalens data.

Testmiljøet blokerer database- og Storage-skrivninger i klientens HTTP-transport.
Bookingens mail/eksport-flow er også blokeret. Brugernes databasepolitik giver
kun SELECT. Private dokumenter kræver fortsat særskilte Storage-politikker.
Dette er en test af side- og læseadgang; redigering er endnu ikke aktiveret.

Commit/push portal_access.py, auth.py, ændringerne i pages/, testing/app.py,
testing/auth_client.py, testing/requirements.txt, denne vejledning,
testing/enable_user_read_access.sql og tests/test_portal_access.py.
Undlad lokale Secrets og andre uvedkommende ændringer.
Cloud skal geninstallere afhængigheder: testappen bruger nu hele portalens
requirements.txt gennem testing/requirements.txt.

Kontrollér først login og læsetest som almindelig bruger, derefter hver side.
Setup og Booking.com-afstemning må kun kunne vælges som administrator.
Kontrollér også legacy-login og de samme sider i produktionsappen.
