# Hammerknuden – status og sikkerhed

**Dato: 22. oktober 2026**  
**Grundlag:** Den lokale kode og SQL-filer samt Finns tilbagemeldinger fra test i den kørende app. Cloud-konfiguration, aktive databasepolitikker og backupindhold er ikke uafhængigt genkontrolleret i denne rapport. Rapporten er en driftsstatus, ikke en penetrationstest eller certificering.

## Samlet status

Overgangen til Supabase-login og central brugeradministration er gennemført og afprøvet. De daglige funktioner har fungeret i de gennemførte test. Der er ingen kendte, åbne loginfejl i dialogen. Den resterende oprydning kan planlægges separat.

Hovedappen bruger kun Supabase-login. Det tidligere legacy-login kan ikke genaktiveres i hovedappen via de gamle loginindstillinger. Restore-testappen har fortsat et separat login fra sine egne Secrets.

## Funktioner og test

| Område | Status |
| --- | --- |
| Login, logout og glemt adgangskode | Bekræftet i drift |
| Invitation og valg af første adgangskode | Bekræftet i drift; invitation giver ikke automatisk portaladgang |
| Brugeroversigt og navneændring | Bekræftet i drift |
| Aktivering, deaktivering og genaktivering | Bekræftet i drift; rerun/genindlæsning viser ny adgang |
| Rolleskift mellem bruger og administrator | Bekræftet i drift |
| Beskyttelse af sidste aktive administrator | SQL-kontrol bestået ifølge Finn; midlertidige ændringer rullet tilbage |
| Nulstillingsmail fra Setup | Bekræftet i drift |
| Bookinger, annullering, bytning og optimering | Afprøvet med de relevante roller |
| Priser, events og morgenmadsoplysninger | Gemning afprøvet med Supabase-login |
| Statistik | Læseadgang afprøvet |
| Private gæsteregistreringer | Administratortilgang og afvisning/skjulning for almindelig bruger afprøvet |
| Backup fra Setup | Oprettelse/download afprøvet; fuld backup er tidligere oplyst gemt på Synology |
| Sæsonafslutning | Klargjort; endnu ikke afprøvet gennem Supabase-login |

Testene dækker de beskrevne forløb, ikke alle mulige fejlsituationer eller belastninger.

## Adgang og sikkerhed

**Roller styres i databasen.** `public.portal_members` indeholder rolle og aktiv status. De gamle bruger-ID-lister i Secrets styrer ikke længere produktionsadgangen. Profilnavn og andre brugerredigerbare profiloplysninger giver ingen rettigheder. Hvis rolleopslaget fejler, afvises adgangen.

**To roller.** Almindelige brugere kan arbejde med bookinger, kalender, morgenmad og statistik. De kan annullere med `cansl`, men ikke permanent slette bookinger. Administratorer har desuden adgang til Setup, Afstemning, gæsteregistreringer og permanent sletning.

**Kontrol både i app og database.** Almindelige databasekald bruger brugerens login-token. RLS-politikker og rollebeskyttede databasefunktioner håndhæver adgangen. Rolleændringer foretages med administratorens token. Databasen kontrollerer administratorrettigheden igen og beskytter den sidste aktive administrator mod deaktivering og nedgradering. Samtidige rolleændringer kontrolleres mod den tidligere tilstand.

**Private dokumenter.** Gæsteregistreringer ligger i en privat Storage-bucket. `storage_path` er en reference til filen; den giver ikke i sig selv adgang. Dokumentadgangen er begrænset til administratorer.

**Adgangskoder og servernøgler.** Hovedappens hardkodede legacy-loginoplysninger er fjernet fra den aktive kode. Supabase håndterer brugernes adgangskoder. Nulstillingslinks lader brugeren vælge en ny kode; administratoren får ikke adgang til den. Den privilegerede servernøgle bruges fortsat til bestemte administratorfunktioner og backup efter adgangskontrol. Den er derfor stadig en følsom driftshemmelighed.

**Deaktivering.** Nye sidehandlinger og databasekald afvises efter deaktivering. Allerede viste eller downloadede oplysninger kan ikke trækkes tilbage ved at deaktivere kontoen.

## Udestående og senere oprydning

1. Ryd op i forældede testfiler, kompatibilitetskode, gamle Secrets-navne og dokumentation efter kontrol af afhængigheder. Bevar restore-testmiljøet.
2. Kontrollér restore-testappens nye, separate login og dokumentér en prøvegendannelse. En backupfil med forventet størrelse beviser ikke alene, at gendannelse virker.
3. Afprøv sæsonafslutning på et passende testgrundlag inden næste reelle afslutning. Den ekstra samtidighedstest, hvor en booking låses mellem optimeringsvisning og gemning, er heller ikke bekræftet i drift.
4. Automatisk sletning af ældre gæsteregistreringer er fortsat en fremtidig opgave. Ingen opbevaringsperiode er teknisk indført som del af loginprojektet.

Tidligere hardkodede oplysninger kan stadig findes i Git-historikken og bør ikke genbruges. Det er ikke kontrolleret her, om de er genbrugt andre steder. MFA, samlet nøglehåndtering, alle Cloud-indstillinger og en fuld sikkerhedsrevision ligger uden for de udførte test. Rapporten fastslår heller ikke GDPR-overholdelse.

## Konklusion

Login og brugeradministration er færdige til den nu afprøvede drift. Rettighederne er samlet i Supabase, og de centrale brugerforløb og adgangsbegrænsninger er bekræftet. Næste arbejde er oprydning samt dokumenteret kontrol af restore og sæsonafslutning.
