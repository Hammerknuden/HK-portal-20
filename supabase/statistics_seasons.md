# Sæsonstatistik

Kør `supabase/migrations/20260910_statistics_season_archive.sql` i det eksisterende
Supabase-projekt efter de tidligere migrationer. Filen installerer fælles
beregninger, opdaterer `close_booking_season` og gemmer de kendte omsætningstal for
maj–september 2024/2025. Den afslutter ingen sæson og overskriver ingen gemte tal.

Push derefter applikationsændringerne. `Vis sæson` styrer sæsonens opgørelser;
omsætning og booking pace sammenligner fortsat flere år. Den tidligste åbne
sæson er standardvalget. Manglende historiske opgørelser vises som manglende,
aldrig som nul eller som genberegnede aktuelle tal.

I Setup afsluttes 2026 med **Gem statistik og afslut 2026**. Det gemmer otte
statistikopgørelser fra `hk_dtb` og skifter sæsonstatus. Den eksisterende
`historie_new` for 2026 ændres ikke. Fra 2027 gemmer samme funktion også
bookinghistorikken. Originalerne forbliver i `hk_dtb`. Hele afslutningen er én
transaktion; ugyldige kildedata eller overførselsfejl ruller ændringerne tilbage.
Gentagne klik ændrer ikke en fuldstændig, afsluttet statistikhistorik.

Beregningsdefinitioner:
- Sæson vælges fra `season`; annullering på en linje fjerner hele bookingen i den sæson.
- Værelsesnætter og bookinglængde følger værelseslinjerne som på den hidtidige side.
- Landefordelingen bruger gæsteantal og gæstenætter. Manglende landekode advares
  om og udelades kun her, ikke fra omsætning eller andre opgørelser.
- Bruttoomsætning bruger `pris` og udcheckningsmåned, alle 12 måneder.
- Morgenmad fordeles på hver overnatningsdato med sæsonens gemte morgenmadspris,
  rabat på webbookinger og 25 % moms. Både 0,10, 10 og 10% tolkes som 10 % rabat.
- Daglige indcheckninger tælles pr. bookingnummer og dato, så periodevalget og PDF
  stadig virker historisk. Gennemsnitlig bookinglængde gemmes som sum og antal.
- 2024/2025 indeholder kun de kendte omsætningsmåneder; øvrige tal er ukendte.

Test:
- `python -m unittest discover -s tests -p test_season_statistics.py`
- `python -m unittest discover -s tests -p test_booking_pace.py`
- `node tests/statistics_archive.mjs /sti/til/pglite/dist/index.js`
  (lokal PostgreSQL-testmotor; kræver PGlite, ingen Supabase-forbindelse).
