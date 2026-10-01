@echo off
REM Builds dist\LeanIXLite.exe. Double-click this file on a Windows PC that has Python installed.
cd /d "%~dp0"
python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed or not on PATH.
  echo Install it from https://www.python.org/downloads/ and TICK "Add python.exe to PATH" in the installer,
  echo then double-click this file again.
  pause
  exit /b 1
)
python -m venv .venv || goto :err
call .venv\Scripts\activate.bat || goto :err
python -m pip install --upgrade pip || goto :err
pip install -r requirements-dev.txt || goto :err
python -m pytest -q tests/test_store.py || goto :err
pyinstaller --noconfirm --onefile --windowed --name LeanIXLite --collect-all customtkinter main.py || goto :err
echo.
echo ================================================================
echo  DONE.  Your program is:  %cd%\dist\LeanIXLite.exe
echo ================================================================
pause
goto :eof
:err
echo.
echo BUILD FAILED - please copy the messages above and send them to me.
pause
exit /b 1
