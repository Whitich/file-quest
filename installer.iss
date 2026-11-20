#define AppVersion "1.1.0"
[Setup]
AppId={{C3391789-5929-45DC-82E0-C82D8A238974}
AppName=File Quest
AppVersion={#AppVersion}
AppPublisher=Whitich
AppPublisherURL=https://github.com/Whitich/file-quest
DefaultDirName={localappdata}\Programs\File Quest
DefaultGroupName=File Quest
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer-output
OutputBaseFilename=FileQuest-Setup-{#AppVersion}-win-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\FileQuest.exe
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "dist\FileQuest\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\File Quest"; Filename: "{app}\FileQuest.exe"
Name: "{autodesktop}\File Quest"; Filename: "{app}\FileQuest.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\FileQuest.exe"; Description: "Launch File Quest"; Flags: nowait postinstall skipifsilent
