# Supabase som eneste login

Hovedappen bruger nu altid Supabase-login. AUTH_MODE="dual", "legacy" og gamle legacy-sessioner kan ikke åbne legacy eller serviceklienten i hovedappen. Sæt hovedappens AUTH_MODE="supabase" for at gøre Secrets tydelige. De eksisterende Supabase-loginindstillinger bevares.

Hardkodede loginoplysninger og cookie-nøgler er fjernet fra auth.py. Git-historikken indeholder fortsat den tidligere kode; gamle adgangskoder skal ikke genbruges. Ingen databasepolitikker ændres.

## Restore-testappen

Før eller efter push skal restore-testappens egne Secrets have et separat login. Uden dette afviser den login. Hovedappen bruger ikke disse indstillinger. Behold APP_ENV="restore_test", AUTH_MODE="legacy", den eksisterende RESTORE_TEST_COOKIE_KEY og testprojektets URL/nøgle.

Tilføj følgende i restore-appens Secrets (listen skal stå før TOML-sektionerne). Erstat pladsholderen med en ny, unik adgangskode direkte i Cloud, aldrig i Git eller chat:

```toml
RESTORE_ADMIN_USERNAMES = ["restoreadmin"]

[RESTORE_CREDENTIALS.usernames.restoreadmin]
name = "Restore administrator"
password = "INDSAET_EN_NY_UNIK_ADGANGSKODE_HER"
```

Det nye cookienavn kræver nyt login i restore-appen. Test hovedappens login og nulstilling efter push. Behold SUPABASE_KEY: den bruges stadig på serveren til brugeradministration/backup, men ikke til almindelige Supabase-brugeres databaseadgang.
