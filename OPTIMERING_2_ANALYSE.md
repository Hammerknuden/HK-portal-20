# Optimering 2 – analyse og forslag

Dato: 15. september 2026.

## Aktuel status – 16. september 2026

**Nyere status 17. september:** Valg, forhåndsvisning og Gem/Fortryd er nu implementeret lokalt. Se `OPTIMERING_GEM_OG_FORTRYD.md` for brugerforløb, tests og den nødvendige Supabase-migration. Beskrivelsen af ren analysevisning nedenfor er den tidligere cloudversion. Gemmefunktionen er ikke installeret i cloud som del af dette arbejde.

Sæsonafgrænsning er nu håndhævet: En analyse af 2026 må kun flytte bookingrækker med sæson 2026. Andre sæsoner er faste overlapbegrænsninger, også når deres `movable` er sand. Byttevinduer dannes kun fra den valgte sæsons bookinggrænser. Eksemplet med booking 300/146 må derfor ikke trække booking 502 fra maj 2027 med. Genvalideringen håndhæver samme regel, og gamle gemte forslag skal genberegnes. Efter denne rettelse består alle **54 tests**.

Den udvidede søgning er nu implementeret lokalt i `modules/optimizer_search.py` og kaldes fra `analyze_improvements`. Den tidligere beskrivelse af manglende sammenkobling nedenfor er historisk.

- Alle målværelser 1–5 undersøges, også værelser der er optaget på ankomstdagen. Værelse 6 er undtaget.
- Mangler der samlet kapacitet en nat, vises datoen, og der søges ikke efter omrokeringer for kandidaten.
- Korte kæder flytter op til tre eksisterende bookinger. Det omfatter delblokke, flere adskilte blokeringer og flytninger gennem et tredje værelse.
- Længere bytter mellem to værelser undersøges ved fælles skæringspunkter, hvor ingen ophold deles. Hele forløb frem til sidste relevante booking kan indgå; grænsen på tre bookinger gælder ikke disse bytter.
- Hver plan indeholder alle bevægelser, inklusive kandidaten fra værelse 7, og valideres samlet for overlap og flytbarhed. Hele ophold bevares altid.
- Forslag sorteres efter færrest flyttede eksisterende bookinger, dernæst færrest berørte værelser. Visningen indeholder bookingnummer, database-ID, datoer og fra-/til-værelse for hver booking.
- Niveau 2 er nu en ren analysevisning. Den gamle udførelsesknap med separate databaseopdateringer er fjernet fra denne sektion. Ingen automatisk flytning og ingen cloud-push er foretaget.
- Datagrundlaget hentes på tværs af sæsoner med paginering. Annulleringer grupperes inden for hver sæson, så genbrugte bookingnumre ikke annullerer andre års ophold. Afsluttede ophold indgår ikke i den fremtidige overlapkontrol.

### Søgegrænser og videre arbejde

Hvert målværelse får to separate søgebudgetter: ét til byttevinduer og ét til korte kæder. Hvert budget er højst 2.000 undersøgte tilstande/vinduer eller ét sekund. Der vises højst 25 fundne forslag pr. målværelse, og udeladte forslag oplyses. Når en grænse rammes, viser resultatet, at søgningen er begrænset. Der loves ikke en udtømmende søgning i alle mulige omrokeringer.

Forslag til flere temp-bookinger er uafhængige alternativer, ikke én samlet optimering. Efter manuelle ændringer skal analysen køres igen. Eventuel senere udførelse skal genvalidere og gemme en valgt plan atomisk; denne funktion er ikke bygget.

Samlet testkørsel: **51 tests bestået**, og syntakskontrol bestået. Testene dækker regler, delblokke, skæringspunkter, lange bytter, korte kæder, kapacitetsafslag, sæsongrænser og visning uden skrivning. Små scenarier er desuden sammenlignet med en udtømmende gennemgang af alle mulige placeringer. Booking 156-fixturen giver nu forslag til både 1 og 5 med de oprindeligt beskrevne forbehold om delvise data. Booking 300 er fortsat kun repræsenteret ved et konstrueret overlapscenarie, ikke brugerens aktuelle clouddata.

