# Invitation – første trin

Administratorer kan sende invitationer fra Setup. Modtageren opretter sin adgangskode i hovedappen. Kontoen får ingen rolle eller portaladgang af dette trin. De nuværende Secrets-lister og SQL-politikker ændres ikke.

## Aktivering

1. Push kodeændringerne, inklusive det nye modul modules/user_invitation.py.
2. I Supabase → Authentication → Emails → Invite user erstattes mailens HTML med hele indholdet af supabase/invite_user_email.html. Gem. Skift ikke Reset password-skabelonen.
3. PASSWORD_RESET_URL i hovedappens Secrets og Supabase Redirect URLs skal fortsat indeholde https://hammerknuden-hk-portal-20-app-kcx0iq.streamlit.app/.
4. Log ind som administrator. I Setup indtastes modtagerens navn og en ny e-mailadresse; tryk Send invitation. Dette sender en rigtig mail og opretter en konto i Supabase. Ingen mails sendes ved blot at åbne Setup.
5. Åbn mailen, tryk Accepter invitation, vælg en adgangskode, og gem den. Der skal komme en besked om, at portaladgangen endnu afventer administratoren. Forsøg på almindeligt login skal fortsat afvises for den nye konto.

## Afgrænsning

Invitationer uden portaladgang vises separat i Setup. Listen omfatter inviterede Supabase-konti, der ikke er i portalens adgangslister; den er ikke en kvittering for maillevering eller for valgt adgangskode. Navnet er en profiloplysning, aldrig en adgangsregel.

Eksisterende e-mailadresser afvises før afsendelse. Der foretages ikke automatisk genafsendelse ved fejl eller genindlæsning. Hvis afsendelsen fejler, kan kontoen alligevel være oprettet; kontrollér invitationerne og Supabase før næste forsøg. En funktion til geninvitation er ikke med i dette trin.

En udløbet eller allerede brugt invitation skal håndteres af administratoren. Den eksisterende nulstillingsfunktion gælder fortsat kun brugere, som allerede har portaladgang.

Næste trin er central rolle- og adgangsstyring. Hverken metadata fra invitationen eller en gennemført adgangskodeoprettelse giver automatisk administratorrettigheder eller databaseadgang.
