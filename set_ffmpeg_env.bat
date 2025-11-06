@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === Absolute path to ffmpeg bin ===
set "FFMPEG_BIN=C:\ffmpeg\bin"

REM --- Ensure bin exists or abort ---
if not exist "%FFMPEG_BIN%\ffmpeg.exe" (
  echo ERROR: ffmpeg.exe not found in %FFMPEG_BIN%
  exit /b 2
)

REM --- Must be admin to write HKLM ---
>nul 2>&1 net session
if not "%errorlevel%"=="0" (
  echo ERROR: Must run as administrator.
  exit /b 5
)

REM --- Write ANTIX_FFMPEG (system) ---
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" ^
 /v ANTIX_FFMPEG /t REG_EXPAND_SZ /d "%FFMPEG_BIN%" /f >nul

REM --- Read current system PATH from registry ---
set "CURRENT_PATH="
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path ^| find /I "Path"') do (
    set "CURRENT_PATH=%%B"
)

REM --- If PATH missing/corrupt, seed it ---
if not defined CURRENT_PATH set "CURRENT_PATH=%SystemRoot%\system32;%SystemRoot%"

REM --- Append only if not already included ---
echo !CURRENT_PATH!; | find /I ";%FFMPEG_BIN%;">nul
if errorlevel 1 (
    set "NEW_PATH=!CURRENT_PATH!;%FFMPEG_BIN%"
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" ^
     /v Path /t REG_EXPAND_SZ /d "!NEW_PATH!" /f >nul
)

REM --- Force environment refresh (without PowerShell dependency) ---
set "VBS=%temp%\_env_broadcast.vbs"
echo Set oShell = CreateObject("WScript.Shell")>"%VBS%"
echo oShell.RegWrite "HKCU\Environment\_refresh","1","REG_SZ">>"%VBS%"
echo oShell.RegDelete "HKCU\Environment\_refresh">>"%VBS%"
cscript //nologo "%VBS%" >nul 2>&1
del "%VBS%" >nul 2>&1

echo ✅ FFMPEG appended to system PATH
echo ✅ ANTIX_FFMPEG created
endlocal
exit /b 0
