@echo off
rem Builds dist\Remnant2SaveEditor.exe (single file, no Python needed to run it).
rem Needs Python 3.8+ on PATH. PyInstaller is installed into a local .venv, not system-wide.
setlocal
cd /d "%~dp0"

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
echo Done:  %cd%\dist\Remnant2SaveEditor.exe
explorer /select,"%cd%\dist\Remnant2SaveEditor.exe"
pause
exit /b 0

:fail
echo.
echo Build failed. See the messages above.
pause
exit /b 1
