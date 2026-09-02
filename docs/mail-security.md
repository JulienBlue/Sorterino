# Sicherheit des E-Mail-Imports

## Sicherheitsziel

Sorterino verarbeitet E-Mail-Anhänge lokal und ordnet jedes Postfach genau
einem Profil zu. Kontopasswörter werden niemals angefordert. Dauerhafte
Zugangsdaten dürfen weder in Profilkonfigurationen noch in Logs oder Backups
gelangen.

Das SQLite-Dokumentregister enthält keine Mailtexte, MIME-Inhalte,
OAuth-Tokens oder App-Passwörter. Es speichert nur technische
Dokumentfingerprints, bekannte Dateipfade, Zuordnungen, ausgewählte
Klassifikationsmetadaten und Verarbeitungsereignisse.

Eine ISO-Zertifizierung entsteht nicht durch einzelne Codekontrollen. Die
Implementierung orientiert sich jedoch risikobasiert an ISO/IEC 27001:2022 und
ISO/IEC 27002:2022, insbesondere Zugriffskontrolle, Identitätsverwaltung,
Schutz von Authentisierungsinformationen, sichere Authentisierung,
Kryptografie, Protokollierung, Konfigurationsmanagement und sichere
Entwicklung. ISO/IEC 27034-1:2011 liefert den Rahmen für integrierte
Anwendungssicherheit; ISO/IEC 29100:2024 für Datenminimierung und den Schutz
personenbezogener Informationen.

Die konkrete OAuth-Umsetzung folgt RFC 8252 und den aktuellen Vorgaben von
Google und Microsoft.

### Kontrollzuordnung

| Referenz | Umsetzung in Sorterino |
|---|---|
| ISO/IEC 27002:2022 A.5.15–A.5.17 | explizite Provider-Auswahl, getrennte Identitäten und Schutz sämtlicher Authentisierungsinformationen durch Windows-Tresor beziehungsweise benutzergebundene DPAPI-Verschlüsselung |
| A.8.5 Sichere Authentisierung | externer Provider-Login, Authorization Code, PKCE-S256, `state`, kein normales Kontopasswort |
| A.8.9 Konfigurationsmanagement | feste Providerdefinitionen, ausgelieferte öffentliche Client-IDs und abwärtskompatible Kontomigration |
| A.8.12 Verhinderung von Datenabfluss | keine Geheimnisse in JSON, Backups, Fehlermeldungen oder Logs; Tokens nur an fest hinterlegte Endpunkte |
| A.8.15 Protokollierung | sicherheitsrelevante Zustände ohne Tokens, Serverantworten oder Nachrichteninhalte |
| A.8.20/A.8.24 Netzwerksicherheit und Kryptografie | verifiziertes TLS ab Version 1.2, Hostnamenprüfung, HTTPS-Tokenendpunkte, Loopback-Bindung |
| A.8.25–A.8.29 sichere Entwicklung | dokumentierte Sicherheitsanforderungen, etablierter OAuth-Standard, Eingabegrenzen sowie automatisierte Positiv- und Negativtests |
| ISO/IEC 27034-1 | Sicherheitskontrollen sind Teil von Architektur, Implementierung, Test und Betrieb statt nachträglicher Zusatz |
| ISO/IEC 29100:2024 | Datenminimierung: nur notwendige Kontometadaten; keine Anbieterpasswörter; keine persistierten Mailtexte oder Access-Tokens |

Die Bezeichnungen dienen der technischen Nachvollziehbarkeit und sind keine
Konformitäts- oder Zertifizierungsaussage.

## Technische Kontrollen

- Google und Microsoft: Authorization Code Flow mit PKCE-S256. Microsoft nutzt
  dafür die offizielle Microsoft Authentication Library (MSAL).
- Anmeldung ausschließlich im externen Standardbrowser; keine eingebettete
  WebView und keine Erfassung von Anbieterpasswörtern.
- Lokaler Callback nur während der Anmeldung. Google bindet exklusiv an
  `127.0.0.1`; MSAL verwendet den für Desktopanwendungen vorgesehenen
  `http://localhost`-Redirect mit freiem lokalen Port.
- Google und Microsoft sind an ihre offiziellen Autorisierungs-, Token- und
  IMAP-Endpunkte sowie IMAP-Port 993 gebunden.
- TLS-Zertifikats- und Hostnamenprüfung; mindestens TLS 1.2.
- IMAP-Anmeldung mit SASL XOAUTH2. Passwort-Downgrade und die Verwendung
  bekannter Google-/Microsoft-Server als „Anderer Anbieter“ werden abgewiesen.
- Google-Refresh-Tokens und App-Passwörter liegen im Windows-
  Anmeldeinformationsspeicher. Microsofts MSAL-Tokenbestand
  wird einschließlich seiner kurzlebigen Access-Tokens mit Windows-DPAPI an
  das aktuelle Windows-Benutzerkonto gebunden verschlüsselt. Entschlüsselte
  Tokens verbleiben nur während ihrer Nutzung im Arbeitsspeicher.
- Logs enthalten keine Tokens, Passwörter, Serverantworten oder Nachrichten.
- Nachrichten und Anhänge besitzen Größen- und Mengenlimits. Dateinamen mit
  Steuerzeichen, Pfadanteilen oder übermäßiger Länge werden verworfen.
- Der Mailabruf verwendet einen dauerhaften UID-Cursor mit `UIDVALIDITY` statt
  des veränderlichen Gelesen-Status. `BODY.PEEK[]` und eine schreibgeschützte
  Postfachauswahl verhindern Änderungen an Gelesen- oder Stern-Markierungen.
