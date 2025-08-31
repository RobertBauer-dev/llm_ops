# LLM-Ops Makefile
# Vereinfacht die Ausführung häufiger Kommandos

.PHONY: help install test run demo clean setup venv venv-clean

# Standardziel
help:
	@echo "LLM-Ops Projekt - Verfügbare Kommandos:"
	@echo ""
	@echo "  make venv         - Erstellt eine neue virtuelle Umgebung"
	@echo "  make venv-clean   - Löscht die virtuelle Umgebung"
	@echo "  make install      - Installiert alle Dependencies (in venv)"
	@echo "  make setup        - Vollständiges Setup für Entwicklung"
	@echo "  make test         - Führt alle Tests aus"
	@echo "  make run          - Startet die Hauptanwendung"
	@echo "  make demo         - Führt die Demo aus"
	@echo "  make clean        - Bereinigt temporäre Dateien"
	@echo "  make lint         - Führt Code-Linting aus"
	@echo "  make format       - Formatiert Code mit Black"
	@echo "  make notebook     - Startet Jupyter Notebook"
	@echo ""

# Virtuelle Umgebung erstellen
venv:
	@echo "Erstelle virtuelle Umgebung..."
	@if [ -d "venv" ]; then \
		echo "Virtuelle Umgebung existiert bereits. Lösche sie zuerst mit 'make venv-clean'"; \
		exit 1; \
	fi
	python3 -m venv venv
	@echo "Virtuelle Umgebung erstellt. Aktiviere sie mit:"
	@echo "  source venv/bin/activate  # Linux/Mac"
	@echo "  venv\\Scripts\\activate     # Windows"

# Virtuelle Umgebung löschen
venv-clean:
	@echo "Lösche virtuelle Umgebung..."
	@if [ -d "venv" ]; then \
		rm -rf venv; \
		echo "Virtuelle Umgebung gelöscht."; \
	else \
		echo "Keine virtuelle Umgebung gefunden."; \
	fi

# Installation in virtueller Umgebung
install:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Erstelle sie zuerst mit 'make venv'"; \
		exit 1; \
	fi
	@echo "Installiere Dependencies in virtueller Umgebung..."
	venv/bin/pip install --upgrade pip
	venv/bin/pip install -r requirements.txt
	@echo "Dependencies installiert!"

# Setup für Entwicklung
setup: venv install
	@echo "Setup für Entwicklung..."
	@if [ ! -f .env ]; then \
		echo "Kopiere env.example zu .env..."; \
		cp env.example .env; \
		echo "Bitte bearbeite .env mit deinen API Keys!"; \
	fi
	@echo "Setup abgeschlossen!"
	@echo ""
	@echo "Nächste Schritte:"
	@echo "1. Aktiviere die virtuelle Umgebung:"
	@echo "   source venv/bin/activate  # Linux/Mac"
	@echo "   venv\\Scripts\\activate     # Windows"
	@echo "2. Bearbeite .env mit deinen API Keys"
	@echo "3. Führe 'make demo' aus"

# Tests ausführen (in venv)
test:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Führe Tests aus..."
	PYTHONPATH=$(PWD) venv/bin/pytest tests/ -v

# Hauptanwendung starten (in venv)
run:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Starte LLM-Ops Anwendung..."
	PYTHONPATH=$(PWD) venv/bin/python src/main.py

# Demo ausführen (in venv)
demo:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Führe LLM-Ops Demo aus..."
	PYTHONPATH=$(PWD) venv/bin/python src/main.py

# Code-Linting (in venv)
lint:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Führe Code-Linting aus..."
	PYTHONPATH=$(PWD) venv/bin/flake8 src/ tests/ --max-line-length=88 --ignore=E203,W503
	PYTHONPATH=$(PWD) venv/bin/mypy src/ --ignore-missing-imports

# Code-Formatierung (in venv)
format:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Formatiere Code..."
	PYTHONPATH=$(PWD) venv/bin/black src/ tests/ --line-length=88

# Jupyter Notebook starten (in venv)
notebook:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Starte Jupyter Notebook..."
	PYTHONPATH=$(PWD) venv/bin/jupyter notebook notebooks/

# Bereinigung
clean:
	@echo "Bereinige temporäre Dateien..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf build/
	rm -rf dist/
	@echo "Bereinigung abgeschlossen!"

# Vollständige Bereinigung (inkl. venv)
clean-all: clean venv-clean
	@echo "Vollständige Bereinigung abgeschlossen!"

# Docker-Kommandos (falls Docker verwendet wird)
docker-build:
	@echo "Baue Docker Image..."
	docker build -t llm-ops .

docker-run:
	@echo "Starte Docker Container..."
	docker run -p 8000:8000 llm-ops

# Monitoring starten
monitoring:
	@echo "Starte Monitoring Services..."
	@echo "Prometheus: http://localhost:8000"
	@echo "Grafana: http://localhost:3000"
	@echo "MLflow: http://localhost:5000"

# Datenbank initialisieren (in venv)
init-db:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Initialisiere Datenbank..."
	PYTHONPATH=$(PWD) venv/bin/python -c "from src.models.model_manager import model_manager; print('Model Registry initialisiert')"
	PYTHONPATH=$(PWD) venv/bin/python -c "from src.prompts.prompt_manager import prompt_manager; print('Prompt Manager initialisiert')"

# Vollständiges Setup
full-setup: setup init-db
	@echo "Vollständiges Setup abgeschlossen!"
	@echo "Du kannst jetzt 'make demo' ausführen."

# Dependency-Konflikte lösen
fix-deps:
	@echo "Löse Dependency-Konflikte..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	venv/bin/pip install --upgrade pip
	venv/bin/pip install --force-reinstall -r requirements.txt
	@echo "Dependencies aktualisiert!"

# Status anzeigen
status:
	@echo "LLM-Ops Projekt Status:"
	@echo "========================"
	@if [ -d "venv" ]; then \
		echo "✅ Virtuelle Umgebung: Aktiv"; \
	else \
		echo "❌ Virtuelle Umgebung: Nicht gefunden"; \
	fi
	@if [ -f ".env" ]; then \
		echo "✅ Environment: Konfiguriert"; \
	else \
		echo "❌ Environment: Nicht konfiguriert"; \
	fi
	@if [ -f "requirements.txt" ]; then \
		echo "✅ Requirements: Verfügbar"; \
	else \
		echo "❌ Requirements: Nicht gefunden"; \
	fi

# Debug-Modus
debug:
	@echo "Prüfe virtuelle Umgebung..."
	@if [ ! -d "venv" ]; then \
		echo "Virtuelle Umgebung nicht gefunden. Führe 'make setup' aus"; \
		exit 1; \
	fi
	@echo "Starte Debug-Modus..."
	PYTHONPATH=$(PWD) venv/bin/python -c "import sys; print('Python Path:'); [print(p) for p in sys.path]"
	PYTHONPATH=$(PWD) venv/bin/python -c "import config; print('Config import erfolgreich')"
	PYTHONPATH=$(PWD) venv/bin/python -c "import src; print('Src import erfolgreich')"
