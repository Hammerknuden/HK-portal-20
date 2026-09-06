# Separat logintest

Denne selvstændige app tester e-mail/adgangskode og en serverstyret liste over
testadministratorer. Den importerer ikke produktionsappens auth.py eller pages/.
Den kan teste læseadgang til public-tabeller med brugerens session via knappen
Test læseadgang. Højst én række hentes pr. tabel, og kun status vises, aldrig
gæsteoplysninger. Tomme svar kan skyldes enten tomme tabeller eller RLS-filtrering.
Testen beviser ikke skriveadgang eller adgang til alle rækker. Den ændrer ikke
bookingtabeller, adgangspolitikker eller Storage. Auth-login og logout
opretter og afslutter dog sessioner i det valgte Supabase-projekt.

## Streamlit Cloud

1. Få testing/-filerne lagt på GitHub i den branch, testappen skal bruge.
2. Opret en NY Streamlit-app med samme repository og den relevante branch.
3. Vælg `testing/app.py` som entrypoint og Python 3.12.
4. Kopiér `testing/secrets.example.toml` til den nye apps Secrets og udfyld den.
   Brug projektets publishable-nøgle, aldrig produktionens sb_secret_-nøgle.
5. Find testbrugerens User UID i Authentication > Users og indsæt det i listen.
   UID er projektbundet: et nyt Supabase-projekt kræver en bruger oprettet dér.
6. Start testappen på dens egen adresse. Produktionsappens Secrets ændres ikke.

Et separat Supabase-testprojekt anbefales før tests med databaseændringer og
dokumenter. Det eksisterende projekt kan bruges til denne afgrænsede logintest.
Der kopieres ikke automatisk produktionsdata eller adgangspolitikker.

## Kontrol før næste fase

- Forkert adgangskode afvises.
- Korrekt login med det konfigurerede UID viser testadministrator.
- En anden gyldig bruger uden for listen afvises.
- Log ud fjerner adgangen; en ny browser-session kræver nyt login.
- Udløbet/ugyldig session afvises. Denne første version kræver nyt login ved udløb.
- Produktionsappen bruger stadig sit eksisterende login.

Listen tildeler kun administratoradgang i testappen, ikke en database- eller
Supabase-projektrolle. Fælles AUTH_MODE-omskifter i portalen, RLS, dokumentadgang
og test af alle portalsider er næste fase. Produktionskoden er ikke omlagt endnu.

Lokalt: installer testing/requirements.txt og kør
`streamlit run testing/app.py --server.port 8502` fra repository-roden.
Lokale test-Secrets placeres i `.streamlit/secrets.toml` (ignoreret af Git).
