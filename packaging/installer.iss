#define MyAppName "Pharmacy Desktop"
#define MyAppVersion "0.2.0"
[Setup]
AppId={{52E2D170-D546-45F5-AB20-B477FDC21437}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\PharmacyDesktop
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=PharmacyDesktop-0.2.0-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\pharmacy-icon.ico
CloseApplications=yes
UninstallDisplayIcon={app}\PharmacyDesktop.exe
[Files]
Source: "..\dist\PharmacyDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"
Source: "..\LICENSE"; DestDir: "{app}"
Source: "..\design-qa.md"; DestDir: "{app}"
[Icons]
Name: "{group}\Pharmacy Desktop"; Filename: "{app}\PharmacyDesktop.exe"
Name: "{autodesktop}\Pharmacy Desktop"; Filename: "{app}\PharmacyDesktop.exe"
[Run]
Filename: "{app}\PharmacyDesktop.exe"; Description: "Launch Pharmacy Desktop"; Flags: nowait postinstall skipifsilent
; Never delete customer data under LOCALAPPDATA\PharmacyDesktop on uninstall.
