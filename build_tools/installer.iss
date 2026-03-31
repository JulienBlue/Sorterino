#define MyAppName "Sorterino"
#define MyAppVersion "0.4.0"
#define MyAppPublisher "Seraph IT GmbH"
#define MyAppExeName "app.exe"   ; ⚠️ PyInstaller Default!

[Setup]
AppId={{F1A8C3D2-9B21-4F5E-9C2A-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\Sorterino
DefaultGroupName=Sorterino

OutputDir=installer
OutputBaseFilename=Sorterino_Setup

Compression=lzma
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest

; 🔥 Icon im Explorer + Installer
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\icons\default_icon_128.ico

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked
Name: "autostart"; Description: "Mit Windows starten"; Flags: unchecked

[Files]
; 🔥 GANZER DIST-ORDNER (onedir Build)
Source: "dist\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sorterino"; Filename: "{app}\{#MyAppExeName}"

; Desktop optional
Name: "{autodesktop}\Sorterino"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Sorterino starten"; Flags: nowait postinstall skipifsilent

[Registry]
; 🔥 Autostart optional (sauber entfernbar)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "Sorterino"; ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: autostart; Flags: uninsdeletevalue

[UninstallDelete]
; 🔥 Nur Logs löschen → Config bleibt erhalten!
Type: filesandordirs; Name: "{app}\logs"