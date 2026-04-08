#define MyAppName "Sorterino"
#define MyAppVersion "v0.8"
#define MyAppPublisher "Seraph IT GmbH"
#define MyAppExeName "Sorterino.exe"

[Setup]
AppId={{F1A8C3D2-9B21-4F5E-9C2A-123456789ABC}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}

LicenseFile=LICENSE

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

DefaultDirName={code:GetInstallDir}
DefaultGroupName={#MyAppName}

OutputDir=installer
OutputBaseFilename=Sorterino_Setup_{#MyAppVersion}

Compression=lzma
SolidCompression=yes
WizardStyle=modern

UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=assets\icons\default_icon_128.ico

AppPublisherURL=https://seraph-it.de
AppSupportURL=https://github.com/JulienBlue/Sorterino
AppUpdatesURL=https://github.com/JulienBlue/Sorterino

CloseApplications=yes
CloseApplicationsFilter=Sorterino.exe
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; Flags: unchecked

[Files]
Source: "dist\Sorterino\*";      DestDir: "{app}";                        Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\templates\*";    DestDir: "{app}\assets\templates";       Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\icons\*";        DestDir: "{app}\assets\icons";           Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";       Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} starten"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\temp"

[Code]

// INSTALL-VERZEICHNIS
function GetInstallDir(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{autopf}\Sorterino')
  else
    Result := ExpandConstant('{localappdata}\Programs\Sorterino');
end;


// PosEx
function PosEx(SubStr, S: String; Offset: Integer): Integer;
var
  Temp: String;
  P: Integer;
begin
  Temp := Copy(S, Offset, Length(S) - Offset + 1);
  P := Pos(SubStr, Temp);
  if P > 0 then
    Result := P + Offset - 1
  else
    Result := 0;
end;


// USER-PATH AUS CONFIG
function GetUserPath(): String;
var
  ConfigFile: String;
  Content: AnsiString;
  PosStart, PosEnd: Integer;
begin
  Result := '';
  // Use environment variable syntax — works in both install and uninstall context
  ConfigFile := ExpandConstant('{%USERPROFILE}\.sorterino_config.json');

  if FileExists(ConfigFile) then
  begin
    LoadStringFromFile(ConfigFile, Content);

    PosStart := Pos('"user_path"', Content);

    if PosStart > 0 then
    begin
      PosStart := PosEx(':', Content, PosStart) + 1;
      PosStart := PosEx('"', Content, PosStart) + 1;
      PosEnd := PosEx('"', Content, PosStart);

      if PosEnd > PosStart then
        Result := Copy(Content, PosStart, PosEnd - PosStart);
    end;
  end;

  if Result = '' then
    // Fall back using env var instead of {userdocs} shell constant
    Result := ExpandConstant('{%USERPROFILE}\Documents\Sorterino');
end;


// UNINSTALL INIT
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  Exec('taskkill.exe', '/F /IM Sorterino.exe', '',
       SW_HIDE, ewWaitUntilTerminated, ResultCode);

  Sleep(800);
end;


// CLEANUP
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserPath: String;
  ResultCode: Integer;
  RuntimePath: String;
  ConfigFile: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    UserPath := GetUserPath();
    RuntimePath := UserPath + '\.sorterino_runtime';
    // Use env var syntax consistently
    ConfigFile := ExpandConstant('{%USERPROFILE}\.sorterino_config.json');

    // Config
    if MsgBox('Benutzer-Konfiguration löschen?' + #13#10 +
              '(~/.sorterino_config.json)',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      if FileExists(ConfigFile) then
        DeleteFile(ConfigFile);
    end;

    // Runtime
    if MsgBox('Runtime-Daten löschen?' + #13#10 + '(' + UserPath + ')',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      if DirExists(RuntimePath) then
        DelTree(RuntimePath, True, True, True);
    end;

    // Verknüpfungen
    if MsgBox('Verknüpfungen entfernen?' + #13#10 +
              '(Input / Manuelle Sortierung)',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('cmd.exe',
        '/c rmdir /S /Q "' + UserPath + '\Sorterino - Input"',
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

      Exec('cmd.exe',
        '/c rmdir /S /Q "' + UserPath + '\Sorterino - Manuelle Sortierung"',
        '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
