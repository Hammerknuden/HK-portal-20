# Sæsonbackup fra Setup

## Før første brug på Streamlit Cloud

Backupfunktionen er kun til administratorer i produktionsappen. Den lukker
ikke sæsonen og ændrer ikke databasen. Den kræver en direkte PostgreSQL-forbindelse
ud over appens eksisterende API-forbindelse.

1. Deploy `packages.txt` sammen med koden. Streamlit installerer PostgreSQL-
   værktøjerne. Klientversionen skal være mindst serverens hovedversion; ved
   versionsfejl skal hostingmiljøet have en nyere PostgreSQL-klient.
2. Tilføj nedenstående værdier i appens private Streamlit Secrets. Behold
   den eksisterende `SUPABASE_URL`. Disse hemmeligheder må aldrig gemmes i Git.

```toml
SUPABASE_BACKUP_DB_URL = "postgresql://postgres.PROJEKTREF:URL_ENCODET_PASSWORD@SERVER.pooler.supabase.com:5432/postgres"
SUPABASE_BACKUP_KEY = "SERVER_SECRET_ELLER_SERVICE_ROLE_KEY"
```

Hent den rigtige Session pooler-forbindelse i Supabase → Connect. Brug
databaseadgangskoden og URL-kod specialtegn i den. Brug ikke Transaction pooler
(port 6543). Nøglen skal tilhøre samme projekt som SUPABASE_URL og give fuld
Storage-adgang; en anon/publishable-nøgle accepteres ikke. Funktionen anvender
en særskilt serverklient, så RLS ikke filtrerer backup til brugerens egne filer.

3. Åbn Setup → Backup ved sæsonafslutning. Manglende opsætning vises her.
4. Lav en første backup og prøvegendannelse i et separat projekt før sæsonslut.
   Det er ikke udført automatisk som del af installationen.

## Brug ved sæsonafslutning

- Hold pause i alle ændringer, også uploads og eksterne integrationer.
- Vælg sæson og "Før sæsonafslutning", opret og download ZIP-filen.
- Gem den i `C:\Users\finnj\SynologyDrive\Supabase backup`.
- Afslut sæsonen med den eksisterende knap i Setup.
- Opret en ny backup mærket "Efter sæsonafslutning", og gem også den.
- Kontrollér begge filer på NAS’en via File Station. Appen kan ikke kontrollere
  Synology-synkronisering fra Streamlit Cloud.

Sæsonen bruges kun til filnavnet. Hele databasen med alle sæsoner eksporteres.
ZIP-filen er ikke krypteret og indeholder gæste- og eventuelle Auth-data.
Opbevar den med begrænset adgang. Tovejssynkronisering kan også overføre sletning.

Cloud-processen skal have lov at køre færdig; luk ikke siden under oprettelsen.
En genstart af appserveren afbryder jobbet. Download straks den færdige fil.
Midlertidige serverfiler fjernes efter oprettelsen; ZIP ligger kun i den aktuelle
Streamlit-session. Knappen "Fjern download" frigiver sessionens kopi.
Samlet backup er begrænset til 150 MB før ZIP-komprimering (SQL-dumpet er allerede
komprimeret). Større projekter kræver et separat backupjob. Enkeltfiler hentes i
hukommelsen; funktionen er beregnet til portalens beskedne dokumentmængde.

## Indhold og kontrol

- `database.dump`: PostgreSQL custom archive med databaseindhold og struktur,
  herunder Auth/Storage-tabeller, funktioner, triggers og adgangspolitikker,
  som backupbrugeren har adgang til. pg_dump fejler ved manglende læseadgang.
- `roles.sql`: roller uden rolle-adgangskoder.
- `storage/*.bin`: samtlige filer fra almindelige Storage-buckets, med oprindelige
  bucketnavne, filstier, metadata og bucketopsætning i `manifest.json`.
- `manifest.json`: projekt, tidspunkt, før/efter-markering, størrelser og SHA-256.
- Denne vejledning.

Databasekopien er et konsistent pg_dump-snapshot. Roller og Storage hentes
separat; der er ingen fælles transaktion på tværs af tjenesterne. Storage-listen
kontrolleres igen efter download, og ændringer afviser backuppen. Hold derfor
hele systemet i ro under backup. Ikke-standard buckets afvises.

Før download kontrolleres pg_restore-indholdslisten, ZIP-integritet og alle
filkontrolsummer. Det beviser filintegritet, ikke at gendannelse er afprøvet.
Ved enhver fejl frigives ingen ny download, og tidligere session-download fjernes.

## Gendannelse — udføres først i et separat projekt

Dette er en database- og dokumentbackup, ikke en automatisk kloning af et helt
Supabase-projekt. Behold også appens Git-repository. Dashboardindstillinger,
SMTP, API-nøgler, OAuth, Edge Functions, deres secrets, evt. krypteringsnøgler
og eksterne tjenester skal genetableres særskilt. Rolle-adgangskoder skal sættes
på ny. Vault/kolonnekryptering kræver særskilt nøglehåndtering inden gendannelse.

1. Pak ZIP ud på en sikker computer. Kontrollér filernes SHA-256 mod manifestet.
2. Opret et separat Supabase-projekt med kompatibel PostgreSQL-version og de
   nødvendige extensions. Behold produktionsprojektet urørt.
3. Brug `pg_restore --list database.dump` til at gennemgå indholdet. Dumpet
   indeholder også Supabase-styrede schemas, som allerede findes i et nyt projekt.
   Gendan ikke blindt hele dumpet med `--clean`. En tekniker skal udvælge
   applikationsstruktur/data og håndtere eksisterende Auth/Storage-objekter,
   roller og ejerskab efter Supabases gendannelsesvejledning. `roles.sql` skal
   tilsvarende gennemgås for roller, som allerede eksisterer. Brug stop-ved-fejl.
4. Genskab bucketindstillingerne fra manifestet. Upload hver .bin-fil via
   Storage API til dens oprindelige `bucket` og `path`, og brug oprindelig
   MIME-type fra metadata. Database-metadata alene genskaber ikke dokumenterne.
5. Genetablér relevante projektindstillinger, Realtime og øvrige integrationer.
6. Sammenlign rækkeantal og vigtige booking-/statistiktotaler. Test login,
   priser, historik, adgangspolitikker og download af gæstedokumenter med appen.
   Notér dato og resultat af prøvegendannelsen uden for backupfilen.

Der er med vilje ingen gendan-knap i driftsappen.

Referencer:
- https://supabase.com/docs/guides/platform/backups
- https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore
- https://www.postgresql.org/docs/current/app-pgdump.html
