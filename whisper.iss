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
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "post_install.bat"; DestDir: "{app}"; Flags: ignoreversion
;Source: "vs_BuildTools.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\Whisper API"; Filename: "{app}\WhisperApi.exe"

[Run]
; ✅ Install Python silently
Filename: "{app}\python-3.11.9-amd64.exe"; Parameters: "/passive InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python..."

; ✅ Install Visual C++ build tools
;Filename: "{app}\vs_BuildTools.exe"; Parameters: ""; StatusMsg: "Installing Visual C++ Redistributables..."

; ✅ Run custom post install batch script (if needed)
Filename: "{app}\post_install.bat"; WorkingDir: "{app}"; Flags: runmaximized waituntilterminated; StatusMsg: "Setting up services and dependencies..."

; ✅ Register the Flask API as a Windows service using NSSM
Filename: "{app}\nssm.exe"; Parameters: "install WhisperAPIService ""{app}\WhisperApi.exe"""; StatusMsg: "Registering Flask API as a Windows Service..."

; ✅ Set the service to start automatically on system boot
Filename: "sc.exe"; Parameters: "config WhisperAPIService start= auto"; Flags: runhidden

; ✅ Start the service immediately
Filename: "sc.exe"; Parameters: "start WhisperAPIService"; Flags: runhidden

; OPTIONAL - Uncomment to open browser to test
; Filename: "http://localhost:8001"; Flags: shellexec postinstall

[UninstallRun]
; ✅ Stop and remove the service on uninstall
Filename: "sc.exe"; Parameters: "stop WhisperAPIService"; Flags: runhidden
Filename: "sc.exe"; Parameters: "delete WhisperAPIService"; Flags: runhidden
