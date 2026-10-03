# Tätigkeitskontexte und Branchenmodule

Dieses Dokument hält die geplante Weiterentwicklung der Profil- und Ablagelogik
fest. Es beschreibt noch keine implementierte Funktion.

## Zielbild

Eine reale Person kann mehrere private und berufliche Lebensbereiche parallel
haben. Berufliche Angaben werden deshalb nicht als einzelne Berufsauswahl an der
Person gespeichert, sondern als eigenständige Tätigkeitskontexte:

    Profil -> Person -> Tätigkeit -> Dokumenttyp -> Ablageziel

Ein Dokument wird einmal physisch abgelegt. Weitere fachliche Zusammenhänge
werden als Metadaten oder Tags geführt, damit keine künstlichen Dateikopien
entstehen.

## Tätigkeit

Eine Tätigkeit soll mindestens enthalten:

- stabile ID und frei gewählte Bezeichnung
- Status: geplant, aktiv, ruhend oder beendet
- Beschäftigungsform: angestellt, Ausbildung/Studium, freiberuflich,
  gewerblich, verbeamtet, ehrenamtlich oder sonstig
- Haupt- oder Nebentätigkeit
- eine primäre und optionale weitere Fachgruppen
- Arbeitgeber, Auftraggeber und wiederkehrende Gegenparteien
- tätigkeitsbezogene Kennungen und Matching-Begriffe
- aktivierte Zusatzmodule
- eigenes Routing innerhalb des Archivs

Beispiele sind eine angestellte IT-Tätigkeit neben freiberuflicher Schauspielerei
oder eine Pflegeanstellung neben einer gesonderten Pflegeberatung.

## Fachgruppen und Module

Fachgruppen liefern kontrolliertes Vokabular und Dokumentkandidaten, erzwingen
aber allein keine Ablage. Vorgesehen sind zunächst Kunst und Kultur, IT und
Medien, Gesundheit und Pflege, Beratung und Dienstleistungen, Bildung und
Unterricht, Verwaltung und öffentlicher Dienst, Handwerk, Handel, Vermietung
und eine allgemeine Tätigkeit.

Zusatzmodule bilden besondere Kontexte ab, beispielsweise KSK, GEMA, GVL,
VG Wort, VG Bild-Kunst, Pflegeberuf, Beamtenstatus, Beihilfe, Reisekosten,
Förderungen, Umsatzsteuer, Personal, Fahrzeug und Anlagevermögen.

## Zuordnungslogik

Die Pipeline soll nacheinander Profil, Person, privaten oder beruflichen Kontext,
konkrete Tätigkeit und Dokumenttyp bestimmen. Starke Signale sind eindeutige
Arbeitgeber oder Auftraggeber, Steuer- und Vertragsnummern, berufliche
E-Mail-Adressen sowie modulbezogene Kennungen. Fachgruppe und Berufsbezeichnung
sind nur unterstützende Signale.

Bei Mehrdeutigkeit fragt die manuelle Prüfung nach dem passenden Kontext und
kann die bestätigte Zuordnung für wiederkehrende Absender oder Kennungen lernen.
Die Zuordnung benötigt langfristig neben `profile_id` und `person_ids` eine
optionale `activity_id`.

## Reihenfolge

1. Datenmodell und Migrationsregeln festlegen.
2. Mehrere Tätigkeiten in der Profilverwaltung verwalten.
3. Aktivitätsmatching und manuelle Auswahl ergänzen.
4. Gemeinsamen Kern für Selbstständige und Freiberufler einführen.
5. Kunst und Kultur als erstes Branchenmodul umsetzen.
6. Pflege, öffentlicher Dienst/Beamtenstatus, Bildung, IT und Beratung ergänzen.
7. Private Dokumentlücken unabhängig davon weiter schließen.
8. Aufbewahrungs- und Fristenlogik erst nach gesonderter fachlicher Prüfung
   offizieller aktueller Vorgaben entwickeln.

## Fachlicher Kern für Selbstständige

Der gemeinsame Kern umfasst Stammdaten und Anmeldungen, Einnahmen, Ausgaben,
Rechnungen, Verträge, Steuern, Versicherungen, Förderungen, Reisekosten und
Anlagevermögen. Branchenmodule ergänzen nur wirklich fachspezifische Bereiche.

Das Modul Kunst und Kultur soll insbesondere KSK, Verwertungsgesellschaften,
Engagements und Produktionen, Werke und Rechte, Honorare und Ausschüttungen,
Förderungen sowie Technik, Instrumente und Material abbilden.

Das Modul Gesundheit und Pflege soll Berufsurkunden, Anerkennungen,
Pflichtfortbildungen, Hygiene- und Gesundheitsnachweise, Einsatzunterlagen,
Pflegeberatung, Leistungsnachweise und Berufshaftpflicht abbilden.

Beamtenstatus ist ein Statusmodul und kein Beruf. Es ergänzt beispielsweise
Ernennung, Besoldung, Beihilfe, Versorgung, Versetzung, Beurteilung und
Nebentätigkeit für unterschiedliche Fachgruppen.
