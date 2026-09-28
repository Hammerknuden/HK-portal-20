# Setup med Supabase-login

1. Kør hele `enable_setup_admin_access.sql` i det oprindelige projekts SQL Editor som postgres. Scriptet installerer rettigheder og en administratorbeskyttet funktion. Det ændrer ikke priser, events eller sæsonstatus. Resultatet er 10 Setup-politikker.
2. Commit og push `portal_access.py`, `pages/7_setup.py`, `modules/season_backup_view.py`, de to ændrede testfiler samt denne vejledning og SQL-filen. Der kræves ingen nye Secrets.
3. Åbn den normale app med Supabase-login som Finn eller Naja. Gem en prisændring, genindlæs og kontrollér den; sæt eventuelt prisen tilbage. Opret, redigér og slet et testevent.
4. Kontrollér, at en almindelig bruger stadig afvises på Setup, og at legacy virker.

Sæsonafslutning bruger den eksisterende databasefunktion via en ny administratorbeskyttet indgang. Den eksisterende kontrol og arkivering bevares. Afslut kun en sæson, når det faktisk er hensigten; installationen afslutter ingen sæson. Den allerede afsluttede 2026-sæson skal ikke åbnes igen som test.

Backup er tilgængelig for administratorer med begge loginmetoder i den normale app (`AUTH_MODE="dual"`), når backupkonfigurationen er på plads. Den separate Supabase-testapp og restore-testappen har fortsat ikke backupknappen aktiveret.

SQL-rettighederne gælder de to nuværende administrator-UID'er. Tilføjelse til Secrets alene giver ikke en ny administrator skriverettigheder i databasen.

Lokale test kontrollerer applikationens adgangsgrænser. SQL-installation og en virkelig sæsonafslutning skal verificeres i Supabase; de er ikke kørt af de lokale test.
