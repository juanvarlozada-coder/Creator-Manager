@echo off
REM ============================================================
REM   Creator Manager v1.0  -  Launcher
REM   Double-click to open the GUI.
REM   The file watcher is controlled from inside the app.
REM ============================================================
cd /d "%~dp0app"

REM Try pythonw first (no console window). Fall back to python.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw gui.py
) else (
    start "" python gui.py
)
exit
