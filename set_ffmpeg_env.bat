@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === CONFIG: absolute path to ffmpeg bin ===
set "FFMPEG_BIN=C:\ffmpeg\bin"

REM --- Admin check (required for HKLM writes) ---
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if not "%errorlevel%"=="0" (
  echo This script must be run as Administrator. Aborting.
  exit /b 5
)

REM --- Create/Update ANTIX_FFMPEG (SYSTEM-wide) ---
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" ^
 /v ANTIX_FFMPEG /t REG_EXPAND_SZ /d "%FFMPEG_BIN%" /f >nul

REM --- Read current SYSTEM PATH (REG value, not process env) ---
for /f "tokens=2,*" %%A in (
  'reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path ^| find /I "Path"'
) do set "CURRENT_PATH=%%B"

REM --- If PATH not found for some reason, seed it ---
if not defined CURRENT_PATH set "CURRENT_PATH=%SystemRoot%\system32;%SystemRoot%"

REM --- Only append if missing (case-insensitive) ---
echo !CURRENT_PATH!; | find /I ";%FFMPEG_BIN%;">nul
if errorlevel 1 (
  set "NEW_PATH=!CURRENT_PATH!;%FFMPEG_BIN%"
  REM Write as REG_EXPAND_SZ to avoid truncation/expansion issues
  reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" ^
   /v Path /t REG_EXPAND_SZ /d "!NEW_PATH!" /f >nul
)

REM --- Nudge the system so new shells see it (no reboot) ---
powershell -NoProfile -Command ^
  "[Environment]::SetEnvironmentVariable('ANTIX_FFMPEG', '%FFMPEG_BIN%', 'Machine');" ^
  "[Environment]::SetEnvironmentVariable('Path', (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment').Path, 'Machine')" >nul

echo ANTIX_FFMPEG set to %FFMPEG_BIN%
echo PATH includes %FFMPEG_BIN%
endlocal
exit /b 0
