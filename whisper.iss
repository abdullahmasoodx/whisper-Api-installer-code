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
Source: "WhisperService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\*"; DestDir: "C:\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
;Source: "post_install.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commondesktop}\Whisper API"; Filename: "{app}\WhisperService.exe"

[Run]
; ✅ Install Python silently
Filename: "{app}\python-3.11.9-amd64.exe"; Parameters: "/passive InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python..."

; ✅ Run custom post install batch script
Filename: "{app}\post_install.bat"; WorkingDir: "{app}"; Flags: runmaximized waituntilterminated; StatusMsg: "Setting up services and dependencies..."

; ✅ Register Whisper API as a Windows service
Filename: "{app}\nssm.exe"; Parameters: "install WhisperAPIService ""{app}\WhisperService.exe"""; StatusMsg: "Registering Flask API as a Windows Service..."

; ✅ Set service to auto-start
Filename: "sc.exe"; Parameters: "config WhisperAPIService start= auto"; Flags: runhidden

; ✅ Start the service immediately
Filename: "sc.exe"; Parameters: "start WhisperAPIService"; Flags: runhidden

; ✅ Add C:\ffmpeg to system PATH
Filename: "{cmd}"; \
    Parameters: "/C setx PATH ""%PATH%;C:\ffmpeg"" /M"; \
    StatusMsg: "Adding FFmpeg to system PATH..."; \
    Flags: runhidden runascurrentuser

[UninstallRun]
; ✅ Stop and delete service on uninstall
Filename: "sc.exe"; Parameters: "stop WhisperAPIService"; Flags: runhidden
Filename: "sc.exe"; Parameters: "delete WhisperAPIService"; Flags: runhidden
