"""
Konfigurationsdatei für das LLM-Ops Projekt.
Verwaltet alle Einstellungen für Modelle, Prompts, Monitoring und Deployment.
"""

import os
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
from enum import Enum


class ModelProvider(str, Enum):
    """Verfügbare LLM-Provider"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


class Environment(str, Enum):
    """Verfügbare Umgebungen"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Hauptkonfigurationsklasse für das LLM-Ops Projekt"""
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    
    # API Keys (aus Environment Variables)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    
    # Model Configuration
    default_model: str = "gpt-4"
    default_provider: ModelProvider = ModelProvider.OPENAI
    
    # Model Registry
    model_registry_uri: str = "sqlite:///./models.db"
    mlflow_tracking_uri: str = "http://localhost:5000"
    
    # Monitoring
    prometheus_port: int = 8000
    grafana_url: str = "http://localhost:3000"
    
    # Database
    database_url: str = "sqlite:///./llm_ops.db"
    redis_url: str = "redis://localhost:6379"
    
    # Cost Management
    cost_alert_threshold: float = 100.0  # USD pro Tag
    token_cost_tracking: bool = True
    
    # A/B Testing
    ab_test_enabled: bool = True
    ab_test_traffic_split: float = 0.5  # 50% für neue Version
    
    # Prompt Engineering
    prompt_versioning_enabled: bool = True
    prompt_cache_ttl: int = 3600  # 1 Stunde
    
    # Evaluation
    evaluation_dataset_path: str = "data/evaluation/"
    # evaluation_metrics wird als String definiert und später geparst
    evaluation_metrics_str: str = "accuracy,latency,cost,user_satisfaction"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Rate Limiting
    max_requests_per_minute: int = 60
    max_tokens_per_request: int = 4000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Ignoriere .env Datei wenn sie nicht existiert
        env_ignore_empty = True
    
    @property
    def evaluation_metrics(self) -> List[str]:
        """Gibt die Evaluations-Metriken als Liste zurück"""
        return [metric.strip() for metric in self.evaluation_metrics_str.split(",")]


# Global settings instance mit Fehlerbehandlung
try:
    settings = Settings()
except Exception as e:
    print(f"Warnung: Fehler beim Laden der Settings: {e}")
    print("Verwende Standard-Einstellungen...")
    # Fallback auf Standard-Einstellungen
    settings = Settings(_env_file=None)


# Model-spezifische Konfigurationen
MODEL_CONFIGS = {
    "gpt-4": {
        "provider": ModelProvider.OPENAI,
        "max_tokens": 8192,
        "temperature": 0.7,
        "cost_per_1k_tokens": 0.03,  # USD
    },
    "gpt-3.5-turbo": {
        "provider": ModelProvider.OPENAI,
        "max_tokens": 4096,
        "temperature": 0.7,
        "cost_per_1k_tokens": 0.002,  # USD
    },
    "claude-3-opus": {
        "provider": ModelProvider.ANTHROPIC,
        "max_tokens": 4096,
        "temperature": 0.7,
        "cost_per_1k_tokens": 0.015,  # USD
    },
    "claude-3-sonnet": {
        "provider": ModelProvider.ANTHROPIC,
        "max_tokens": 4096,
        "temperature": 0.7,
        "cost_per_1k_tokens": 0.003,  # USD
    }
}


# Prompt Templates Konfiguration
PROMPT_TEMPLATES = {
    "chatbot": {
        "version": "1.0",
        "template": """
Du bist ein hilfreicher Assistent. Antworte auf Deutsch und sei freundlich und professionell.

Kontext: {context}
Frage: {question}

Antwort:""",
        "variables": ["context", "question"]
    },
    "summarization": {
        "version": "1.0",
        "template": """
Fasse den folgenden Text in maximal 100 Wörtern zusammen:

Text: {text}

Zusammenfassung:""",
        "variables": ["text"]
    },
    "translation": {
        "version": "1.0",
        "template": """
Übersetze den folgenden Text von {source_language} nach {target_language}:

Text: {text}

Übersetzung:""",
        "variables": ["source_language", "target_language", "text"]
    }
}


def get_model_config(model_name: str) -> Dict:
    """Holt die Konfiguration für ein spezifisches Modell"""
    return MODEL_CONFIGS.get(model_name, MODEL_CONFIGS["gpt-4"])


def get_prompt_template(template_name: str) -> Dict:
    """Holt ein Prompt-Template"""
    return PROMPT_TEMPLATES.get(template_name, {})
