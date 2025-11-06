; -- Antix Digital AI Captions Subtitles Service Installer Script  --    
;1.4.16 whisper  version

[Setup]
AppName=Antix Digital AI Captions Subtitles Service
AppVersion=1.0.3
SetupIconFile=AntixDigital.ico
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
DisableFinishedPage=yes


[Dirs]
Name: "{commonappdata}\Antix Digital\AICS Service\model_cache"; Permissions: users-modify


[Files] 
Source: "AntixDigitalAICSService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\*"; DestDir: "C:\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "set_ffmpeg_env.bat"; DestDir: "{app}"; Flags: ignoreversion
;Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "model_cache\*"; \
    DestDir: "{commonappdata}\Antix Digital\AICS Service\model_cache"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "python-3.11.9-amd64.exe"; DestDir: "{app}"; Flags: ignoreversion

;[Icons] 
;Name: "{commondesktop}\Antix Digital AI Captions Subtitles Service"; Filename: "{app}\AntixDigitalAICSService.exe"

[Run]

; run as admin, silent
Filename: "{app}\set_ffmpeg_env.bat"; Flags: runhidden
; existing lines ...
Filename: "{app}\nssm.exe"; Parameters: "install ""Antix Digital AI Captions Subtitles Service"" ""{app}\AntixDigitalAICSService.exe"""; StatusMsg: "Registering Antix Digital AI Captions Subtitles Service as a Windows Service..." 

; ✅ Set to auto-start
Filename: "sc.exe"; Parameters: "config ""Antix Digital AI Captions Subtitles Service"" start= auto"; Flags: runhidden 

; ✅ Start the service immediately 
Filename: "sc.exe"; Parameters: "start ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden 

; ✅ Ensure the Display Name is what you want
Filename: "sc.exe"; Parameters: "config ""Antix Digital AI Captions Subtitles Service"" DisplayName= ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden

; ✅ Set the Description (same as the name for consistency)
Filename: "sc.exe"; Parameters: "description ""Antix Digital AI Captions Subtitles Service"" ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden


; ✅ Start the service

; ✅ Start the service

[UninstallRun] 
; ✅ Stop and delete service on uninstall 
Filename: "sc.exe"; Parameters: "stop ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden 
Filename: "sc.exe"; Parameters: "delete ""Antix Digital AI Captions Subtitles Service"""; Flags: runhidden
; Remove old ProgramData cache path (legacy/1.0.1)
[UninstallDelete]
; delete the installed application folder
Name: "{app}"; Type: filesandordirs

; delete the new ProgramData cache folder
Name: "{commonappdata}\Antix Digital\AICS Service"; Type: filesandordirs

; delete the old cache folder if it exists
;Name: "{commonappdata}\Antix Digital\model_cache"; Type: filesandordirs



[Code]
{ === custom install/uninstall messages === }

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    MsgBox('Antix Digital AI Captions Subtitles Service was installed successfully.',
           mbInformation, MB_OK);
end;

procedure CurUninstallFinished(ResultCode: Integer);
begin
  MsgBox('Antix Digital AI Captions Subtitles Service was uninstalled successfully.',
         mbInformation, MB_OK);
end;
