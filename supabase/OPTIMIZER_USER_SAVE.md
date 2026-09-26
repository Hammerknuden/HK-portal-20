# Supabase: gem optimering

Kør enable_optimizer_user_save.sql som postgres i det oprindelige projekt.
Den installerede apply_optimizer_plan_authenticated er en separat kopi af den
atomiske legacy-algoritme med eksplicit auth.uid-kontrol for de tre portalbrugere.
SECURITY DEFINER er nødvendig for den beskyttede kvitteringstabel. Ingen almindelig
bruger får direkte adgang til kvitteringer. Funktionen bruger fast search_path
(pg_catalog, pg_temp), fuldt kvalificerede persistente tabeller og statisk SQL.
Legacy-funktionen ændres ikke. Brugerlister i Secrets og SQL skal holdes ens.

Bevarede kontroller: fremtidig indcheckning, movable=true, uændrede kildeværelser,
datoer og sæson, ingen annullerede ophold, kandidat fra rum 7 til 1–5, ingen overlap.
Tabel-lås beskytter kontrol og gemning; alt rulles tilbage ved fejl.
Gemmekvittering med request-ID giver samme resultat ved genforsøg.

Deploy portal_access.py, modules/optimizer_preview.py, modules/optimizer_workflow.py
og pages/6_timeline.py samlet, med de ændrede tests. Reboot. Ingen nye Secrets.
Vælg forslag -> Vis på timeline -> kontrollér -> Gem ændringer.
Forslag og forhåndsvisning flytter intet. Gem flytter alle planens bookinger samlet.

Oktobertest (2026): 313 fra rum 3 til 1 (21.–23. oktober), 318 fra 7 til 3
(19.–22. oktober). Bekræft genindlæst placering/datoer og øvrige uændrede bookinger.
Test begge roller med et passende gendannet scenario. Brug ikke SQL Editor som
bevis for almindelig brugers rettigheder. Automatisk test har ikke kørt live SQL.

Tilbagefald: fjern authenticated EXECUTE på den nye funktion. Legacy bevares:
REVOKE EXECUTE ON FUNCTION public.apply_optimizer_plan_authenticated(uuid,integer,bigint,jsonb) FROM authenticated;
