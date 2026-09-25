# Bookingmail med Supabase-login

Booking-siden viser nu mailknapperne også ved Supabase-login.
- Opret booking gemmer og genlæser booking uafhængigt af mail.
- Send booking mail bruger de eksisterende DK/UK/DE-skabeloner.
- send data fil sender den eksisterende Excel/data-mail; ved Supabase-login
  opretter knappen aldrig en databasebooking, heller ikke ved genafsendelse.
- Legacy beholder sin eksisterende oprettelse gennem send data fil.

Mailkodeord er kodeordet til den eksisterende bookingmailkonto, ikke brugerens
Supabase-adgangskode og ikke nødvendigvis noreply-kontoen til nulstilling.
Feltet er nu maskeret. SMTP-konfiguration og afsender er ikke ændret.
Ingen mail er sendt af agenten. Fejl vises uden SMTP-detaljer eller hemmeligheder.
Ved ukendt leveringsstatus skal modtagelsen kontrolleres før genafsendelse.

Deploy pages/1_Booking.py, tests/test_booking_mail_flow.py og denne vejledning.
Ingen SQL eller nye Secrets kræves. Test først uden Send mail direkte til gæst,
så bookingmailen kun går til den eksisterende administratormailadresse.
Opret booking separat hvis den skal gemmes. Kontrollér mail og datafil samt at
et nyt tryk på mailknappen ikke giver en ny bookingrække. Ryd testbooking som admin.

Lokalt: 21 tests for bookingmailflow, oprettelse og adgang bestod med mock-mail;
herunder gentagen data-mail uden INSERT, SMTP-fejl uden INSERT samt legacy-INSERT.
Live SMTP/modtagelse mangler brugerens test.