- Der erste Abruf ist nutzerseitig auf ab jetzt, 7, 30, 90 oder 365 Tage begrenzt; danach wird lückenlos
  ab der letzten vollständig geprüften UID fortgesetzt. Begrenzte Hashlisten
  verhindern Dubletten nach Wiederholungen oder einem UIDVALIDITY-Wechsel.
- Profil- und Postfach-IDs erscheinen nicht im Dokumenteneingang. Die flach
  abgelegten Anhänge erhalten ihren Profilhinweis ausschließlich über die
  interne Zustandsdatei unter AppData.
- Beim Entfernen wird ein Google-Token nach Möglichkeit beim Anbieter
  widerrufen und anschließend immer lokal gelöscht. Microsoft bietet für
  diesen schmalen Flow keinen gleichwertigen Per-Token-Endpunkt; Sorterino
  fordert dafür bewusst keine administrativen Zusatzrechte an.
- Eine normale Programmdeinstallation entfernt Zugangsdaten nicht ungefragt
  aus dem Windows-Anmeldeinformationsspeicher. Postfächer sollten vor einer
  endgültigen Deinstallation in Sorterino entfernt und Freigaben bei Google,
  Microsoft beziehungsweise Apple bei Bedarf zusätzlich widerrufen werden.

## Provider registrieren

### Google

Die öffentliche Sorterino-Desktopanwendung ist bereits fest registriert. Nutzer
wählen ausschließlich **Mit Google verbinden** und melden sich direkt bei
Google an. Für IMAP wird der von Google vorgegebene Scope
`https://mail.google.com/` benötigt. Dieser ist weitreichend; Sorterino nutzt
ihn ausschließlich zum Lesen neuer Nachrichten, Speichern unterstützter
Anhänge und Markieren erfolgreich importierter Nachrichten.

Google behandelt installierte Anwendungen als öffentliche Clients: Der beim
Desktop-Client erzeugte Clientwert kann deshalb grundsätzlich nicht als echtes
Geheimnis gelten. Google verlangt ihn aktuell dennoch am Token-Endpunkt.
Sorterino liest ihn aus dem Build oder dem Windows-Anmeldeinformationsspeicher;
er steht nie in den JSON-Konfigurationen. Die offizielle Registrierung liegt
beim Packen in der von Git ignorierten Datei `src/oauth_release_config.py` und
wird nur in die veröffentlichte Binärdatei übernommen. PKCE schützt zusätzlich den
Authorization-Code-Austausch. Für Entwicklung können Client-ID und Clientwert
über `SORTERINO_GOOGLE_CLIENT_ID` und `SORTERINO_GOOGLE_CLIENT_SECRET`
überschrieben werden.

### Microsoft

Die öffentliche Sorterino-Desktopanwendung ist bereits fest registriert. Nutzer
wählen ausschließlich **Mit Microsoft verbinden**, melden sich direkt bei
Microsoft an und bestätigen den Zugriff. Es wird kein Microsoft-Client-Secret
gespeichert oder benötigt. Für Entwicklung und Tests kann die ausgelieferte
Client-ID intern über `SORTERINO_MICROSOFT_CLIENT_ID` überschrieben werden.

Benötigte delegierte Scopes:

- `offline_access`
- `https://outlook.office.com/IMAP.AccessAsUser.All`

## Apple und andere Anbieter

Apple/iCloud verwendet derzeit ein ausschließlich für Sorterino erzeugtes
App-Passwort mit `imap.mail.me.com:993`. Dasselbe Prinzip gilt für GMX, WEB.DE,
IONOS und benutzerdefinierte Anbieter. Das normale Kontopasswort darf nicht
verwendet werden. App-Passwörter sollten nach dem Entfernen des Postfachs auch
beim Anbieter widerrufen werden.

## Restrisiken und Betrieb

- Ein vollständig kompromittiertes Windows-Benutzerkonto kann auch auf Daten
  dieses Benutzers zugreifen. Windows-Anmeldung, aktuelle Sicherheitsupdates
  und Laufwerksverschlüsselung bleiben erforderlich.
- IMAP-OAuth-Berechtigungen sind breiter als Sorterinos tatsächliche Nutzung.
  Nutzer sollten die Freigaben regelmäßig im Anbieter-Konto prüfen.
- Dokumentanhänge liegen nach dem Import bewusst im lokalen Eingangsordner und
  anschließend im gewählten Dokumentenarchiv. Deren Schutz richtet sich nach
  Windows-/NTFS-Berechtigungen und gegebenenfalls BitLocker.
- Release-Builds müssen Abhängigkeiten, Signatur, Updateweg und die registrierten
  OAuth-Anwendungen separat prüfen. Diese Implementierung behauptet keine
  formelle ISO-Konformität oder Zertifizierung.

## Verifizierte Referenzen

- [ISO/IEC-27000-Familie und aktuelle Ausgaben 27001:2022/27002:2022](https://www.iso.org/standard/iso-iec-27000-family)
- [ISO/IEC 27034-1 – Anwendungssicherheit](https://www.iso.org/standard/44378.html)
- [ISO/IEC 29100:2024 – Privacy Framework](https://www.iso.org/standard/85938.html)
- [RFC 8252 – OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252)
- [Google OAuth für Desktop-Apps und PKCE](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google XOAUTH2 für IMAP](https://developers.google.com/workspace/gmail/imap/xoauth2-protocol)
- [Microsoft OAuth für IMAP](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth)
- [Microsoft Redirect-URI-Vorgaben](https://learn.microsoft.com/en-us/entra/identity-platform/reply-url)
- [Apple iCloud-Mailserver und App-Passwort](https://support.apple.com/en-mide/102525)
