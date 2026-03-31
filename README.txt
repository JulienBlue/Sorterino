# 📦 Sorterino v0.5.0

Desktop-Anwendung zur automatisierten Dokumentenanalyse und strukturierten Ablage.

Sorterino verarbeitet lokale Dokumente, extrahiert Inhalte mittels OCR und legt diese regelbasiert in einer definierten Ordnerstruktur ab.

---

# 🚀 Schnellstart

## Voraussetzungen

• Windows 10 oder 11  
• Keine zusätzliche Installation notwendig (EXE enthält alle Abhängigkeiten)  
• Optional: Microsoft Outlook (für MailDrop)

---

# 🖥 Anwendung starten

Nach Installation:

Sorterino starten → Speicherort wählen → Workspace wird automatisch eingerichtet

---

# ⚙️ Funktionsweise

Beim ersten Start wird eine lokale Runtime-Umgebung erzeugt:

<USER_HOME>/.sorterino_runtime/

Diese enthält:

• incoming → Eingangsdokumente  
• processed → Sicherungskopien  
• manual_sort → manuelle Nachbearbeitung  
• error → fehlerhafte Dokumente  
• logs → Protokolle  
• config.json → zentrale Konfiguration  

Alle benutzerspezifischen Konfigurationsdaten werden im Runtime-Verzeichnis gespeichert und von der Anwendung aktiv verwendet.

---

# 🔄 Verarbeitungsablauf

Die Verarbeitung erfolgt vollständig automatisiert:

1. Einlesen von Dokumenten (Ordner oder MailDrop)
2. Erstellung einer Sicherungskopie
3. OCR-Verarbeitung (PDF und Bilder)
4. Textanalyse
5. Klassifikation (regelbasiert)
6. Extraktion relevanter Metadaten
7. Generierung eines neuen Dateinamens
8. Bestimmung des Zielpfades
9. Verschieben in die Zielstruktur
10. Protokollierung

---

# 🖥 Benutzeroberfläche

Die Anwendung läuft als Hintergrundprozess im System-Tray.

Funktionen:

• Start und Stop der Pipeline  
• Anzeige des aktuellen Status  
• Live-Loganzeige  
• Konfiguration (Speicherort, Automatikmodus, Autostart)

Die GUI enthält keine Geschäftslogik und greift ausschließlich auf die Pipeline zu.

---

# ⚙️ Konfiguration

Die Konfiguration erfolgt zentral über:

.sorterino_runtime/config.json

Diese wird von GUI und Verarbeitung gemeinsam genutzt.

---

# 📧 MailDrop (optional)

Optional können E-Mail-Anhänge automatisch übernommen werden:

• Speicherung der Anhänge in den Eingangsordner  
• Verarbeitung durch die Pipeline  

Umsetzung erfolgt über Outlook VBA.

---

# 🔐 Sicherheitskonzept

• vollständiger Offline-Betrieb  
• keine Cloud-Anbindung  
• keine API-Nutzung  
• keine externe Datenübertragung  

---

# 🧠 Architektur

Die Anwendung basiert auf einer mehrschichtigen Architektur:

• Domain → Datenmodelle  
• Usecases → Geschäftslogik  
• Infrastructure → OCR, Dateisystem, Konfiguration  
• GUI → Benutzeroberfläche  

Die Schichten sind klar voneinander getrennt.

---

# 🛠 Build und Deployment

Die Anwendung wird als Verzeichnisstruktur bereitgestellt:

dist/Sorterino/

Enthält:

• Sorterino.exe  
• assets/  
• config/  
• third_party/ (OCR-Komponenten)

Ein Installer wird mit Inno Setup erstellt.

---

# 📄 Logging

Logs befinden sich unter:

.sorterino_runtime/logs/

Format:

sorterino_logs_YYYY-MM-DD.log

---

# 📊 Status

Version v0.4.5

• GUI vollständig integriert  
• Runtime-Konzept stabil  
• OCR zuverlässig  
• Klassifikation regelbasiert umgesetzt  
• Installer vorhanden  

---

# 🎯 Ziel

Ziel der Anwendung ist die automatisierte und nachvollziehbare Ablage von Dokumenten in einer strukturierten Umgebung.

---

# 💡 Hinweis

Sorterino ist als erweiterbare Basislösung konzipiert.