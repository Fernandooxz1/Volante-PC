; Script de Inno Setup para Volante-PC Simracing Controller
; Genera el instalador todo-en-uno: VolantePC_Setup.exe

#define MyAppName "Volante-PC Simracing Controller"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "VolantePC"
#define MyAppURL "https://github.com/Fernandooxz1/Volante-PC"
#define MyAppExeName "VolantePC.exe"

[Setup]
AppId={{D9B3C84A-9A4B-4E38-B7C9-0D582A9C1234}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Volante-PC
DefaultGroupName=Volante-PC
AllowNoIcons=yes
OutputDir=..\dist_installer
OutputBaseFilename=VolantePC_Setup
SetupIconFile=..\volante-pc.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Archivos compilados por PyInstaller
Source: "..\dist\VolantePC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\volante-pc.ico"; DestDir: "{app}"; Flags: ignoreversion

; Instalador del driver ViGEmBus (emulación virtual Xbox 360)
Source: "drivers\ViGEmBus_Setup.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\volante-pc.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Volante-PC"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\volante-pc.ico"; Tasks: desktopicon

[Run]
; Instalación automática y silenciosa de ViGEmBus si no está presente en Windows
Filename: "{tmp}\ViGEmBus_Setup.exe"; Parameters: "/passive /norestart"; StatusMsg: "Instalando controlador de mando virtual Xbox 360 (ViGEmBus)..."; Check: NeedsViGEmBus; Flags: runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function IsViGEmBusInstalled(): Boolean;
var
  sysDir: String;
begin
  sysDir := ExpandConstant('{sys}');
  Result := FileExists(sysDir + '\drivers\ViGEmBus.sys');
  if not Result then
  begin
    sysDir := ExpandConstant('{sysnative}');
    Result := FileExists(sysDir + '\drivers\ViGEmBus.sys');
  end;
end;

function NeedsViGEmBus(): Boolean;
begin
  Result := not IsViGEmBusInstalled();
end;
