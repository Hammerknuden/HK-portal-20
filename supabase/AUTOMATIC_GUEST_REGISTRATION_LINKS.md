# Automatisk dokumentparring for alle år

Aktivér pg_cron under Supabase Integrations / Cron. Kør derefter hele
`enable_automatic_guest_registration_links.sql` som postgres i SQL Editor.
Agenten har ikke kørt filen i databasen.

Jobbet hk-link-guest-registrations kører hvert femte minut uafhængigt af portalen.
Det læser Storage-metadata og udfylder kun tomme storage_path i historie_new.
Det ændrer ingen filer, bookingdata ud over stien eller adgangspolitikker.
Første kørsel sker straks og inkluderer eksisterende filer fra alle historikår.

Understøttede navne: 2025/2025-001.pdf, 2025/2025-1.pdf og tilsvarende for andre firecifrede år.
Årstal i mappe og filnavn skal være ens. Den faktiske sti gemmes uændret.
Flere filer med samme normaliserede bookingnummer eller flere historikrækker
for samme sæson/nummer springes over. Eksisterende koblinger overskrives ikke.
Filer uden historikrække bliver først koblet, når historikken senere indeholder
bookingen. Dette kobler ikke hk_dtb direkte. Alle firecifrede historikår (1000–9999) er omfattet.

Kontrol: Upload en korrekt navngivet PDF til en historikbooking med tom sti,
vent op til fem minutter og kontrollér opslag som administrator. Se jobbets
History under Cron for succes/fejl. Filer fjernet eller omdøbt efter kobling
repareres ikke automatisk af denne funktion.

Stop uden dataændringer:
SELECT cron.unschedule('hk-link-guest-registrations');

SQL er gennemgået lokalt, ikke live-testet. Cron-runhistorik vokser med tiden;
gennemgå opbevaring af joblogs som separat vedligeholdelse.
Automatisk sletning af PDF'er er ikke implementeret. Før dette besluttes,
aftales præcis periode og startdato (fx checkout), håndtering af storage_path
og kopier i backup. Selve filen skal senere slettes gennem Storage API.

## Løbende upload og sæsonafslutning

Upload filer gennem sæsonen under ÅÅÅÅ/ÅÅÅÅ-bookingnummer.pdf.
Jobbet kræver en entydig matchende række i historie_new. Når sæsonens
bookinger overføres til historikken, kobles filerne ved næste kørsel.
Der kræves ingen årlig SQL-ændring. Hvis en historikrække allerede findes
før sæsonafslutning, kan den kobles tidligere; sæsonstatus er ikke en betingelse.

Ved opgradering køres hele enable_automatic_guest_registration_links.sql igen
som postgres. Det erstatter funktionen og opdaterer samme navngivne job.
Eksisterende koblinger bevares. Ingen PDF-sletning aktiveres.
