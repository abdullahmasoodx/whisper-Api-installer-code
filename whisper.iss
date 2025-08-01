; -- Antix Digital AI Captions Subtitles Service Installer Script  --    
;1.4.17 whisper  version

[Setup]
AppName=Antix Digital AI Captions Subtitles Service
AppVersion=1.0.1
AppVerName=Antix Digital AI Captions Subtitles Service
AppPublisher= Antix Digital Inc
AppPublisherURL=https://www.antixdigital.com
AppSupportURL=https://support.antixdigital.com
AppUpdatesURL=https://updates.antixdigital.com
AppContact=contact@antixdigital.com
AppComments=AI-based real-time captioning and subtitle generation service.
DefaultDirName={pf}\Antix Digital\AICS Service
DefaultGroupName=Antix Digital AI Captions Subtitles Service
OutputDir=output
OutputBaseFilename=AntixDigitalAICSService
Compression=lzma
SolidCompression=yes
DisableProgramGroupPage=yes
WizardStyle=modern
PrivilegesRequired=admin
DiskSpanning=yes
SlicesPerDisk=1
DiskSliceSize=734003200




[Files] 
Source: "AntixDigitalAICSService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\*"; DestDir: "C:\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
;Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons] 
Name: "{commondesktop}\Antix Digital AI Captions Subtitles Service"; Filename: "{app}\AntixDigitalAICSService.exe" 

[Run] 
; ✅ Install Python silently 
;Filename: "{app}\python-3.11.9-amd64.exe"; Parameters: "/passive InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python..." 

; ✅ Register Antix Digital AI Captions Subtitles Service as a Windows service 
Filename: "{app}\nssm.exe"; Parameters: "install ""Antix Digital AI Captions Subtitles Service"" ""{app}\AntixDigitalAICSService.exe"""; StatusMsg: "Registering Antix Digital AI Captions Subtitles Service as a Windows Service..." 

; ✅ Set service to auto-start 
Filename: "sc.exe"; Parameters: "config ""Antix Digital AI Captions Subtitles Service"" start= auto"; Flags: runhidden 

; ✅ Start the service immediately 
Filename: "sc.exe"; Parameters: "start ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden 

; ✅ Add C:\ffmpeg to system PATH 
Filename: "{cmd}"; Parameters: "/C setx PATH ""C:\ffmpeg\bin;%PATH%"" /M"; StatusMsg: "Adding C:\ffmpeg\bin to system PATH..."; Flags: runhidden runascurrentuser 

[UninstallRun] 
; ✅ Stop and delete service on uninstall 
Filename: "sc.exe"; Parameters: "stop ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden 
Filename: "sc.exe"; Parameters: "delete ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden
