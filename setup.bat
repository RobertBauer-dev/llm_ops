@echo off
REM LLM-Ops Setup für Windows
echo ================================
echo LLM-Ops Projekt Setup
echo ================================

REM Prüfe ob Python installiert ist
python --version >nul 2>&1
if errorlevel 1 (
    echo Fehler: Python ist nicht installiert oder nicht im PATH
    echo Bitte installiere Python von https://python.org
    pause
    exit /b 1
)

echo Python gefunden: 
python --version

REM Erstelle virtuelle Umgebung
echo.
echo Erstelle virtuelle Umgebung...
if exist venv (
    echo Virtuelle Umgebung existiert bereits.
    echo Lösche sie zuerst...
    rmdir /s /q venv
)
python -m venv venv

REM Aktiviere virtuelle Umgebung und installiere Dependencies
echo.
echo Installiere Dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Erstelle .env Datei
echo.
echo Erstelle .env Datei...
if not exist .env (
    copy env.example .env
    echo .env Datei erstellt. Bitte bearbeite sie mit deinen API Keys!
) else (
    echo .env Datei existiert bereits.
)

echo.
echo ================================
echo Setup abgeschlossen!
echo ================================
echo.
echo Nächste Schritte:
echo 1. Aktiviere die virtuelle Umgebung:
echo    venv\Scripts\activate.bat
echo.
echo 2. Bearbeite .env mit deinen API Keys
echo.
echo 3. Führe die Demo aus:
echo    make demo
echo    oder
echo    python src\main.py
echo.
pause
