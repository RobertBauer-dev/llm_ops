"""
Model Manager für LLM-Ops
Verwaltet Modelle, Versionierung und Deployment
"""

import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import mlflow
import mlflow.pytorch
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

from config.settings import settings, ModelProvider, get_model_config


class ModelStatus(str, Enum):
    """Status eines Modells"""
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class ModelMetadata:
    """Metadaten für ein Modell"""
    name: str
    version: str
    provider: ModelProvider
    status: ModelStatus
    created_at: datetime
    updated_at: datetime
    parameters: Dict[str, Any]
    performance_metrics: Dict[str, float]
    cost_per_1k_tokens: float
    description: Optional[str] = None


class ModelManager:
    """Zentrale Klasse für Model Management"""
    
    def __init__(self, demo_mode: bool = True):
        self.demo_mode = demo_mode
        if not demo_mode:
            self.mlflow_client = mlflow.tracking.MlflowClient(
                tracking_uri=settings.mlflow_tracking_uri
            )
        self.models: Dict[str, ModelMetadata] = {}
        self._load_models()
    
    def _load_models(self):
        """Lädt alle registrierten Modelle"""
        try:
            # Hier würde normalerweise die Verbindung zur Model Registry erfolgen
            # Für das Beispiel verwenden wir eine lokale Speicherung
            pass
        except Exception as e:
            print(f"Fehler beim Laden der Modelle: {e}")
    
    def register_model(
        self,
        name: str,
        provider: ModelProvider,
        parameters: Dict[str, Any],
        description: Optional[str] = None
    ) -> str:
        """Registriert ein neues Modell"""
        
        # Generiere Version basierend auf Timestamp und Parametern
        timestamp = datetime.now().isoformat()
        param_hash = hashlib.md5(
            json.dumps(parameters, sort_keys=True).encode()
        ).hexdigest()[:8]
        version = f"{timestamp}_{param_hash}"
        
        # Hole Modell-Konfiguration
        model_config = get_model_config(name)
        
        # Erstelle Model-Metadaten
        model_metadata = ModelMetadata(
            name=name,
            version=version,
            provider=provider,
            status=ModelStatus.READY,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            parameters=parameters,
            performance_metrics={},
            cost_per_1k_tokens=model_config.get("cost_per_1k_tokens", 0.0),
            description=description
        )
        
        # Speichere in MLflow (nur wenn nicht im Demo-Modus)
        if not self.demo_mode:
            try:
                with mlflow.start_run():
                    mlflow.log_params(parameters)
                    mlflow.log_metric("cost_per_1k_tokens", model_metadata.cost_per_1k_tokens)
                    
                    # Logge Model-Metadaten
                    mlflow.log_dict(
                        model_metadata.__dict__,
                        "model_metadata.json"
                    )
                    
                    # Für Demo-Zwecke: Erstelle ein einfaches Modell-Artifact
                    mlflow.log_artifact("config/settings.py", "model_config")
                    
                    print(f"MLflow Run erfolgreich erstellt für Modell {name}")
            except Exception as e:
                print(f"Warnung: MLflow Fehler (überspringe MLflow für Demo): {e}")
                print("Modell wird nur lokal registriert...")
        else:
            print(f"Demo-Modus: MLflow wird übersprungen für Modell {name}")
        
        # Speichere lokal
        model_key = f"{name}_{version}"
        self.models[model_key] = model_metadata
        
        print(f"Modell {name} Version {version} erfolgreich registriert")
        return version
    
    def deploy_model(self, name: str, version: str) -> bool:
        """Deployt ein Modell in Produktion"""
        model_key = f"{name}_{version}"
        
        if model_key not in self.models:
            raise ValueError(f"Modell {name} Version {version} nicht gefunden")
        
        model = self.models[model_key]
        model.status = ModelStatus.DEPLOYED
        model.updated_at = datetime.now()
        
        # Hier würde normalerweise das Deployment erfolgen
        # z.B. Kubernetes, Docker, etc.
        
        print(f"Modell {name} Version {version} erfolgreich deployed")
        return True
    
    def get_model(self, name: str, version: Optional[str] = None) -> Optional[ModelMetadata]:
        """Holt ein spezifisches Modell"""
        if version:
            model_key = f"{name}_{version}"
            return self.models.get(model_key)
        else:
            # Hole die neueste Version
            matching_models = [
                model for key, model in self.models.items()
                if key.startswith(f"{name}_")
            ]
            if matching_models:
                return max(matching_models, key=lambda m: m.updated_at)
        return None
    
    def list_models(self) -> List[ModelMetadata]:
        """Listet alle registrierten Modelle"""
        return list(self.models.values())
    
    def update_model_metrics(
        self,
        name: str,
        version: str,
        metrics: Dict[str, float]
    ) -> bool:
        """Aktualisiert Performance-Metriken für ein Modell"""
        model_key = f"{name}_{version}"
        
        if model_key not in self.models:
            return False
        
        model = self.models[model_key]
        model.performance_metrics.update(metrics)
        model.updated_at = datetime.now()
        
        # Logge Metriken in MLflow (nur wenn nicht im Demo-Modus)
        if not self.demo_mode:
            try:
                with mlflow.start_run():
                    for metric_name, metric_value in metrics.items():
                        mlflow.log_metric(metric_name, metric_value)
            except Exception as e:
                print(f"Warnung: MLflow Metriken-Logging fehlgeschlagen: {e}")
        
        return True
    
    def deprecate_model(self, name: str, version: str) -> bool:
        """Markiert ein Modell als veraltet"""
        model_key = f"{name}_{version}"
        
        if model_key not in self.models:
            return False
        
        model = self.models[model_key]
        model.status = ModelStatus.DEPRECATED
        model.updated_at = datetime.now()
        
        return True
    
    def get_model_cost(self, name: str, version: str, token_count: int) -> float:
        """Berechnet die Kosten für eine bestimmte Anzahl Tokens"""
        model = self.get_model(name, version)
        if not model:
            return 0.0
        
        return (token_count / 1000) * model.cost_per_1k_tokens
    
    def compare_models(
        self,
        model1: str,
        version1: str,
        model2: str,
        version2: str
    ) -> Dict[str, Any]:
        """Vergleicht zwei Modelle"""
        m1 = self.get_model(model1, version1)
        m2 = self.get_model(model2, version2)
        
        if not m1 or not m2:
            raise ValueError("Eines oder beide Modelle nicht gefunden")
        
        comparison = {
            "model1": {
                "name": m1.name,
                "version": m1.version,
                "provider": m1.provider,
                "cost_per_1k_tokens": m1.cost_per_1k_tokens,
                "performance_metrics": m1.performance_metrics
            },
            "model2": {
                "name": m2.name,
                "version": m2.version,
                "provider": m2.provider,
                "cost_per_1k_tokens": m2.cost_per_1k_tokens,
                "performance_metrics": m2.performance_metrics
            },
            "cost_difference": m2.cost_per_1k_tokens - m1.cost_per_1k_tokens
        }
        
        return comparison


# Global model manager instance (Demo-Modus aktiviert)
model_manager = ModelManager(demo_mode=True)