Brugerfladens analysedel er testet med falske UI- og databaseadaptere. Der er ikke kørt visuel browsertest eller test mod en rigtig database.

**Historisk status efter første rettelse (erstattet af status ovenfor):** Kontrollen af `movable=True` og ankomst efter dags dato er nu samlet og anvendt på berørte bookinger i niveau 2-forslag, blokflytninger, delblokke og byttekontrol. Alle 20 automatiske tests består, inklusive de fem oprindelige fejlscenarier. Niveau 2 genlæser også bookingerne og kontrollerer lås/dato før udførelse af et gemt forslag. Gennemgangen nedenfor beskriver udgangspunktet før rettelsen; den samlede overlapkontrol og atomisk databaseudførelse er fortsat separate opgaver.

## Formål og afgrænsning

Systemet skal undersøge, hvordan bookinger på midlertidigt værelse 7 kan placeres på værelse 1–5. Resultatet skal være konkrete, kontrollerede valgmuligheder med forklaring og før/efter-visning. Analyse må aldrig i sig selv ændre bookinger. Værelse 6 er fortsat undtaget: det må hverken modtage bookinger, indgå i bytter eller kæder eller tælle som ledig kapacitet. Eksisterende bookinger på værelse 6 berøres ikke.

Denne fil er en kodebaseret analyse og et forslag til videre udvikling. Den oprindelige analyse ændrede ikke programadfærd; lås-/datokontrollen er efterfølgende rettet som beskrevet ovenfor. Der er ikke kørt analyse på aktuelle databasebookinger. Implementeringen findes i `modules/level2_optimizer.py` og vises nederst i `pages/6_timeline.py`. Der blev ikke fundet en særskilt analysefil med navnet »optimering 2« blandt projektets søgbare filnavne.

## 1. Beslutningsforløb

For hver flytbar booking på værelse 7:

1. Undersøg **alle værelser 1–5 for hele opholdet**. Vis alle direkte placeringer.
2. For hvert øvrigt målværelse: find alle optagede nætter og samtlige booking-ID'er, som blokerer.
3. Undersøg, om der findes ledig kapacitet på de manglende nætter i de andre værelser.
4. Undersøg, om de blokerende bookinger eller sammenhængende blokke kan flyttes **for hele deres egne ophold**. Ledighed på kandidatens manglende nætter alene er ikke tilstrækkelig.
5. Hvis en enkel blokflytning ikke løser det, undersøg flere skæringspunkter og begrænsede kæder af flytninger.
6. Simulér hele forslaget, inklusive placeringen af bookingen fra værelse 7. Kun en samlet konfliktfri plan må kaldes gennemførlig.
7. Vis alternativer og begrundelser; brugeren vælger selv.

Hvis alle fem værelser er optaget på en nødvendig nat, kan omrokering mellem de fem værelser ikke skabe ekstra kapacitet. Dette er et sikkert afslag under forudsætning af én booking pr. værelse og uændrede opholdsdatoer. Omvendt er ledighed et eller andet sted hver nat kun en nødvendig betingelse: det beviser ikke, at hele bookinger kan placeres.

## 2. Fund i den nuværende kode

