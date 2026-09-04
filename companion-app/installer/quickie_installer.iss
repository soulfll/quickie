; Inno Setup script for Quickie. Wraps dist\Quickie.exe (built by
; PyInstaller -- see quickie.spec and BUILD_WINDOWS.md) into a real
; Windows installer: welcome screen, a privacy notice the user has to
; accept, Start Menu / optional Desktop shortcuts, an optional "launch at
; Windows startup" checkbox, and a normal uninstaller.
;
; Requires Inno Setup (free): https://jrsoftware.org/isinfo.php
; To build: open this file in the Inno Setup Compiler (or run ISCC.exe
; against it from the command line) -- see BUILD_WINDOWS.md for the full
; walkthrough. Output lands in installer\Output\QuickieSetup.exe.

#define MyAppName "Quickie"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Quickie Project"
#define MyAppExeName "Quickie.exe"

[Setup]
AppId={{B3B6F1C4-6A6D-4C6C-9C7D-5B6B6E5F1A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; This is the "accept the privacy notice" step -- Setup won't let the user
; continue past it without choosing "I accept the agreement."
LicenseFile=PRIVACY.txt
OutputDir=Output
OutputBaseFilename=QuickieSetup
Compression=lzma
SolidCompression=yes
; No admin rights required -- installs to the current user only.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startupicon"; Description: "Launch Quickie automatically when Windows starts"; GroupDescription: "Additional shortcuts:"

[Files]
; The PyInstaller output -- build this first (see BUILD_WINDOWS.md).
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
