# Test af den gendannede backup med eksisterende login

Opret en separat Streamlit Cloud-app fra samme repository og branch som
produktionsappen. Main file path skal være `restore_test_app.py`.
Vælg en særskilt adresse, fx hammerknuden-backup-test hvis den er ledig.
Produktionsappens entrypoint og Secrets må ikke ændres.

Indsæt indholdet af `testing/restore-secrets.example.toml` i den nye apps Secrets.
Erstat SUPABASE_KEY med testprojektets server-secret/service_role-nøgle.
RESTORE_TEST_COOKIE_KEY skal være en ny tilfældig hemmelighed, fx genereret af
en adgangskodeadministrator. Ingen SMTP- eller produktionsnøgler skal kopieres.

Testprojektet er låst til ycasinssaffzpsyhgzgf. Login bruger samme brugere,
adgangskoder og administratorroller som produktionens eksisterende authenticator.
Login-cookie har eget navn og signeringsnøgle. Den nye Supabase Auth-løsning
og dens eksisterende testapp er uændrede.

Alle sider viser TEST-markeringen via den fælles navigation. De to centrale
mailfunktioner springer SMTP over i dette miljø. Et bookingflow kan stadig
gemme data i testdatabasen efter den simulerede mailafsendelse. Siderne kan vise
deres sædvanlige succesbesked; TEST-beskeden fortæller, at mail ikke blev sendt.
Backupknappen er deaktiveret i testappen.

## Kontrolplan – ikke udført endnu

1. Åbn testappens sider uden login, også via direkte links: ingen gæstedata.
2. Log ind med forkert kode: adgang afvises.
3. Log ind som almindelig bruger: test almindelige sider; Setup,
   Booking.com-kontrol og download af registreringsdokumenter skal afvises.
4. Log ind som administrator: kontrollér disse sider og dokumentdownload.
5. Sammenlign bookinger, statistik, historik og priser med backupgrundlaget.
6. Test en tydeligt mærket prøvebooking og ændring i testdatabasen. Bekræft
   at ingen mail sendes; afslut med logout og kontrol af afvist adgang.

Service_role/secret omgår RLS: ovenstående afprøver appens rollegrænser.
Supabase-brugerbaserede Storage-politikker er ikke bevist af denne test og er
ikke gendannet endnu. Testprojektets buckets forbliver private.
Ændringer af testdata betyder, at tidligere rækkeantal ikke længere er en
gyldig løbende sammenligning; de tidligere gendannelsesrapporter bevares.
