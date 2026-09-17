# Vælg løsning → vis på timeline → gem eller fortryd

Implementeret lokalt 17. september 2026. Intet er pushet eller installeret i cloud som del af arbejdet.

## Brugerforløb

1. Kør niveau 2-analysen, og tryk **Vælg denne løsning** ved det ønskede forslag.
2. Den valgte plans bookinger, datoer og fra-/til-værelser vises samlet.
3. Tryk **Vis på timeline**. Appen henter aktuelle bookinger, kontrollerer planen og bygger en kopi med **Før** og **Efter (forslag)**. Orange bookinger flyttes; grå nabobookinger bliver stående. Hele ophold bevares.
4. Tryk **Fortryd** for at kassere valget og forhåndsvisningen. Det skriver intet til databasen.
5. Tryk **Gem ændringer** for at gemme hele planen. Først her sendes en skriveforespørgsel. Ved bekræftet gemning ryddes forslagene, og siden genindlæses med den gemte timeline.

Mens en løsning er valgt, skal den gemmes eller fortrydes før en ny analyse. Skift af sæson kasserer et normalt, ugemt valg. Der er ikke implementeret fortrydelse af en allerede gemt flytning.

## Samlet gemning

`apply_optimizer_plan` kører i én PostgreSQL-transaktion. Funktionen låser bookingtabellen mod samtidige ændringer under kontrollen og lagringen. Den kontrollerer alle berørte ID'er, kildeværelser, datoer, sæson, `movable`, ankomstdag, annulleringer og den samlede slutplacering på berørte værelser, inklusive andre sæsoners faste bookinger. Kandidaten skal komme fra værelse 7, øvrige flyttede bookinger fra 1–5, og alle destinationer skal være 1–5.

Hvis en kontrol eller databaseopdatering fejler, rulles alle flytninger tilbage. Mekanismen bygger på [PostgreSQLs transaktionslåse](https://www.postgresql.org/docs/17/explicit-locking.html) og en [databasefunktion kaldt gennem Supabase](https://supabase.com/docs/guides/database/functions).

Et tilfældigt gemme-ID følger samme valgte løsning ved gentagne forsøg. Funktionen gemmer en kvittering, så et gentaget kald efter et mistet netværkssvar returnerer samme resultat uden at flytte igen. Hvis et gemmeresultat er ukendt, bevares forhåndsvisningen og ID'et. Fortryd deaktiveres indtil gemningen er afklaret, fordi den allerede kan være gennemført. Brugeren kan trykke Gem igen med samme plan.

## Installation før brug af Gem

Kør **`supabase/migrations/20260917_apply_optimizer_plan.sql`** én gang i Supabase SQL Editor på den database, portalen bruger. Filen:

- Opretter gemmefunktionen og kvitteringstabellen `optimizer_plan_receipts`.
- Flytter ingen eksisterende bookinger ved installation.
- Tillader kun kald fra `service_role`, samme serverbaserede adgang som projektets eksisterende sæsonafslutningsfunktion. `anon` og `authenticated` får ikke skriveadgang til denne RPC eller kvitteringstabellen.
- Beder PostgREST opdatere sit funktionsregister.

Portalens serverbaserede Supabase-klient skal bruge en nøgle med den nødvendige rolle. Login-kontrollen ændres ikke. Det eksisterende Supabase-testspor i læsetilstand får forhåndsvisning, men ingen aktiv Gem-knap.

Hvis funktionen endnu ikke er installeret, giver Gem en forklarende besked. Der findes ingen reservevej med enkeltvise opdateringer.

Deploy derefter de opdaterede Python-filer og genstart cloud-appen. Første praktiske prøve bør være den fiktive booking 300: vælg, se før/efter, fortryd; vælg derefter igen og gem først efter kontrol af forslaget.

## Verifikation

- 65 Python-tests består: eksisterende analyseregler samt valg, kopiering, forhåndsvisning, fortryd, gemning, ændret lås/sæson, netværksfejl, gentaget gemme-ID og læsetilstand.
- 23 PostgreSQL-tests består i lokal PGlite: fuld flytning, gentagelser, ændrede bookinger, lås/dato/sæson, ugyldige værelser, annulleringer, overlap, tilladelser og en fremprovokeret databasefejl midt i opdateringen. Fejltesten bekræfter, at hverken delvise flytninger eller en kvittering bliver gemt.
- Plotly-figuren er bygget med den lokale Plotly-installation og kontrolleret for før-/efter-visning og fire dataserier. Der er ikke kørt en visuel browsertest eller udført en lagring mod en rigtig Supabase-database.
- PGlite-testene kører i én isoleret forbindelse; de simulerer ikke flere samtidige serverforbindelser. Beskyttelsen mod samtidige ændringer er SQL-tabellåsen, ikke en Python-kontrol alene.

Python-tests: `python -m unittest discover -s tests -p test_optimizer_preview.py -v` sammen med de eksisterende optimizer-tests.

SQL-tests: `node tests/optimizer_save.mjs tmp/statistics-test/package/dist/index.js` (lokalt PGlite-testbibliotek).
