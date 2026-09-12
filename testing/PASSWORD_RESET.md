# Opsætning efter deployment

Kun testappen har det nye nulstillingsforløb. Legacy-login ændres ikke.
Ændring af adgangskode gælder brugerens Supabase-konto i samme projekt.

1. Push testing/app.py, testing/auth_client.py, testing/password_recovery.py,
   testing/password_reset_email.html, denne vejledning og tests/test_password_recovery.py.
2. Tilføj i testappens Cloud Secrets (bevar resten):

```toml
PASSWORD_RESET_URL = "https://9jxcncqxdwbyxextrknuzr.streamlit.app/"
```

3. Supabase Authentication > URL Configuration: brug ovenstående adresse som
   Site URL og tilføj den som Redirect URL. Bevar andre nødvendige redirects.
   Site URL er fælles for projektets Auth-mails; legacy-authenticator bruger den ikke.
4. Authentication > Emails > Templates > Reset Password: erstat mailens HTML
   med testing/password_reset_email.html. Emne: Ny adgangskode til Hammerknuden.
   Linket går direkte til testappen med TokenHash. Standard-ConfirmationURL
   leverer tokens i et URL-fragment, som Streamlit-serveren ikke kan læse.
5. Genstart testappen og bestil en NY mail via Glemt adgangskode eller dashboardet.
   Gamle mails indeholder stadig det gamle link.

Appen fjerner token fra adresselinjen og verificerer først efter klik på Fortsæt.
Recovery-token giver ingen portalnavigation. Kontoen skal stadig være på en
godkendt UID-liste. Nyt password kræver mindst 12 tegn; Supabases yderligere
passwordkrav gælder stadig. UID og adgangsrettigheder ændres ikke.

Test levering, link, to ens nye koder, nyt login og afvisning af den gamle kode.
Kontrollér også mismatch/kort kode og at et brugt eller udløbet link afvises.
En session kan kræve et nyt link efter genindlæsning eller afbrudt forbindelse.
De automatiske tests bruger mocks, sender ingen mail og ændrer ingen adgangskode.
