#define MyAppName "Sorterino"
#define MyAppVersion "0.5.2"
#define MyAppPublisher "Seraph IT GmbH"
#define MyAppExeName "Sorterino.exe"

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
; 🔥 WICHTIG: dein neuer Build-Ordner
Source: "dist\Sorterino\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sorterino"; Filename: "{app}\{#MyAppExeName}"

; Desktop optional
Name: "{autodesktop}\Sorterino"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Sorterino starten"; Flags: nowait postinstall skipifsilent

[Registry]
; 🔥 Autostart optional (Registry – wie dein Code!)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "Sorterino"; ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: autostart; Flags: uninsdeletevalue

[UninstallDelete]
; 🔥 WICHTIG: KEINE User-Daten löschen!
; Nur falls du mal App-interne Sachen hast
Type: filesandordirs; Name: "{app}\temp"