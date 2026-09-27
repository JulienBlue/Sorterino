#define MyAppName "Sorterino"
#define MyAppVersion "v2.2.3beta"
#define MyAppFileVersion "2.2.3.0"
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
Name: "{group}\Sorterino_Uninstaller"; Filename: "{uninstallexe}"; Parameters: "/SILENT /SUPPRESSMSGBOXES"; Comment: "Sorterino sicher deinstallieren"
Name: "{app}\Sorterino_Uninstaller"; Filename: "{uninstallexe}"; Parameters: "/SILENT /SUPPRESSMSGBOXES"; Comment: "Sorterino sicher deinstallieren"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} starten"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]

var
  RemoveProgramData: Boolean;
  RemoveMailCredentials: Boolean;


function ShowUninstallOptions: Boolean;
var
  OptionsForm: TSetupForm;
  HeadingLabel: TNewStaticText;
  DescriptionLabel: TNewStaticText;
  ProgramFilesCheck: TNewCheckBox;
  ProgramDataCheck: TNewCheckBox;
  MailCredentialsCheck: TNewCheckBox;
  DocumentsCheck: TNewCheckBox;
  IncomingCheck: TNewCheckBox;
  BackupsCheck: TNewCheckBox;
  SafetyLabel: TNewStaticText;
  UninstallButton: TNewButton;
  CancelButton: TNewButton;
begin
  OptionsForm := CreateCustomForm(ScaleX(560), ScaleY(455), False, False);
  try
    OptionsForm.Caption := 'Sorterino_Uninstaller';
    OptionsForm.Position := poScreenCenter;
    OptionsForm.BorderStyle := bsDialog;

    HeadingLabel := TNewStaticText.Create(OptionsForm);
    HeadingLabel.Parent := OptionsForm;
    HeadingLabel.Left := ScaleX(24);
    HeadingLabel.Top := ScaleY(22);
    HeadingLabel.Width := ScaleX(510);
    HeadingLabel.Caption := 'Was soll entfernt werden?';
    HeadingLabel.Font.Style := [fsBold];
    HeadingLabel.Font.Size := 13;

    DescriptionLabel := TNewStaticText.Create(OptionsForm);
    DescriptionLabel.Parent := OptionsForm;
    DescriptionLabel.Left := ScaleX(24);
    DescriptionLabel.Top := ScaleY(58);
    DescriptionLabel.Width := ScaleX(510);
    DescriptionLabel.Height := ScaleY(45);
    DescriptionLabel.AutoSize := False;
    DescriptionLabel.WordWrap := True;
    DescriptionLabel.Caption :=
      'Wähle zusätzliche lokale Daten aus. Deine Dokumente bleiben aus Sicherheitsgründen immer erhalten.';

    ProgramFilesCheck := TNewCheckBox.Create(OptionsForm);
    ProgramFilesCheck.Parent := OptionsForm;
    ProgramFilesCheck.Left := ScaleX(28);
    ProgramFilesCheck.Top := ScaleY(115);
    ProgramFilesCheck.Width := ScaleX(500);
    ProgramFilesCheck.Caption := 'Programmdateien und Verknüpfungen entfernen';
    ProgramFilesCheck.Checked := True;
    ProgramFilesCheck.Enabled := False;

    ProgramDataCheck := TNewCheckBox.Create(OptionsForm);
    ProgramDataCheck.Parent := OptionsForm;
    ProgramDataCheck.Left := ScaleX(28);
    ProgramDataCheck.Top := ScaleY(150);
    ProgramDataCheck.Width := ScaleX(500);
    ProgramDataCheck.Caption :=
      'Lokale Programmdaten löschen (Einstellungen, Profile, Regeln, Logs und Datenbank)';
    ProgramDataCheck.Checked := False;

    MailCredentialsCheck := TNewCheckBox.Create(OptionsForm);
    MailCredentialsCheck.Parent := OptionsForm;
    MailCredentialsCheck.Left := ScaleX(28);
    MailCredentialsCheck.Top := ScaleY(185);
    MailCredentialsCheck.Width := ScaleX(500);
    MailCredentialsCheck.Caption :=
      'Gespeicherte E-Mail-Anmeldungen und OAuth-Tokens entfernen';
    MailCredentialsCheck.Checked := False;

    DocumentsCheck := TNewCheckBox.Create(OptionsForm);
    DocumentsCheck.Parent := OptionsForm;
    DocumentsCheck.Left := ScaleX(28);
    DocumentsCheck.Top := ScaleY(235);
    DocumentsCheck.Width := ScaleX(500);
    DocumentsCheck.Caption := 'Dokumentarchive bleiben erhalten';
    DocumentsCheck.Checked := False;
    DocumentsCheck.Enabled := False;

    IncomingCheck := TNewCheckBox.Create(OptionsForm);
    IncomingCheck.Parent := OptionsForm;
    IncomingCheck.Left := ScaleX(28);
    IncomingCheck.Top := ScaleY(270);
    IncomingCheck.Width := ScaleX(500);
    IncomingCheck.Caption := 'Sorterino - Eingang bleibt erhalten';
    IncomingCheck.Checked := False;
    IncomingCheck.Enabled := False;

    BackupsCheck := TNewCheckBox.Create(OptionsForm);
    BackupsCheck.Parent := OptionsForm;
    BackupsCheck.Left := ScaleX(28);
    BackupsCheck.Top := ScaleY(305);
    BackupsCheck.Width := ScaleX(500);
    BackupsCheck.Caption := 'Sorterino - Backups bleibt erhalten';
    BackupsCheck.Checked := False;
    BackupsCheck.Enabled := False;

    SafetyLabel := TNewStaticText.Create(OptionsForm);
    SafetyLabel.Parent := OptionsForm;
    SafetyLabel.Left := ScaleX(24);
    SafetyLabel.Top := ScaleY(345);
    SafetyLabel.Width := ScaleX(510);
    SafetyLabel.Height := ScaleY(38);
    SafetyLabel.AutoSize := False;
    SafetyLabel.WordWrap := True;
    SafetyLabel.Caption :=
      'Nicht ausgewählte lokale Daten bleiben erhalten und können bei einer späteren Neuinstallation weiterverwendet werden.';

    UninstallButton := TNewButton.Create(OptionsForm);
    UninstallButton.Parent := OptionsForm;
    UninstallButton.Left := ScaleX(335);
    UninstallButton.Top := ScaleY(405);
    UninstallButton.Width := ScaleX(130);
    UninstallButton.Caption := 'Deinstallieren';
    UninstallButton.Default := True;
    UninstallButton.ModalResult := mrOk;

    CancelButton := TNewButton.Create(OptionsForm);
    CancelButton.Parent := OptionsForm;
    CancelButton.Left := ScaleX(475);
    CancelButton.Top := ScaleY(405);
    CancelButton.Width := ScaleX(70);
    CancelButton.Caption := 'Abbrechen';
    CancelButton.Cancel := True;
    CancelButton.ModalResult := mrCancel;

    Result := OptionsForm.ShowModal = mrOk;
    if Result then
    begin
      RemoveProgramData := ProgramDataCheck.Checked;
      RemoveMailCredentials := MailCredentialsCheck.Checked;
    end;
  finally
    OptionsForm.Free;
  end;
