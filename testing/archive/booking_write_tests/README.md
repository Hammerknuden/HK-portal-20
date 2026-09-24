# Arkiv: afsluttede skrivetests

Her ligger SQL-opsætning og vejledninger fra testbooking 2099/99999,
2026/300 og 2026/301. Filerne er bevaret som dokumentation; de skal ikke
køres igen ved overgangen til almindelig drift.

Aktive Python-moduler og automatiske tests er ikke flyttet, fordi testappen
stadig importerer dem. Fuld Supabase-skriveadgang er endnu ikke implementeret.

## Afslut testadgangen

Sæt disse eksisterende topniveauværdier til false i testappens Cloud Secrets:

```toml
ENABLE_BOOKING_WRITE_PROBE = false
ENABLE_BOOKING_300_TEST = false
ENABLE_BOOKING_301_TEST = false
```

Kør derefter `testing/cleanup_booking_write_tests.sql` i det oprindelige
Supabase-projekt. Det fjerner kun de navngivne testpolitikker og testindekser.
Filen sletter ikke bookingdata og bevarer læse- og dokumentpolitikker.
Dens sidste SELECT viser eventuelle resterende testbookinger, herunder 2099/99999.

Supabase-testappen går tilbage til læseadgang, indtil den almindelige
skriveadgang er implementeret. Legacy er fortsat til rådighed.
Flytning af filer lokalt ændrer ikke Secrets eller Supabase automatisk.
