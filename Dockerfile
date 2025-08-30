# LLM-Ops Dockerfile
# Containerisierung der LLM-Ops Anwendung

FROM python:3.11-slim

# Setze Arbeitsverzeichnis
WORKDIR /app

# Installiere System-Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Kopiere Requirements zuerst (für besseres Caching)
COPY requirements.txt .

# Installiere Python-Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere Anwendungscode
COPY . .

# Erstelle notwendige Verzeichnisse
RUN mkdir -p data/evaluation logs

# Setze Umgebungsvariablen
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO

# Exponiere Ports
EXPOSE 8000 5000 3000

# Health Check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Starte Anwendung
CMD ["python", "src/main.py"]
