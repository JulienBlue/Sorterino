SORTERINO IM MICROSOFT STORE
================================

Produktidentität
----------------

Package/Identity/Name:
JulienBlueHirte.Sorterino

Package/Identity/Publisher:
CN=ADB34DB7-2F09-45A8-9D01-F77F334B36D9

PublisherDisplayName:
Julien Blue Hirte

Package Family Name:
JulienBlueHirte.Sorterino_pqqza58pmg7yg

Store ID:
9P2G62D9M13K


Build
-----

Voraussetzungen:

- vollständiger PyInstaller-Build einschließlich third_party
- Windows 10/11 SDK mit MakeAppx.exe
- aktive virtuelle Umgebung mit den Projektabhängigkeiten

Aus dem Projektstamm:

powershell -ExecutionPolicy Bypass -File tools\build_msix.ps1

Das Ergebnis liegt in installer\store. Das für Partner Center erzeugte Paket
bleibt absichtlich unsigniert. Microsoft signiert die veröffentlichte
Store-Ausgabe. Für eine lokale Installation ist dagegen ein separates
Testzertifikat erforderlich.


Release-Regeln
--------------

- MSIX-Versionen bestehen aus vier Zahlen. 2.2.5beta wird zu 2.2.5.0.
- Die Store-Ausgabe darf nicht gleichzeitig den GitHub-Installer installieren.
- Ein einmal in Partner Center hochgeladenes Paket wird nicht überschrieben.
- Tesseract und Poppler werden als unveränderte Laufzeitabhängigkeiten gebündelt.
- Trainings-, Diagnose- und Deinstallationsprogramme aus deren Distributionen
  werden nicht in das Store-Paket übernommen. Enthalten bleiben nur Tesseract,
  pdfinfo, pdftoppm und pdftocairo sowie die benötigten DLLs und Datendateien.
