# Secure login i normal drift

## Rækkefølge

1. Commit og push alle kodeændringer fra denne loginflytning, inklusive de nye moduler. Behold AUTH_MODE="dual". De gamle Secrets-navne virker fortsat. Vent på at hovedappen er opdateret.
2. I hovedappens Cloud Secrets sættes PASSWORD_RESET_URL til:
   "https://hammerknuden-hk-portal-20-app-kcx0iq.streamlit.app/"
3. I Supabase Authentication → URL Configuration: sæt Site URL til samme adresse, og tilføj den under Redirect URLs. Bevar testappens eksisterende adresse under overgangen.
4. I Authentication → Emails → Reset password: erstat mailens HTML med HELE indholdet af supabase/password_reset_email.html. Skabelonen bruger TokenHash og går direkte til hovedappen; standard ConfirmationURL kan ikke erstatte den.
5. Åbn hovedappen, vælg Secure login → Glemt adgangskode, bestil en NY mail, åbn linket, vælg Fortsæt med nulstilling, gem ny kode og log ind. Kontrollér admin/almindelig bruger samt legacy-reserven. Gamle mails kan fortsat pege på testappen.
6. Behold auth-testappen, indtil dette forløb er bekræftet. Restore-testappen bevares separat.

## Navne i hovedappens Secrets

Omdøb hver eksisterende nøgle i stedet for at kopiere hele Secrets eller ændre værdierne:

| Gammelt navn | Nyt navn |
| --- | --- |
| SUPABASE_TEST_URL | SUPABASE_AUTH_URL |
| SUPABASE_TEST_PUBLISHABLE_KEY | SUPABASE_PUBLISHABLE_KEY |
| TEST_ADMIN_USER_IDS | ADMIN_USER_IDS |
| TEST_USER_IDS | USER_IDS |

De nye navne har forrang, hvis begge findes, også ved en tom liste. Den privilegerede SUPABASE_KEY og SUPABASE_URL til legacy/backup skal ikke omdøbes eller bruges som login-nøgle. APP_ENV="test" i hovedappen kan ændres til APP_ENV="production"; restore-appens APP_ENV må ikke ændres. De tre ENABLE_BOOKING_…-testflag kan fjernes fra hovedappen; de giver ikke længere adgang. Ændr ikke den separate testapps Secrets i denne omgang.

Ingen SQL eller nye brugere er nødvendige. UID'er og databasepolitikker bevares. Tilføjelse af nye brugere kræver fortsat både appliste og de relevante databasepolitikker.

## Kode

Fælles login ligger nu i modules/auth_client.py, modules/auth_settings.py, modules/portal_login.py og modules/password_recovery.py. testing/auth_client.py og testing/password_recovery.py er kun kompatibilitetsimporter til den gamle testapp. Eksisterende sessioner understøttes, mens nye sessioner bruger auth_access_token. Nulstillingssessioner giver aldrig automatisk adgang til portalen.
