#define AppVersion "0.2.0"
#ifndef BuildNumber
  #define BuildNumber "local"
#endif

[Setup]
AppName=CTHarvester
AppVersion={#AppVersion}
AppPublisher=Jikhanjung
AppPublisherURL=https://github.com/jikhanjung/CTHarvester
AppSupportURL=https://github.com/jikhanjung/CTHarvester
AppUpdatesURL=https://github.com/jikhanjung/CTHarvester
DefaultDirName={commonpf}\PaleoBytes\CTHarvester
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=CTHarvester_v{#AppVersion}_build{#BuildNumber}_Installer
SetupIconFile=..\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Include main executable
Source: "..\dist\CTHarvester\CTHarvester.exe"; DestDir: "{app}"

; Include all other files and directories
Source: "..\dist\CTHarvester\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

; Copy sample data if available
; Source: "..\SampleData\*"; DestDir: "{%userprofile}\PaleoBytes\CTHarvester\SampleData"; Flags: recursesubdirs createallsubdirs

[Run]
Filename: "{app}\CTHarvester.exe"; Description: "{cm:LaunchProgram,CTHarvester}"; Flags: postinstall nowait skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  // Create a specific Start Menu group under PaleoBytes
  if not DirExists(ExpandConstant('{userprograms}\PaleoBytes')) then
    CreateDir(ExpandConstant('{userprograms}\PaleoBytes'));

  Result := True;
end;

[Icons]
Name: "{userprograms}\PaleoBytes\CTHarvester"; Filename: "{app}\CTHarvester.exe"
Name: "{autodesktop}\CTHarvester"; Filename: "{app}\CTHarvester.exe"; Tasks: desktopicon
