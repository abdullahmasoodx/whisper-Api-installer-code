; -- Whisper API Installer Script --

[Setup]
AppName=Whisper API GUI
AppVersion=1.0
DefaultDirName={pf}\WhisperApi
DefaultGroupName=Whisper API
OutputDir=output
OutputBaseFilename=WhisperApiInstaller
Compression=lzma
SolidCompression=yes
DisableProgramGroupPage=yes
WizardStyle=modern

[Files]
Source: "WhisperApi.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "requirements.txt"; DestDir: "{app}"
Source: "nssm.exe"; DestDir: "{app}"
Source: "post_install.bat"; DestDir: "{app}"
Source: "vs_BuildTools.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion

; Optional embedded Python
;Source: "embedded_python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{commondesktop}\Whisper API"; Filename: "{app}\WhisperApi.exe"

[Run]
; ✅ Show Python installer
Filename: "{app}\python-3.11.9-amd64.exe"; Parameters: "/passive InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python..."

; ✅ Show VC++ installer
Filename: "{app}\vs_BuildTools.exe"; Parameters: ""; StatusMsg: "Installing Visual C++ Redistributables..."

; ✅ Post-install setup (can be shown with window)
Filename: "{app}\post_install.bat"; WorkingDir: "{app}"; Flags: runmaximized waituntilterminated; StatusMsg: "Setting up services and dependencies..."



[Setup]
DiskSpanning=yes
SlicesPerDisk=1
DiskSliceSize=734003200

