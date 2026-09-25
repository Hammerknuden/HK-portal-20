# Bookingrettigheder ved overgang til Supabase-login

Kør hele enable_booking_user_permissions.sql i det oprindelige Supabase-projekt.
Filen er til manuel kørsel; agenten har ikke kørt den mod databasen.

UID'er er eksplicitte: Finn og Naja er administratorer, og den eksisterende
almindelige testbruger er bookingbruger. Secrets og SQL synkroniseres ikke automatisk.
Nye brugere skal tilføjes begge steder, indtil en fælles rolleløsning etableres.

SQL'en gælder kun public.hk_dtb:
- Alle tre kan SELECT, INSERT og UPDATE, inklusive annullering med web='cansl'.
- Kun administratorerne kan DELETE.
- Restriktive skrivepolitikker begrænser eksisterende permissive politikker.
- Ingen bookingdata ændres. Gamle navngivne testpolitikker fjernes.
- Legacy med servernøgle fortsætter med sin eksisterende adgang.

Kørsel afsluttes med syv policy-rækker som kontrolresultat. Scriptet er transaktionelt
og kan genkøres. Det stopper, hvis RLS ikke er aktiveret, eller en af brugerne mangler.

Dette er database-trinnet for bookinger, ikke den færdige overgang:
Appens generelle skriveblokering, mail/oprettelse og admin-only sletteknapper
skal stadig tilpasses. Øvrige tabeller og Storage-politikker ændres ikke her.
RPC'er (især SECURITY DEFINER-funktioner til optimering/sæsonafslutning) skal
gennemgås særskilt; tabel-RLS alene dokumenterer ikke deres rettigheder.
Setup og Booking.com-afstemning skal fortsat have appens administratorcheck.

Efter appændringen testes oprettelse/redigering/annullering for begge roller,
afvisning af DELETE for almindelig bruger og tilladt DELETE for administrator.
Test databaseafvisning med bruger-JWT, ikke som owner i SQL Editor.
SQL'en er gennemgået lokalt; live RLS-verifikation mangler.

## Apptrin: almindelig bookingadgang

Booking og Timeline bruger nu allow_booking_writes=True med brugerens JWT.
Kun /rest/v1/hk_dtb åbnes for INSERT/UPDATE og administrator-DELETE.
Andre skriveendpoints og RPC'er er fortsat blokeret. De installerede RLS-politikker
håndhæver databaseadgangen separat. Ingen nye Secrets er nødvendige.
Gamle ENABLE_BOOKING-testindstillinger skal fortsat være false.

Oprettelse fra Booking har knappen Opret booking, uafhængigt af mailafsendelse.
Det eksisterende formularformat anvendes, inklusive room_number=7; værelse kan
ændres bagefter. Der foretages duplicate-check og genlæsning af den nye række.
Duplicate-check er ikke en atomisk reservation af bookingnummer: undgå samtidig
oprettelse med samme nummer, da flerværelsesbookinger legitimt deler nummer.

Slet-knapper på Booking og Timeline kræver administrator, også i legacy.
Almindelige brugere annullerer med web=cansl. Øvrigt legacy-flow bevares.
Dette er endnu ikke fuld portaldrift: mail, dokumentupload, Setup-skrivninger,
optimering og værelsesbytning kræver særskilt klargøring og test.

Deploy pages/1_Booking.py, pages/6_timeline.py, portal_access.py,
modules/booking_write.py og testing/app.py samlet og reboot Supabase-appen.
Test med begge roller: opret en tydeligt markeret booking, rediger, annuller.
Kontrollér afvist permanent sletning for almindelig bruger og sletning som admin.
RLS er endnu ikke live-verificeret af agenten. Behold legacy under overgangen.
