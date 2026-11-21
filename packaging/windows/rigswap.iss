; RigSwap installer for Windows (Inno Setup 6).
;
; Built by packaging\windows\build.ps1, which passes:
;   /DAppVersion=2.0.0  /DNumericVersion=2.0.0.0  /DArch=x64|arm64  /DArchAllowed=x64compatible|arm64
;
; Installs for the current user only, into %LOCALAPPDATA%\Programs\RigSwap, so it never
; needs administrator rights. Uninstalling keeps the user's saved configs
; (%LOCALAPPDATA%\rigswap) and removes the start-at-login entry.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef NumericVersion
  #define NumericVersion "0.0.0.0"
#endif
#ifndef Arch
  #define Arch "x64"
#endif
#ifndef ArchAllowed
  #define ArchAllowed "x64compatible"
#endif

[Setup]
AppId={{B42E7D3E-AA4F-44BB-B587-219D5C49F746}
AppName=RigSwap
AppVersion={#AppVersion}
AppVerName=RigSwap {#AppVersion}
VersionInfoVersion={#NumericVersion}
AppPublisher=QPfixxy
AppPublisherURL=https://github.com/QPfixxy/RigSwap
AppSupportURL=https://github.com/QPfixxy/RigSwap/issues
AppUpdatesURL=https://github.com/QPfixxy/RigSwap/releases
DefaultDirName={localappdata}\Programs\RigSwap
DefaultGroupName=RigSwap
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed={#ArchAllowed}
ArchitecturesInstallIn64BitMode={#ArchAllowed}
LicenseFile=..\..\LICENSE
SetupIconFile=..\..\docs\logo\rigswap.ico
UninstallDisplayIcon={app}\RigSwap.exe
UninstallDisplayName=RigSwap
OutputDir=..\..\dist
OutputBaseFilename=RigSwap-{#AppVersion}-windows-{#Arch}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
; RigSwap holds this mutex while running (rigswap.core.instance). Setup and uninstall
; then ask the user to close it first, so files are never left behind and a running
; switch is never cut off.
AppMutex=RigSwapRunning
CloseApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
Name: "addtopath"; Description: "Add the &rigswap command to PATH (for the command line)"; Flags: unchecked

[Files]
Source: "..\..\dist\RigSwap\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "rigswap.cmd"; DestDir: "{app}\bin"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\RigSwap"; Filename: "{app}\RigSwap.exe"
Name: "{autodesktop}\RigSwap"; Filename: "{app}\RigSwap.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}\bin"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}\bin'))

[Run]
Filename: "{app}\RigSwap.exe"; Description: "Start RigSwap"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove the start-at-login entry, if RigSwap made one
Filename: "{app}\rigswap-cli.exe"; Parameters: "autostart off"; Flags: runhidden; RunOnceId: "AutostartOff"

[Code]
const
  EnvKey = 'Environment';

function NeedsAddPath(Dir: string): Boolean;
var
  Paths: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Paths) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Paths) + ';') = 0;
end;

{ Take our bin folder back out of the user's PATH when uninstalling. }
procedure RemoveFromPath(Dir: string);
var
  Paths, Rest, Item, Kept: string;
  P: Integer;
  Found: Boolean;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Paths) then
    exit;
  Rest := Paths;
  Kept := '';
  Found := False;
  while Rest <> '' do
  begin
    P := Pos(';', Rest);
    if P = 0 then
    begin
      Item := Rest;
      Rest := '';
    end
    else
    begin
      Item := Copy(Rest, 1, P - 1);
      Delete(Rest, 1, P);
    end;
    if CompareText(Item, Dir) = 0 then
      Found := True
    else if Item <> '' then
    begin
      if Kept <> '' then
        Kept := Kept + ';';
      Kept := Kept + Item;
    end;
  end;
  if Found then
    RegWriteExpandStringValue(HKEY_CURRENT_USER, EnvKey, 'Path', Kept);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromPath(ExpandConstant('{app}\bin'));
end;
