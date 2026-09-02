#define MyAppName "Sorterino"
#define MyAppVersion "v2.0beta"
#define MyAppFileVersion "2.0.0.0"
#define MyAppPublisher "Seraph IT GmbH"
#define MyAppPublisherURL "https://seraph-it.de"
#define MyAppProjectURL "https://github.com/JulienBlue/Sorterino"
#define MyAppExeName "Sorterino.exe"
#define MyAppMutex "SorterinoSingletonMutex"

[Setup]
; Diese ID muss über alle Updates hinweg unverändert bleiben.
AppId={{F1A8C3D2-9B21-4F5E-9C2A-123456789ABC}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppPublisherURL}
AppSupportURL={#MyAppProjectURL}/issues
AppUpdatesURL={#MyAppProjectURL}/releases
AppMutex={#MyAppMutex}

VersionInfoVersion={#MyAppFileVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}-Installationsprogramm
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppFileVersion}

LicenseFile=LICENSE
SetupIconFile=assets\icons\default_icon_128.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; Standardmäßig benutzerbezogen installieren. Auf ausdrückliche Auswahl ist
; weiterhin eine Installation für alle Benutzer möglich.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
DefaultDirName={code:GetInstallDir}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes

; Der gebündelte Python-Runtime-Build ist für moderne 64-Bit-Windows-Systeme.
MinVersion=10.0.17763
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=installer
OutputBaseFilename=Sorterino_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
TimeStampsInUTC=yes

; Der Windows Restart Manager versucht zuerst, die Anwendung geordnet zu
; schließen. AppMutex verhindert Installation oder Deinstallation, solange
; Sorterino noch im Infobereich läuft. So wird keine aktive Verarbeitung mit
; taskkill abgebrochen.
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
RestartIfNeededByRun=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Verknüpfungen:"; Flags: unchecked

[Files]
Source: "dist\Sorterino\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\README"; Filename: "{app}\README.txt"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} starten"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]

function GetInstallDir(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{autopf}\Sorterino')
  else
    Result := ExpandConstant('{localappdata}\Programs\Sorterino');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataPath: String;
  DeleteSucceeded: Boolean;
begin
  if CurUninstallStep <> usUninstall then
    Exit;

  AppDataPath := ExpandConstant('{userappdata}\Sorterino');

  if MsgBox(
       'Lokale Sorterino-Programmdaten ebenfalls löschen?' + #13#10 + #13#10 +
       AppDataPath + #13#10 + #13#10 +
       'Gelöscht werden Einstellungen, Profile, Regeln, Logs, Mail-Abrufstände ' +
       'und das lokale Dokumentregister.' + #13#10 + #13#10 +
       'Nicht gelöscht werden Dokumentarchive, der Eingangsordner, ' +
       '„Sorterino - Backups“ und Zugangsdaten im Windows-Anmeldeinformationsmanager.',
       mbConfirmation, MB_YESNO) <> IDYES then
    Exit;

  if not DirExists(AppDataPath) then
    Exit;

  DeleteSucceeded := DelTree(AppDataPath, True, True, True);
  if not DeleteSucceeded then
    MsgBox(
      'Die lokalen Programmdaten konnten nicht vollständig gelöscht werden:' + #13#10 +
      AppDataPath + #13#10 + #13#10 +
      'Möglicherweise wird noch eine Datei verwendet. Der Ordner kann später ' +
      'manuell gelöscht werden.',
      mbError, MB_OK);
end;
