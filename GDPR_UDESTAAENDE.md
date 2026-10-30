# GDPR – udestående emner til den nye sæson

Noten samler beslutninger og opfølgning. Den opretter ingen påmindelse og
aktiverer ingen yderligere sletning.

## 1. Sæsonvis oprydning i hk_dtb

Forslag til senere beslutning: Bevar indeværende sæson, de to foregående
sæsoner samt fremtidige sæsoner, så kalenderen kan ses bagud.

- Afklar, om hele gamle bookingrækker skal slettes, eller om kun personfelterne
  skal ryddes, så en kalender uden personoplysninger kan bevares længere.
- Sæsonvis oprydning er ikke en præcis toårsfrist fra hvert ophold. Afklar
  skæringsdato og hvordan aktiv sæson fastlægges; en fremtidig sæson må ikke
  udløse oprydning for tidligt.
- Kontrollér afsluttet sæson, overført bookinghistorik og gemte statistikker
  før oprydning. Ældre sæsoner har ikke nødvendigvis alle otte statistiktyper.
- Kontrollér kalender, booking pace, sæsonafslutning, tilknyttede tabeller og
  genkørsel af arkivering. Gamle personoplysninger må ikke kopieres tilbage
  til allerede ryddet historik.
- Lav læseprøve med berørte sæsoner og antal før aktivering.

Status: Forslag drøftet; ingen ny oprydning i hk_dtb er implementeret eller aktiveret.

## 2. Løbende scanning og opslag i arbejdsårets gæsteregistreringer

Det nuværende dokumentopslag tager udgangspunkt i historie_new. PDF'er kan
uploades løbende, men er ikke nødvendigvis tilgængelige via opslaget, før der
findes en matchende historikrække.

- Undersøg opslag på både arbejdsårets hk_dtb og historie_new med sæson og
  bookingnummer som nøgle, uden at kopiere en åben sæson for tidligt.
- Bevar administratorbeskyttelsen af private registreringsdokumenter.
- Sikr toårssletning også for dokumenter, som endnu ikke har en historikrække.
  Det nuværende job gætter ikke datoer for umatchede filer.
- Afklar procedure for kontrol af scanning og efterfølgende makulering af
  papiroriginaler, før den bruges i driften.

Status: Udskudt. Den eksisterende løsning er ikke udvidet med arbejdsårsopslag.

## 3. Undtagelser og driftskontrol

- To historikrækker mangler indcheck: sæson 2022, booking 147 (id 3161), og
  sæson 2023, booking 153 (id 3325). Begge springes over; ingen datoer gættes.
- Én umatchet Storage-post var sandsynligvis `.emptyFolderPlaceholder`.
  PDF-filnavnene havde forventet format, men pladsholderens identitet som
  den umatchede post er ikke endeligt verificeret.
- Følg op på test-PDF med 2024-bookingnummer, som brugeren uploadede til
  kontrol af den planlagte dokumentsletning. Endelig kontrol af sletningen
  er ikke dokumenteret i denne chat.
- Kontrollér, at både PDF-trinnet og femårstrinnet gennemføres i den
  planlagte GitHub-kørsel, og at fejl/undtagelser bliver fulgt op.

## 4. Persondatainformation og øvrige kopier

- Tilpas dansk, tysk og engelsk gæsteinformation til den endelige regel:
  personfelter ryddes pr. booking fem kalenderår efter indcheck. Et nyt
  ophold forlænger ikke fristen for ældre bookingrækker.
- Beskriv, at nationalitet, bookingnummer og statistikgrundlag bevares.
  Rydning af navne og kontaktfelter er ikke i sig selv garanti for fuld
  anonymitet, hvis resterende oplysninger kan forbindes med en person.
- Afklar opbevaring af kopier i hk_dtb, backups, downloads og papirarkiv.
  Database- og Storage-jobbene håndterer ikke alle disse kopier.
- Dokumentér begrundelsen for femårsfristen og behandlingsgrundlaget for
  kundekartoteket til genbesøgsrabat.
- Fastlæg en enkel rutine for sikker makulering. P-4 er foreslået som intern
  praksis; det blev ikke fastslået som et generelt udtrykkeligt GDPR-lovkrav.

## Allerede etableret – ændres ikke af denne note

Ifølge brugerens installations- og kørselsbekræftelser:

- Dagligt GitHub-workflow kl. 02:17 UTC (03:17 dansk vintertid / 04:17 sommertid).
- Toårsregel fra indcheck for PDF i privat Storage, med fjernelse af
  storage_path og registrering af gennemført behandling. Bookingrækken bevares.
- Femårsregel fra indcheck for navn, familienavn, e-mail, telefon,
  ledsageroplysninger og noter/kommentarer i historie_new.
- Nationalitet, bookingnummer, datoer, sæson og statistikfelter bevares.
- Femårsreglen afventer dokumentoprydning og, fra sæson 2026, afsluttet sæson
  og komplette gemte sæsonstatistikker. Manglende indcheck springes over.
- Eksisterende GitHub-secrets genbruges; begge regelsæt er aktiveret via
  repository-variabler. Femårsprøven viste ingen forfaldne rækker ved installation.

Tekniske vejledninger:

- [Dokumentsletning](supabase/GUEST_REGISTRATION_RETENTION.md)
- [Femårsrydning](supabase/HISTORY_PERSONAL_DATA_RETENTION.md)

Forslag til rækkefølge ved genoptagelse: beslut hk_dtb-reglen, undersøg
arbejdsårsopslag, gennemgå undtagelser og opdatér derefter gæsteinformationen.
