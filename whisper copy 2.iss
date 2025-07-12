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
DiskSpanning=yes
SlicesPerDisk=1
DiskSliceSize=734003200

[Files]
Source: "WhisperApi.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "nssm.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs"

[Icons]
Name: "{commondesktop}\Whisper API"; Filename: "{app}\WhisperApi.exe"

[Run]
; ✅ Install Python silently
Filename: "{app}\python-3.11.9-amd64.exe"; Parameters: "/passive InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python..."

; ✅ Register Flask API as Windows service using NSSM
Filename: "{app}\nssm.exe"; Parameters: "install WhisperService ""{app}\WhisperApi.exe"""; StatusMsg: "Creating background service..."

; ✅ Set working directory for service
Filename: "{app}\nssm.exe"; Parameters: "set WhisperService AppDirectory ""{app}"""

; ✅ Redirect service output to logs
Filename: "{app}\nssm.exe"; Parameters: "set WhisperService AppStdout ""{app}\logs\service.log"""
Filename: "{app}\nssm.exe"; Parameters: "set WhisperService AppStderr ""{app}\logs\service_error.log"""

; ✅ Set service to auto start
Filename: "{app}\nssm.exe"; Parameters: "set WhisperService Start SERVICE_AUTO_START"

; ✅ Start service immediately
Filename: "sc.exe"; Parameters: "start WhisperService"; Flags: runhidden

[UninstallRun]
Filename: "sc.exe"; Parameters: "stop WhisperService"; Flags: runhidden
Filename: "sc.exe"; Parameters: "delete WhisperService"; Flags: runhidden