| Fund | Betydning | Anbefalet ændring |
|---|---|---|
| Værelseslisterne i niveau 2 er 1–5. | Værelse 6 er korrekt undtaget. | Bevar afgrænsningen i én fælles definition af værelse 1–5. |
| `choose_target_rooms` tager kun værelser, der er ledige første dag. | Blokeringer i starten af opholdet overses. | Undersøg alle fem målværelser. |
| `find_target_block` vælger første score og første overlappende blok. | Andre målværelser og flere adskilte blokeringer bliver ikke undersøgt samlet. | Find alle blokerende blokke for hvert målværelse. |
| Direkte muligheder og flere delanalyser beregnes, men returneres ikke som konkrete valgmuligheder. | Brugeren får ikke hele det beregnede beslutningsgrundlag. | Returnér færdige planer med alle bevægelser. |
| Delblokke opbygges kun fremad i hovedforløbet. | Andre begyndelser og slutninger på en blok overses. | Undersøg relevante sammenhængende delblokke ved bookinggrænser. |
| Modtagerværelser filtreres efter første manglende dags aktuelle ledighed. | Et værelse, som kan frigøres gennem et bytte, sorteres fra. | Brug dette filter til enkle flytninger, men ikke som generelt afslag på kæder/bytter. |
| `movable` og fremtidig ankomst bruges til kandidaten fra værelse 7, men håndhæves ikke konsekvent for alle flyttede blokke i anbefalingerne. | Et forslag kan berøre låste eller allerede påbegyndte ophold. | Kontrollér hver berørt række i den samlede plan. |
| `build_recommendations` viser omrokeringer ud fra blokeringstal uden samlet slutkontrol. | En vist mulighed er ikke nødvendigvis gennemførlig. | Adskil undersøgte spor fra validerede forslag. |
| Niveau 2-knappen »Udfør mulighed« laver separate databaseopdateringer og flytter ikke kandidaten fra værelse 7 i samme forløb. | Delvist udførte planer er mulige; en plan kan ende uden at opfylde formålet. | Et eventuelt senere udførelsesforløb skal genvalidere og gemme hele den valgte plan samlet. |

Eksisterende blokdannelse er baseret på datoer på samme værelse: næste ankomst skal være lig med forrige afrejse. Den er ikke baseret på fortløbende bookingnumre. Det er en vigtig forskel: database-ID identificerer rækken, mens bookingnummer bruges til genkendelse. Flere rækker kan have samme bookingnummer.

## 3. Flere skæringspunkter og muligheder

Her betyder et skæringspunkt en grænse mellem hele bookinger. Et enkelt ophold deles ikke mellem værelser i denne model.

### A. Blokering i starten, midten eller slutningen

Undersøg alle tre placeringer af manglende nætter. Et målværelse behøver ikke være ledigt ved kandidatens ankomst, hvis den tidlige blokering kan flyttes.

### B. Alternative delblokke

For en tidsmæssigt sammenhængende blok A–B–C–D undersøges relevante udsnit, eksempelvis B, B–C, A–B og B–C–D, når de fjerner kandidatens blokering. Kun hele bookingrækker flyttes. Hele blokken er også et alternativ.

En tidsmæssig kæde er som udgangspunkt en søgeenhed, ikke nødvendigvis en udelelig gruppe. Hvis nogle bookinger faktisk skal blive samlet, bør dette være en eksplicit binding i data; samme bookingnummer er ikke i sig selv bevis på en sådan regel.

### C. Flere blokeringer i samme målværelse

Et målværelse kan være blokeret både tidligt og sent med ledighed imellem. Begge blokeringer skal fjernes i samme forslag. De kan flyttes til forskellige værelser, hvis den samlede slutplan er gyldig.

### D. Bytte mellem to værelser

En blok på værelse 2 kan flyttes til 4, mens en blok på 4 flyttes til 2. Kontrollen skal omfatte begge blokkes fulde ophold og den nye booking fra værelse 7. At de to blokke kan bytte, beviser ikke alene, at kandidaten kan placeres.

### E. Kæde gennem flere værelser

Eksempel: B flyttes fra 4 til 5, A fra 2 til 4, og kandidaten fra 7 til 2. Undersøg i første version kæder med højst tre eksisterende bookinger, der skifter værelse. Vis grænsen i resultatet. Større søgninger kan tilføjes senere som en udvidet analyse.

### F. Samlet analyse af flere bookinger på værelse 7

Individuelle forslag kan konkurrere om samme ledighed. Analysér derfor senere kombinationer på samme simulerede belægningsplan. To hver for sig gyldige forslag må ikke automatisk opfattes som en gyldig kombination.

## 4. Gyldighedskriterier

