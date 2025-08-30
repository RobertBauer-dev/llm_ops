# LLM-Ops Makefile
# Vereinfacht die Ausführung häufiger Kommandos

.PHONY: help install test run demo clean setup

# Standardziel
help:
	@echo "LLM-Ops Projekt - Verfügbare Kommandos:"
	@echo ""
	@echo "  make install    - Installiert alle Dependencies"
	@echo "  make setup      - Setup für Entwicklung"
	@echo "  make test       - Führt alle Tests aus"
	@echo "  make run        - Startet die Hauptanwendung"
	@echo "  make demo       - Führt die Demo aus"
	@echo "  make clean      - Bereinigt temporäre Dateien"
	@echo "  make lint       - Führt Code-Linting aus"
	@echo "  make format     - Formatiert Code mit Black"
	@echo "  make notebook   - Startet Jupyter Notebook"
	@echo ""

# Installation
install:
	@echo "Installiere Dependencies..."
	pip install -r requirements.txt

# Setup für Entwicklung
setup: install
	@echo "Setup für Entwicklung..."
	@if [ ! -f .env ]; then \
		echo "Kopiere env.example zu .env..."; \
		cp env.example .env; \
		echo "Bitte bearbeite .env mit deinen API Keys!"; \
	fi
	@echo "Setup abgeschlossen!"

# Tests ausführen
test:
	@echo "Führe Tests aus..."
	pytest tests/ -v

# Hauptanwendung starten
run:
	@echo "Starte LLM-Ops Anwendung..."
	python src/main.py

# Demo ausführen
demo:
	@echo "Führe LLM-Ops Demo aus..."
	python src/main.py

# Code-Linting
lint:
	@echo "Führe Code-Linting aus..."
	flake8 src/ tests/ --max-line-length=88 --ignore=E203,W503
	mypy src/ --ignore-missing-imports

# Code-Formatierung
format:
	@echo "Formatiere Code..."
	black src/ tests/ --line-length=88

# Jupyter Notebook starten
notebook:
	@echo "Starte Jupyter Notebook..."
	jupyter notebook notebooks/

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

# Datenbank initialisieren
init-db:
	@echo "Initialisiere Datenbank..."
	python -c "from src.models.model_manager import model_manager; print('Model Registry initialisiert')"
	python -c "from src.prompts.prompt_manager import prompt_manager; print('Prompt Manager initialisiert')"

# Vollständiges Setup
full-setup: setup init-db
	@echo "Vollständiges Setup abgeschlossen!"
	@echo "Du kannst jetzt 'make demo' ausführen."
