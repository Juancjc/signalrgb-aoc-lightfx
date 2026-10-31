; Instalador do AOC Light FX para SignalRGB (Inno Setup 6)
; Gere com instalador\build.bat, que antes empacota a ponte com o PyInstaller.

#define AppName "AOC Light FX"
#define AppVersion "0.1.0"
#define AppExe "AOC Light FX.exe"

[Setup]
AppId={{6E9FCC7A-9CD0-4045-9279-AA7F11907DE8}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Juan Carlos Justiniano Coelho
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; instala so para o usuario atual, sem pedir administrador
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=AOC-LightFX-Setup-{#AppVersion}
SetupIconFile=icone.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Iniciar com o Windows"; GroupDescription: "Opções:"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\AOC_LightFX.js"; DestDir: "{userdocs}\WhirlwindFX\Plugins"; Flags: ignoreversion

[InstallDelete]
; atalho de inicializacao das versoes antigas (antes do instalador)
Type: files; Name: "{userstartup}\AOC Light FX Ponte.lnk"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; mesmo valor que a opcao "Iniciar com o Windows" do icone da bandeja usa
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExe}"""; Tasks: startup; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "{#AppName}"; Flags: deletevalue uninsdeletevalue; Tasks: not startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#AppExe}"""; Flags: runhidden; RunOnceId: "FecharPonte"

[UninstallDelete]
Type: files; Name: "{userdocs}\WhirlwindFX\Plugins\AOC_LightFX.js"
Type: files; Name: "{app}\ponte.log"
Type: files; Name: "{app}\config.json"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  // fecha a ponte se ela estiver aberta, para poder substituir os arquivos
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "{#AppExe}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
