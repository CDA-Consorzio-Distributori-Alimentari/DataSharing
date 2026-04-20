@echo off
setlocal

REM updater.bat <path_exe> <path_release_dir> <file1,file2,...>

set "EXE_PATH=%~1"
set "RELEASE_DIR=%~2"
set "FILES=%~3"
set "TARGET_DIR=%~dp1"

REM Attendi che l'eseguibile non sia più in uso
:waitloop
ping 127.0.0.1 -n 2 >nul
move "%EXE_PATH%" "%EXE_PATH%" >nul 2>&1
if errorlevel 1 goto waitloop

REM Copia i file aggiornati
for %%F in (%FILES%) do (
    if exist "%RELEASE_DIR%\%%F" copy /Y "%RELEASE_DIR%\%%F" "%TARGET_DIR%\%%F"
)

REM Riavvia il programma
start "" "%EXE_PATH%"

exit /b 0
