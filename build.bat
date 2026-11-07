@echo off
rem Builds the editor so it runs without Python.
rem   build.bat           -> dist\Remnant2SaveEditor\Remnant2SaveEditor.exe  (folder: exe + _internal, recommended)
rem   build.bat onefile   -> dist\Remnant2SaveEditor.exe  (one file; antivirus heuristics flag it more often)
rem Needs Python 3.8+ on PATH. PyInstaller is installed into a local .venv, not system-wide.
setlocal
cd /d "%~dp0"

set "R2_ONEFILE=0"
set "OUT=%cd%\dist\Remnant2SaveEditor\Remnant2SaveEditor.exe"
if /i "%~1"=="onefile" (
    set "R2_ONEFILE=1"
    set "OUT=%cd%\dist\Remnant2SaveEditor.exe"
)

where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment .venv ...
    %PY% -m venv .venv || goto :fail
)

echo [2/3] Installing PyInstaller ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip pyinstaller || goto :fail

echo [3/3] Building ...
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm Remnant2SaveEditor.spec || goto :fail

echo.
echo Done:  %OUT%
if "%R2_ONEFILE%"=="0" echo Keep the exe inside its folder, next to _internal.
explorer /select,"%OUT%"
pause
exit /b 0

:fail
echo.
echo Build failed. See the messages above.
pause
exit /b 1
