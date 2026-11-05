@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 "Remnant2SaveEditor.pyw" & exit /b)
where pythonw >nul 2>nul && (start "" pythonw "Remnant2SaveEditor.pyw" & exit /b)
echo Python 3 not found. Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH").
pause
