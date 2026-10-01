@echo off
REM Builds dist\LeanIXLite.exe  (run this on Windows, from the leanix_lite folder)
python -m venv .venv || goto :err
call .venv\Scripts\activate.bat || goto :err
python -m pip install --upgrade pip || goto :err
pip install -r requirements-dev.txt || goto :err
python -m pytest -q tests || goto :err
pyinstaller --noconfirm --onefile --windowed --name LeanIXLite --collect-all customtkinter main.py || goto :err
echo.
echo Done. Your program is: dist\LeanIXLite.exe
goto :eof
:err
echo.
echo BUILD FAILED - see the messages above.
exit /b 1
