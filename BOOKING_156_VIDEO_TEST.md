# Booking 156 – genskabelse fra video

## Opdatering 16. september 2026: udvidet søgning

Den nye søgning finder nu **26 alternativer i det delvise testdatasæt**, herunder ét til værelse 1 og to til værelse 5. Tallene er testresultater under de nedenstående antagelser, ikke bevis for tilgængelighed i den rigtige bookingdatabase.

Det korteste fundne forslag til **værelse 1** bytter et forløb fra 17. til 26. august mellem værelse 1 og 2:

- Booking 26 og 65: værelse 1 → 2.
- Booking 133, 54 og 120: værelse 2 → 1.
- Booking 156: værelse 7 → 1.

Det korteste fundne forslag til **værelse 5** bytter et forløb fra 17. til 27. august mellem værelse 5 og 2:

- Booking 21 og 25: værelse 5 → 2.
- Booking 133, 54 og 120: værelse 2 → 5.
- Booking 156: værelse 7 → 5.

Begge planer består den samlede slutkontrol i testdatasættet. Det tidligere forslag, som lod booking 65 blive stående og gav overlap, afvises fortsat. Videotestene er opdateret til at kontrollere nye alternativer og afvisning af den gamle konflikt. Resten af dokumentet beskriver den oprindelige genskabelse før udvidelsen.

## Resultat

Der er lavet en lokal, delvis genskabelse af situationen i `booking 156.mp4`. Ingen database er tilsluttet, og ingen rigtige bookinger er ændret.

Booking **156 ligger på værelse 7 fra 16. til 18. august 2026**. Værelse **1 og 5 er begge ledige natten 16.–17. august**, men optagede natten 17.–18. august:

| Muligt målværelse | Første blokerende booking | Aflæst ophold |
|---|---|---|
| 1 | 26 | 17.–21. august |
| 5 | 21 | 17.–22. august |

Begge er derfor relevante at undersøge som omrokeringer. Ingen af dem er en direkte placering for hele opholdet i den oprindelige situation. Værelse 3 har også ledighed første nat; dette gør heller ikke automatisk en hel placering mulig.

Den aktuelle analyse vælger kun ét målværelse. Med testdata vælger den værelse 1 og flytning af blokken til værelse 2, svarende til videoens forslag omkring 3:20–3:31. Den returnerer ikke et alternativt forslag til værelse 5.

## Restfejl, som genskabelsen afslører

Når programmets foreslåede tilbageflytning fra værelse 2 til værelse 1 simuleres, rammer den eksisterende booking **65 på værelse 1, 22.–25. august**:

- Booking 54, 20.–23. august, overlapper booking 65 natten 22.–23. august.
- Booking 120, 23.–26. august, overlapper booking 65 nætterne 23.–25. august.

De aflæste ophold viser dermed en konflikt uden for booking 156's eget ophold. En løsning skal være konfliktfri for hele de flyttede blokke. Kontrollen af `movable` og dags dato løser ikke denne separate fejl.

Testen viser, at det foreslåede bytte er ugyldigt i det genskabte udsnit. Den beviser ikke, at ingen anden løsning til værelse 1 eller 5 findes.

## Kilder og forudsætninger

- Før-planen er aflæst fra videoen omkring **3:05**.
- Booking 156's datoer fremgår også af redigeringsfelterne omkring **4:24**.
- Slutbilledet omkring **5:15** viser booking 156 placeret på værelse 1 efter handlingerne i videoen. Det er ikke i sig selv dokumentation for, at resten af planen er konfliktfri.
- Testen bruger udvalgte synlige bookingrækker. Den indeholder ikke alle 153 bookinger, og sammenhængende blokke kan fortsætte uden for udsnittet.
- Database-ID'er er syntetiske. Bookingnumre og ophold er manuelt aflæst fra videoen.
- Alle rækker er sat til `movable=True` som **testforudsætning**; tidslinjen dokumenterer ikke de oprindelige flag.
- Testens dags dato er sat til **16. juli 2026**, før opholdene. Optagelsens faktiske dato er ikke verificeret.

En fuldstændig genskabelse kræver et oprindeligt dataudtræk eller bekræftelse af hele de berørte blokke og deres flytbarhed.

## Automatiske tests

Data: `tests/fixtures/booking_156_video.json`.

Test: `tests/test_booking_156_video.py`.

Fem tests er kørt og består: kandidatens ophold, de to målværelsers manglende nat, fravær af direkte placering, genskabelse af det oprindelige forslag og påvisning af overlap med booking 65. **At testene består betyder, at situationen og restfejlen er genskabt; det betyder ikke, at optimeringsforslaget er godkendt.**

Kør fra projektmappen: `python -m unittest discover -s tests -p test_booking_156_video.py -v`.

Programkoden er ikke ændret i forbindelse med videogenskabelsen.
