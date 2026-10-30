# Automatisk sletning af gæsteregistreringer

## Regel og afgrænsning

PDF-filer i den private bucket `guest-registrations` slettes ved indcheck + to
kalenderår, regnet ved midnat i Europe/Copenhagen. Jobbet kører dagligt
kl. 02:17 UTC (03:17 dansk vintertid / 04:17 sommertid) og
behandler forfaldne filer ved første kørsel efter fristen. Fristen regnes aldrig
fra upload, sæsonafslutning eller kundens senere ophold. Den 29. februar bliver
til den 28. februar i et år uden skuddag.

`historie_new.delete_at` er dokumentets planlagte slettefrist.
`registration_deleted_at` er tidspunktet for bekræftet fjernelse eller konstateret
fravær af dokumentet. `storage_path` tømmes først derefter. Selve bookingrækken,
navne, kontaktoplysninger og statistik ændres ikke. Femårs-anonymisering er ikke
en del af denne installation.

Der slettes gennem Storage API; SQL-sletning af `storage.objects` er ikke nok.
Jobbet kontrollerer bagefter, at metadata er væk. Ved API-fejl bevares referencen,
og jobbet fejler, så næste kørsel kan forsøge igen. Hvis filen blev fjernet før
en databasefejl, afslutter næste kørsel oprydningen idempotent.

Bookingrækker med tom dokumentreference kræver ingen PDF-upload. Jobbet finder
også entydige filer navngivet `ÅÅÅÅ/ÅÅÅÅ-bookingnummer.pdf` (med eller uden
foranstillede nuller), selv hvis dokumentkoblingsjobbet endnu ikke har kørt.
En senere upload af en allerede udløbet, genkendelig fil bliver også slettet.
Ukendte filer uden matchende historikrække rapporteres som `unmatched_files`;
de slettes ikke ud fra uploadtid eller et gættet indcheck. Historik med manglende
indcheck rapporteres som `missing_checkin`. Begge tal skal følges op manuelt.
Flere matchende PDF'er, delte referencer eller uoverensstemmende bookingnumre
stopper jobbet før sletning.

## Installation og aktivering

Koden er forberedt lokalt. Installation og første produktionskørsel er ikke
udført som del af kodeændringen.

1. Kør `migrations/20261029_guest_registration_retention.sql` som postgres i
   produktionsprojektets SQL Editor. Den sætter frister på eksisterende rækker
   og installerer en trigger for fremtidige ændringer. Den sletter ingen PDF'er.
2. Få workflow og Python-kode ind på GitHub-repositoryets default branch.
3. Opret GitHub Environment `guest-registration-retention` og tilføj secrets:
   - `SUPABASE_URL`: produktionsprojektets HTTPS-adresse.
   - `SUPABASE_RETENTION_KEY`: samme projekts server secret/service_role-nøgle.
   - `SUPABASE_RETENTION_DB_URL`: samme projekts Direct eller Session pooler
     PostgreSQL-adresse med postgres-bruger og URL-kodet adgangskode. Port 5432.
     Format som beskrevet i `BACKUP.md`. Transaktionspooler 6543 accepteres ikke.
   Nøgler må ikke lægges i kode, workflowtekst eller output. Environment kan
   holdes uden secrets indtil prøveinstallation og test er klar.
4. Start workflow **Guest registration retention** manuelt med `execute=false`.
   Kontrollér de anonymiserede tællere. Gennemgå alle manglende datoer, ukendte
   filer og tvetydige koblinger inden første rigtig sletning. En prøve kan også
   køres lokalt med miljøvariabler og
   `python scripts/purge_guest_registrations.py` efter installation af
   `scripts/retention-requirements.txt`.
5. Start manuelt med `execute=true` for den første rigtige kørsel. Det fjerner
   også allerede udløbne dokumenter permanent. Kontrollér resultatet i Storage
   og på historikrækkerne. Sæt derefter repository Actions-variablen
   `GUEST_RETENTION_ENABLED` til `true` for at aktivere daglig sletning.
   Uden denne variabel udføres kun manuelt startede kørsler.

Workflowet får ingen skriveadgang til GitHub. Servernøglen har privilegeret
adgang til Supabase og skal behandles som en administrativ hemmelighed.
Vedligeholdelse sker uafhængigt af Streamlit og kræver ikke en åben portal.
GitHub-planlagte kørsler kan blive forsinket; kontrollér Actions og fejlmeddelelser.
I offentlige repositories kan tidsplaner deaktiveres efter længere inaktivitet.
Jobbet er en periodisk håndhævelse, ikke en garanti for sletning på præcis sekund.

## Kontrol og stop

Kontrollér workflowets exitstatus og tællere. Ingen gæstenavne, filstier eller
nøgler logges. En SQL-kontrol af resterende udløbne referencer:

```sql
select count(*) as udloebne_referencer
from public.historie_new
where delete_at <= now() and nullif(btrim(storage_path), '') is not null;
```

Deaktivér workflowet i GitHub Actions for at stoppe fremtidig sletning.
Allerede slettede filer kan ikke genskabes af jobbet.

Slettejobbet låser historiktabellen mod skrivning under hver batch på højst 100
rækker, så indcheck og referencer ikke ændres under sletning. Uploads skal bruge
korrekt, entydigt bookingnavn; foretag ikke samtidig manuel ombytning af filer.
Backups, downloads og papiroriginaler slettes ikke af dette job. De skal følge
en særskilt opbevarings- og destruktionsprocedure; en restore skal efterfølges af
ny fristkontrol, før gamle dokumenter gøres tilgængelige i portalen.

Kilder: https://supabase.com/docs/guides/storage/management/delete-objects
og https://supabase.com/docs/guides/storage/schema/design