end;


function InitializeUninstall: Boolean;
begin
  RemoveProgramData := False;
  RemoveMailCredentials := False;
  Result := ShowUninstallOptions;
end;


procedure CurStepChanged(CurStep: TSetupStep);
var
  UninstallRoot: Integer;
  UninstallKey: String;
  UninstallCommand: String;
begin
  if CurStep <> ssPostInstall then
    Exit;

  if IsAdminInstallMode then
    UninstallRoot := HKLM
  else
    UninstallRoot := HKCU;

  UninstallKey :=
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
    '{F1A8C3D2-9B21-4F5E-9C2A-123456789ABC}_is1';
  UninstallCommand :=
    '"' + ExpandConstant('{uninstallexe}') + '" /SILENT /SUPPRESSMSGBOXES';
  RegWriteStringValue(UninstallRoot, UninstallKey, 'UninstallString', UninstallCommand);
  RegWriteStringValue(UninstallRoot, UninstallKey, 'QuietUninstallString', UninstallCommand);
end;

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
  ResultCode: Integer;
begin
  if CurUninstallStep <> usUninstall then
    Exit;

  AppDataPath := ExpandConstant('{userappdata}\Sorterino');

  if RemoveMailCredentials then
    Exec(
      ExpandConstant('{app}\{#MyAppExeName}'),
      '--remove-mail-credentials',
      ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if RemoveProgramData and DirExists(AppDataPath) then
    DelTree(AppDataPath, True, True, True);
end;
