#!/bin/bash

# LLM-Ops Setup für Linux/Mac
echo "================================"
echo "LLM-Ops Projekt Setup"
echo "================================"

# Prüfe ob Python installiert ist
if ! command -v python3 &> /dev/null; then
    echo "Fehler: Python3 ist nicht installiert"
    echo "Bitte installiere Python von https://python.org"
    exit 1
fi

echo "Python gefunden:"
python3 --version

# Erstelle virtuelle Umgebung
echo ""
echo "Erstelle virtuelle Umgebung..."
if [ -d "venv" ]; then
    echo "Virtuelle Umgebung existiert bereits."
    echo "Lösche sie zuerst..."
    rm -rf venv
fi
python3 -m venv venv

# Aktiviere virtuelle Umgebung und installiere Dependencies
echo ""
echo "Installiere Dependencies..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Erstelle .env Datei
echo ""
echo "Erstelle .env Datei..."
if [ ! -f ".env" ]; then
    cp env.example .env
    echo ".env Datei erstellt. Bitte bearbeite sie mit deinen API Keys!"
else
    echo ".env Datei existiert bereits."
fi

echo ""
echo "================================"
echo "Setup abgeschlossen!"
echo "================================"
echo ""
echo "Nächste Schritte:"
echo "1. Aktiviere die virtuelle Umgebung:"
echo "   source venv/bin/activate"
echo ""
echo "2. Bearbeite .env mit deinen API Keys"
echo ""
echo "3. Führe die Demo aus:"
echo "   make demo"
echo "   oder"
echo "   python src/main.py"
echo ""

# Mache das Skript ausführbar
chmod +x setup.sh
