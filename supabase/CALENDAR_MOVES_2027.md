# Kalender: gemning af værelsesflytninger

Kør `migrations/20261007_calendar_moves_2027.sql` én gang i SQL Editor i samme
Supabase-projekt som portalens bookinger. Installation flytter ingen bookinger.
Kør derefter `migrations/20261011_calendar_moves_all_seasons.sql` for at fjerne
2027-begrænsningen. Den opdaterer funktionen uden at ændre bookinger eller adgangsregler.
Push derefter kalenderændringerne til appen.

Vælg 2027 i Kalender, træk en ulåst booking til et ledigt værelse, kontrollér
kladdens tabel og tryk **Gem flytning**. Vent på beskeden om, at
flytningen er gemt og genlæst. Genindlæs Kalender og Timeline, og kontrollér
værelset og de uændrede datoer. Flyt den tilbage og gem igen.

Afprøv også overlap: forsøg at gemme i et optaget værelse. Hele planen skal
afvises. En låst del af en booking må ikke flyttes; den ulåste del må gerne.
Gemning følger den valgte sæson og er ikke længere begrænset til 2027.
Kun fremtidige, ulåste ophold i den valgte sæson kan flyttes.

Lagring sker via én transaktion med tabel-lås, kontrol af oprindeligt værelse,
datoer, sæson, movable, annullering og overlap på tværs af sæsoner. Kun
room_number opdateres. Eksisterende adgangsregler fra optimeringen genbruges:
service_role i legacy eller de tre godkendte portalbrugere via authenticated RPC.

Hvis en gemning ikke kan bekræftes, fastholdes kladden og gemme-ID'et.
Tryk Gem igen for at få resultatet af samme transaktion. Nulstil og sæsonvalg
er deaktiveret, mens resultatet er uafklaret. Genindlæsning af hele browseren
kan miste sessionen; kontrollér i så fald Supabase eller Timeline før en ny kladde.
