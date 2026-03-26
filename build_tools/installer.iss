#define MyAppName "Sorterino"
#define MyAppVersion "0.4.0"
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

UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\icons\sorterino_sky.ico

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked
Name: "autostart"; Description: "Mit Windows starten"; Flags: unchecked

[Files]
; GANZER Build-Ordner
Source: "dist\Sorterino\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sorterino"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Sorterino"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Sorterino starten"; Flags: nowait postinstall skipifsilent

[Registry]
; Autostart optional
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "Sorterino"; ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: autostart

[UninstallDelete]
; Nur App-Logs löschen (User-Daten bleiben!)
Type: filesandordirs; Name: "{app}\logs"