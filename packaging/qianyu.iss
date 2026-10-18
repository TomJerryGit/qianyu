; 浅语影音 0.9 — Inno Setup script (per-user install, no admin)
; Build:  packaging\build.ps1 -Installer
; Requires Inno Setup 6 (iscc.exe on PATH).

#define AppName "浅语影音"
#define AppVersion "0.9.0"
#define AppPublisher "QianYuMedia"
#define AppExe "QianYu.exe"

[Setup]
AppId={{7E2E6A1B-4B77-4A5B-9A5E-9E3A6C3E1B21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\QianYu
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Write the uninstall entry ourselves so a locked-down registry cannot abort
; setup. Inno's built-in write failure would otherwise roll back the install.
CreateUninstallRegKey=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=QianYu-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked
Name: "associate"; Description: "注册音频文件关联（可在应用内取消）"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "..\dist\QianYu\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "运行 {#AppName}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExe}"; Parameters: "--register-associations"; Flags: runhidden; Tasks: associate

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--unregister-associations"; Flags: runhidden; RunOnceId: "RemoveAssociations"

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{7E2E6A1B-4B77-4A5B-9A5E-9E3A6C3E1B21}_is1';

procedure RegisterUninstallEntry();
begin
  { Best effort: a restricted registry leaves the app installed and the
    uninstall shortcut works, but no Add/Remove Programs entry is created. }
  RegWriteStringValue(HKCU, UninstallKey, 'DisplayName', '{#AppName}');
  RegWriteStringValue(HKCU, UninstallKey, 'DisplayVersion', '{#AppVersion}');
  RegWriteStringValue(HKCU, UninstallKey, 'Publisher', '{#AppPublisher}');
  RegWriteStringValue(HKCU, UninstallKey, 'InstallLocation', ExpandConstant('{app}'));
  RegWriteStringValue(HKCU, UninstallKey, 'DisplayIcon', ExpandConstant('{app}\{#AppExe}'));
  RegWriteStringValue(HKCU, UninstallKey, 'UninstallString', '"' + ExpandConstant('{uninstallexe}') + '"');
  RegWriteStringValue(HKCU, UninstallKey, 'QuietUninstallString', '"' + ExpandConstant('{uninstallexe}') + '" /SILENT');
  RegWriteDWordValue(HKCU, UninstallKey, 'NoModify', 1);
  RegWriteDWordValue(HKCU, UninstallKey, 'NoRepair', 1);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RegisterUninstallEntry();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RegDeleteKeyIncludingSubkeys(HKCU, UninstallKey);
end;