- Kandidaten ender på ét værelse fra 1 til 5 i hele opholdet.
- Ingen booking flyttes ind på værelse 7 som led i løsningen.
- Alle flyttede bookingrækker er eksplicit flytbare og har fremtidig ankomst, svarende til den nuværende kandidatregel. Ankomstdagen behandles dermed som låst.
- Opholdsdatoer ændres ikke, og et ophold deles ikke.
- Værelsesskift under et ophold er helt uden for analysen, også som alternativ hvis ingen løsning findes. Det er altid en særskilt manuel beslutning. Skæringspunkter må kun ligge mellem hele bookinger; en delblok består af hele bookingrækker, aldrig enkelte nætter fra et ophold.
- Alle berørte værelser kontrolleres for overlap efter samtlige simulerede ændringer.
- Ophold anvender intervallet fra ankomst inklusive til afrejse eksklusive. Afrejse og ny ankomst samme dag er tilladt.
- Konfliktkontrollen omfatter hele flyttede ophold, også uden for kandidatens periode og hen over en sæsongrænse. Et sæsonfilter alene må ikke skjule relevante bookinger.
- Annullerede bookinger optager ikke kapacitet. Timeline filtrerer dem allerede; analysefunktionen bør også have et klart inputkrav eller egen filtrering.
- Manglende ID, dublerede ID'er, ugyldige datoer eller ukendt flytbarhed skal give en forklaring frem for et positivt forslag.
- Eventuelle krav til værelsestype, antal gæster og grupper skal indgå, hvis de findes. Denne analyse antager ikke, at sådanne regler allerede håndhæves af niveau 2.

## 5. Hvordan mulighederne bør vises

For hver booking på værelse 7 vises datoer, bookingnummer og en af følgende statusser:

- **Direkte flytning mulig:** konkrete målværelser.
- **Flytning mulig med omrokering:** én eller flere validerede planer.
- **Ingen kapacitet:** konkrete nætter, hvor alle fem værelser er optaget.
- **Ingen løsning fundet inden for søgegrænsen:** hvor meget der er undersøgt; dette er ikke et bevis på umulighed.
- **Kan ikke analyseres / booking låst:** konkret årsag.

Hvert forslag viser:

1. Målværelse for kandidaten.
2. Alle berørte bookinger med bookingnummer, ID, datoer og fra/til-værelse.
3. De manglende nætter, som forslaget frigør.
4. Antal eksisterende bookinger, der flyttes, og antal berørte værelser.
5. Før/efter-timeline på en kopi af data.
6. Tidspunkt for analysen og dens søgegrænse.

Sortér som udgangspunkt efter færrest flyttede eksisterende bookinger, dernæst færrest berørte værelser. Bevar alternative målværelser som synlige valg. For en samlet analyse prioriteres først antal bookinger, der kan komme væk fra værelse 7; brugeren kan senere vælge en anden prioritering.

Analysen skriver ingen ændringer. Hvis udførelse senere ønskes som funktion, skal den være et særskilt, eksplicit valg af en komplet plan, som genkontrolleres mod aktuelle data og gemmes atomisk, dvs. alle ændringer eller ingen. Den eksisterende niveau 2-udførelse opfylder ikke dette.

## 6. Foreslået teknisk opbygning

1. Normalisér input og adskil faste og flytbare bookinger.
2. Byg opslag over ophold pr. værelse med database-ID som nøgle.
3. Beregn direkte placeringer og manglende nætter for alle fem værelser.
4. Generér relevante blokke og delblokke ved ankomst-/afrejsegrænser.
5. Søg først enkle flytninger, dernæst bytter og begrænsede kæder på kopier af belægningen. Undgå at besøge samme placeringstilstand flere gange.
6. Send hver komplet plan gennem én fælles validator.
7. Fjern dubletter ud fra ID og slutværelse, rangér og returnér forklaringer.

En plan bør indeholde `candidate_id`, `target_room`, `moves` med ID og fra/til-værelse, `missing_nights`, `validation`, `score` og metadata om datagrundlag og søgegrænser. Bookingnummer er præsentation, ikke en unik nøgle.

Sæt både en grænse for antal flyttede bookinger og et tids-/tilstandsbudget. Når en grænse rammes, skal resultatet oplyse, at analysen er delvis. En grænse må aldrig omsættes til »kan ikke flyttes«.

## 7. Kontrolscenarier til implementeringen

