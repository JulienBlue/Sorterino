#define MyAppName "Sorterino"
#define MyAppVersion "0.7.0"
#define MyAppPublisher "Seraph IT GmbH"
#define MyAppExeName "Sorterino.exe"

[Setup]
AppId={{F1A8C3D2-9B21-4F5E-9C2A-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

DefaultDirName={code:GetInstallDir}
DefaultGroupName={#MyAppName}

OutputDir=installer
OutputBaseFilename=Sorterino_Setup_v0.7.0

Compression=lzma
SolidCompression=yes
WizardStyle=modern

UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\icons\default_icon_128.ico

AppPublisherURL=https://github.com/JulienBlue/Sorterino
AppSupportURL=https://github.com/JulienBlue/Sorterino
AppUpdatesURL=https://github.com/JulienBlue/Sorterino

# SPRACHE / SETUP
[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

# TASKS / OPTIONEN
[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked
Name: "autostart"; Description: "Mit Windows starten"; Flags: unchecked

# DATEIEN / INSTALLATION
[Files]
Source: "dist\Sorterino\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\templates\*"; DestDir: "{app}\assets\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\icons\*"; DestDir: "{app}\assets\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

# ICONS / VERKNUEPFUNGEN
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

# RUN / POST INSTALL
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} starten"; Flags: nowait postinstall skipifsilent

# REGISTRY / AUTOSTART
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; \
    Tasks: autostart; Flags: uninsdeletevalue

# UNINSTALL / CLEANUP
[UninstallDelete]
Type: filesandordirs; Name: "{app}\temp"

# INSTALL / PFAD LOGIK
[Code]
function GetInstallDir(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{autopf}\Sorterino')
  else
    Result := ExpandConstant('{localappdata}\Programs\Sorterino');
end;