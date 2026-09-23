# Første skrivetest med Supabase-login

## Kommentarændring gennem Booking-siden

Efter oprettelse i Skrivetest kan administratorer med ENABLE_BOOKING_WRITE_PROBE
vælge 2099 på Booking-siden. Siden viser kun Rediger booking for denne sæson.
Vælg booking 99999, indtast Ny testkommentar og klik Gem ændringer. Den benytter
portalens Supabase-klient med brugerens JWT, og genlæser kommentaren efter PATCH.
Klientens skriveblokering tillader kun comments, når forespørgslen indeholder
det præcise testnummer, sæson, navn, cansl og et enkelt række-ID. Alle andre
skrivehandlinger forbliver blokeret. Legacy viser ikke 2099. Timeline er uændret,
da den annullerede booking fortsat skal filtreres fra.
Dette tester en begrænset redigeringsfunktion, ikke hele bookingformularens
almindelige gemmeforløb. Der kræves ingen nye Secrets eller SQL-politikker.

Den oprindelige testapp bruger produktionsdatabasen. Derfor testes kun én
syntetisk, annulleret booking i sæson 2099 med nummer 99999, uden gæster,
kontaktoplysninger eller mails. Almindelige bookinger og sider er fortsat
i læsetilstand. Backup-testappen og legacy-klientens adgang ændres ikke.

1. Push testing/app.py, testing/write_probe.py, tests/test_booking_write_probe.py
   og evt. denne vejledning og testing/enable_booking_write_probe.sql.
2. Kør hele testing/enable_booking_write_probe.sql i Supabase SQL Editor som
   administrator. Det opretter kun regler og et indeks, ingen booking.
   Scriptet stopper ved eksisterende skrivepolitikker eller optaget testnummer.
   Eksisterende læsepolitikker til de to administratorer skal bevares.
3. Tilføj i TESTAPPENS Cloud Secrets:

```toml
ENABLE_BOOKING_WRITE_PROBE = true
```

4. Log ind med administratorens e-mail/adgangskode. Vælg Skrivetest.
5. Klik Opret annulleret testbooking. INSERT og efterfølgende SELECT skal bekræftes.
6. Klik Genindlæs testbooking, skriv en kommentar, og gem. PATCH og SELECT skal
   bekræftes. Genindlæs igen og kontrollér, at kommentaren er bevaret.
7. Gentag kommentarændringen med den anden administrator. Almindelige brugere
   skal ikke få menupunktet; SQL-politikkerne tillader heller ikke deres skrivninger.

Resultatet beviser kun INSERT/UPDATE/SELECT på den afgrænsede booking gennem
den indloggede brugers JWT. Det beviser endnu ikke de normale bookingsiders
arbejdsforløb, andre tabeller, sletning eller upload. Supabase-politikkerne skal
testes live; enhedstests bruger mocks og ændrer ikke databasen.

Ved timeout: genindlæs før nyt forsøg, da en ændring kan være gemt trods timeout.
Testbookingen findes også i rå tabelvisninger og backups, men er markeret cansl
og ligger uden for de aktuelle sæsoner. Fjern den kontrolleret efter testen.
Secrets-flaget skjuler kun funktionen; databasepolitikkerne skal fjernes særskilt
for at tilbagekalde den midlertidige skriveadgang. Fjern ikke læsepolitikkerne.
