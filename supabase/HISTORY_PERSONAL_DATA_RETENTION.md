# Femårsregel for personfelter i historie_new

Reglen gælder hver bookingrække separat: indcheck + fem kalenderår ved midnat
i Europe/Copenhagen. Et senere ophold forlænger ikke fristen for en ældre række.
29. februar bliver til 28. februar, når friståret ikke er et skudår.

Fjernes: `navn`, `familie_navn`, `email`, `phone`, `spouse`, `spouce`, `comments`
og eventuelle `notes`/`note`-kolonner. Felterne sættes til SQL NULL. Migrationen
tillader derfor NULL i `navn`. `personal_data_deleted_at` registrerer gennemført
rydning; genindførte personfelter bliver ryddet igen ved næste kørsel.

Bevares: alle andre kolonner, herunder nationalitet, bookingnummer, teknisk ID,
sæson, indcheck, udcheck, bookingdato, værelsesantal, værelsesnætter og bookingkanal/
annulleringsmarkering. Der slettes ingen rækker. Det bevarer den eksisterende
booking pace-beregning og alle gemte sæsonopgørelser i `statistik_historik`.

Dette er rydning af de angivne personfelter, ikke en garanti for fuld anonymitet:
bookingreferencer og præcise datoer bevares efter aftale. Originaler i `hk_dtb`,
backups, downloads og andre systemer ændres ikke af denne funktion. Gæsteopslag
kan ikke genkende en gammel booking på de fjernede felter efter rydning.

## Installation — ingen sletning ved installation

1. Kør hele `migrations/20261030_history_personal_data_retention.sql` i Supabases
   SQL Editor som postgres, efter statistik- og toårsmigrationerne. Det tilføjer
   funktion og tidsstempel, men rydder ingen rækker. Ingen secrets skal ændres.
2. Kontrollér produktionsdatabasens kolonner, hvis den har ekstra felter ud over
   repositoryets migrationsfiler. Yderligere personfelter skal vurderes særskilt:

   ```sql
   select column_name, data_type
   from information_schema.columns
   where table_schema='public' and table_name='historie_new'
   order by ordinal_position;
   ```
3. Push kode og workflow til repositoryets standardbranch (`master`). Den
   eksisterende PDF-kørsel fortsætter uændret. Femårskørslen er separat og er
   deaktiveret, indtil den nye repository-variabel aktiveres.
4. Kør først en læseprøve i SQL Editor:

   ```sql
   select public.clear_history_personal_data(false, 100);
   ```

   Alternativt: Actions → Guest registration retention → Run workflow →
   `history_mode=preview`. PDF-parameteren `execute` gælder kun toårsreglen;
   den kan forblive slået fra. Preview ændrer ingen personfelter.
5. Når tællerne er kontrolleret: kør manuelt med `history_mode=execute`.
   Det rydder op til 2.000 rækker i batches og logger kun tællere. Der kan også
   køres direkte `select public.clear_history_personal_data(true, 100);`, som
   kun rydder én batch. Gentag i så fald, indtil `history_processed=0`.
6. Aktivér den daglige femårskørsel ved at oprette **repository variable**
   `GUEST_HISTORY_RETENTION_ENABLED=true` i GitHub Actions. Den bruger samme
   klokkeslæt og secrets som PDF-jobbet. `GUEST_RETENTION_ENABLED` skal fortsat
   være true for det samlede planlagte workflow.

## Undtagelser og kontrol

- `history_missing_checkin`: rækker uden dato, som ikke får en gættet frist.
- `history_documents_pending`: udløbne rækker, hvis PDF-oprydning endnu ikke er
  bekræftet (`storage_path` skal være NULL og `registration_deleted_at` udfyldt).
  Det eksisterende PDF-job køres før femårsjobbet på den daglige tidsplan.
- `history_statistics_pending`: fra sæson 2026 kræves afsluttet sæson i
  `high_season` og alle otte arkiverede opgørelser i `statistik_historik`.
  Mangler disse, ryddes rækken ikke. Ældre sæsoner bruger de separate historiske
  statistiktabeller og kræver ikke otte opgørelser.
- `history_due`: alle endnu ubehandlede udløbne rækker, inkl. blokerede.
- `history_eligible`: de udløbne rækker, der er klar til rydning.
- `history_processed`: faktisk ryddede rækker i denne batch (nul ved preview).

Indekser, statistikfelter og den eksisterende toårsfrist ændres ikke. Funktionen
låser sæsonstatus/statistik og historikken under transaktionen og kan kun kaldes
af service_role/postgres, ikke almindelige portalbrugere. Ved fejl rulles hele
batchen tilbage. Stop fremtidig femårsrydning ved at sætte den nye repository-
variabel til false; toårssletningen kan fortsætte.