| Scenarie | Forventet resultat |
|---|---|
| Kun værelse 6 er ledigt hele opholdet. | Ingen flyttemulighed; værelse 6 er undtaget og tæller ikke som ledig kapacitet. |
| Ét værelse er ledigt hver nat, men forskellige værelser fra nat til nat. | Ingen direkte placering uden yderligere valideret omrokering. |
| Målværelset er blokeret på første nat; blokeringen kan flyttes. | Omrokeringsforslag findes. |
| Det bedst scorede værelse kan ikke frigøres, men et andet kan. | Det andet værelse vises. |
| To adskilte blokeringer på samme målværelse. | Begge indgår i løsningen. |
| Kun en midterdel af en kæde behøver at flyttes. | Gyldig delblok vises, hvis ingen gruppebinding forhindrer det. |
| Modtagerværelset er ledigt på den manglende nat, men optaget senere under blokeringens ophold. | Den enkle blokflytning afvises. |
| En nødvendig blokering er låst eller har ankomst i dag. | Ingen plan, der flytter den booking. |
| Et bytte er gyldigt alene, men tilbageflytningen overlapper kandidaten. | Planen afvises. |
| Alle fem værelser 1–5 er optaget en nødvendig nat. | Kapacitetsafslag med dato, uanset ledighed på værelse 6. |
| To rækker har samme bookingnummer og forskellige ID'er. | De identificeres og valideres hver for sig. |
| Afrejse og næste ankomst falder samme dag. | Ingen overlapkonflikt. |
| En flyttet blok krydser sæsongrænsen. | Bookinger på begge sider indgår i konfliktkontrollen. |
| To kandidater konkurrerer om samme plads. | Forslagene markeres som alternativer eller valideres samlet. |
| Tomt input eller ugyldige data. | Forklaring uden nedbrud eller falsk positivt forslag. |
| Søgebudgettet opbruges. | Delvis analyse, ikke definitivt afslag. |
| Analyseknappen aktiveres. | Ingen databaseopdateringer. |

## Anbefalet rækkefølge

**Første trin:** alle fem værelser, alle målværelser, komplette blokeringer, direkte forslag og enkel blokflytning med fælles slutkontrol og analysevisning.

**Andet trin:** alternative delblokke, blokeringer flere steder i perioden, bytter og begrænsede kæder med synlig søgegrænse.

**Tredje trin:** kombinationer for flere bookinger på værelse 7 samt eventuel særskilt udførelse af en brugerudvalgt, genvalideret plan.

## Udført test af eksisterende kode

Den 15. september 2026 blev `tests/test_level2_optimizer.py` kørt med 13 automatiske kontrakttests: **8 bestået, 5 fejlet**. Testene bruger konstruerede bookinger og en fast dags dato, 15. september 2026. Ingen database er tilsluttet. Programkoden er ikke ændret som del af testen.

Bestået: fremtidig flytbar kandidat, låst kandidat, kandidat med ankomst i dag, allerede indchecket kandidat, udelukkelse af værelse 6 fra kapacitet, direkte muligheder kun på 1–5, genbrug af afrejsedagen samt uændret input efter analyse.

Fejlet:

- `can_block_move` tilbyder flytning af en blok med `movable=False`.
- `can_block_move` tilbyder flytning af en blok med ankomst i dag.
- `can_block_move` tilbyder flytning af en allerede indchecket blok.
- `can_swap_blocks` accepterer et bytte med en låst booking.
- `analyze_improvements` returnerer »Kræver omrokering« med flytteforslag i et scenarie, hvor alle blokerende bookinger er låst.

Oprindelig konklusion: Reglerne blev håndhævet for kandidaten på værelse 7, men ikke konsekvent for øvrige bookinger i omrokeringen. Efter rettelsen består alle fem fejlscenarier. Testpakken er udvidet til 20 tests, som alle består, herunder positive kontroller af tilladte flytninger, låste returblokke, delblokke, manglende booking-ID'er samt ændring af lås og dags dato. Tests for UI og databaseudførelse er ikke kørt.

Gentag testen fra projektmappen med en Python-installation med pandas: `python -m unittest discover -s tests -p test_level2_optimizer.py -v`. Testen erstatter kun den ubrugte Streamlit-import, hvis Streamlit ikke er installeret. Her blev det bundtede Python-miljø med pandas 3.0.1 brugt, fordi projektets `.venv` ikke kunne starte. Timeline-brugerfladen og databaseudførelse er ikke testet.
