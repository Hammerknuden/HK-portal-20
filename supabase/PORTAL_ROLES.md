# Roller og aktivering fra Setup

## Installation – SQL først, derefter kode

1. Kør HELE `supabase/enable_portal_roles.sql` som postgres i det oprindelige Supabase-projekt. Scriptet skal afsluttes med tre medlemmer: Finn og Naja som aktive admin, den oprindelige almindelige bruger som aktiv user. Den nye invitation afventer stadig aktivering. Hvis scriptet stopper, må koden ikke pushes endnu; send fejlteksten. Transaktionen ruller tilbage ved fejl.
2. Kør eventuelt hele `supabase/check_portal_roles.sql` som postgres. Kontrollen afprøver sidste administrator, selvopgradering, deaktiveret læseadgang og kalender-RPC. Midlertidige rolleændringer rulles tilbage; bookinger ændres ikke. Ved fejl: kør ROLLBACK, før du fortsætter.
3. Commit og push kodeændringerne, det nye modules/portal_roles.py, test og SQL/vejledning. Vent på Cloud-opdateringen.
4. Log ind som Finn eller Naja, og åbn Setup. Aktivér den inviterede bruger som almindelig bruger. Invitationen skal være accepteret først.
5. Log ind med den nye bruger. Kontrollér Booking, Kalender, Morgenmad og Statistik samt afvisning på Setup og gæstedokumenter. Afprøv kun skrivning på en tydelig testbooking.
6. Som administrator: deaktiver testbrugeren. Dens næste sidehandling og direkte databasekald skal afvises; allerede viste oplysninger forsvinder ikke fra en åben browserside før genindlæsning. Genaktivér den og kontrollér login igen.
7. Test eventuelt en midlertidig opgradering af testbrugeren til administrator og derefter tilbage til almindelig bruger. Kontroller Setup, dokumentadgang og permanent sletning. Fjern ikke jeres egen sidste aktive administrator.

## Hvad ændres

`public.portal_members` er nu sandhedskilden for rolle og aktiv adgang. Gamle ADMIN_USER_IDS, USER_IDS og TEST_...-lister bruges ikke til produktionsrettigheder. De kan beholdes i Secrets indtil installationen er testet, men ændring af dem giver ingen ny adgang. Hvis rolleopslaget fejler, afvises login; der er ingen fallback til gamle administratorlister.

Finn og Naja samt den oprindelige bruger indsættes kun ved første installation. En genkørsel ændrer ikke eksisterende roller eller deaktiveringer. Ingen adgangskoder eller bookingdata ændres.

SQL erstatter politikker på de syv portal-tabeller og indfører aktuelle rollekrav på gæsteregistreringer. Andre Storage-buckets bevares. Oprindelige politikker og RPC-definitioner gemmes i det private schema portal_private til manuel fejlsøgning. Funktioner til bytning, optimering, kalender og sæsonafslutning ændres kun i adgangskontrollen; deres installerede forretningslogik bevares. Ved ukendte funktioner/politikker stopper installationen.

Rolleændringer køres med administratorens bruger-token, ikke service-nøglen. Databasefunktionen serialiserer ændringer, kontrollerer rollen igen under lås og beskytter sidste aktive administrator. Samtidige ændringer af samme bruger skal genindlæses. Medlemslisten kan ikke ændres direkte af klientbrugere. Deaktivering fjerner portaladgang men sletter ikke Supabase-kontoen.

Navne og invitationer bruger fortsat den separate serverklient efter en frisk administratorkontrol. Restore-testappen er uændret. Nulstillingsmail fra Setup er stadig næste trin; eksisterende Glemt adgangskode virker med de nye roller.

## Verifikation

Python-test bruger simulerede API-svar. SQL skal installeres og kontrolleres i Supabase; der er ikke kørt ændringer på produktionsdatabasen fra udviklingsmiljøet. Sæsonafslutning er stadig ikke live-testet.
