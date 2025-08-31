"""
Prompt Manager für LLM-Ops
Verwaltet Prompts, Versionierung und A/B Testing
"""

import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import random

from config.settings import settings, get_prompt_template


class PromptStatus(str, Enum):
    """Status eines Prompts"""
    DRAFT = "draft"
    ACTIVE = "active"
    TESTING = "testing"
    DEPRECATED = "deprecated"


@dataclass
class PromptVersion:
    """Eine Version eines Prompts"""
    id: str
    template_name: str
    version: str
    template: str
    variables: List[str]
    status: PromptStatus
    created_at: datetime
    updated_at: datetime
    performance_metrics: Dict[str, float]
    description: Optional[str] = None
    tags: List[str] = None


class PromptManager:
    """Zentrale Klasse für Prompt Management"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
        self.prompts: Dict[str, PromptVersion] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """Lädt alle gespeicherten Prompts"""
        try:
            # Lade von Redis
            for key in self.redis_client.keys("prompt:*"):
                prompt_data = self.redis_client.get(key)
                if prompt_data:
                    prompt_dict = json.loads(prompt_data)
                    prompt_dict['created_at'] = datetime.fromisoformat(prompt_dict['created_at'])
                    prompt_dict['updated_at'] = datetime.fromisoformat(prompt_dict['updated_at'])
                    prompt = PromptVersion(**prompt_dict)
                    self.prompts[prompt.id] = prompt
        except Exception as e:
            print(f"Fehler beim Laden der Prompts: {e}")
    
    def _save_prompt(self, prompt: PromptVersion):
        """Speichert einen Prompt in Redis"""
        try:
            prompt_dict = asdict(prompt)
            prompt_dict['created_at'] = prompt.created_at.isoformat()
            prompt_dict['updated_at'] = prompt.updated_at.isoformat()
            
            self.redis_client.setex(
                f"prompt:{prompt.id}",
                settings.prompt_cache_ttl,
                json.dumps(prompt_dict)
            )
        except Exception as e:
            print(f"Fehler beim Speichern des Prompts: {e}")
    
    def create_prompt(
        self,
        template_name: str,
        template: str,
        variables: List[str],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Erstellt einen neuen Prompt"""
        
        # Generiere eindeutige ID
        timestamp = datetime.now().isoformat()
        template_hash = hashlib.md5(template.encode()).hexdigest()[:8]
        prompt_id = f"{template_name}_{timestamp}_{template_hash}"
        
        # Erstelle Prompt-Version
        prompt = PromptVersion(
            id=prompt_id,
            template_name=template_name,
            version=f"v{len([p for p in self.prompts.values() if p.template_name == template_name]) + 1}",
            template=template,
            variables=variables,
            status=PromptStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            performance_metrics={},
            description=description,
            tags=tags or []
        )
        
        # Speichere Prompt
        self.prompts[prompt_id] = prompt
        self._save_prompt(prompt)
        
        print(f"Prompt {template_name} Version {prompt.version} erstellt")
        return prompt_id
    
    def get_prompt(self, prompt_id: str) -> Optional[PromptVersion]:
        """Holt einen spezifischen Prompt"""
        return self.prompts.get(prompt_id)
    
    def get_active_prompt(self, template_name: str) -> Optional[PromptVersion]:
        """Holt den aktiven Prompt für einen Template-Namen"""
        active_prompts = [
            p for p in self.prompts.values()
            if p.template_name == template_name and p.status == PromptStatus.ACTIVE
        ]
        return active_prompts[0] if active_prompts else None
    
    def activate_prompt(self, prompt_id: str) -> bool:
        """Aktiviert einen Prompt"""
        if prompt_id not in self.prompts:
            return False
        
        prompt = self.prompts[prompt_id]
        
        # Deaktiviere andere Prompts mit gleichem Template-Namen
        for other_prompt in self.prompts.values():
            if (other_prompt.template_name == prompt.template_name and 
                other_prompt.status == PromptStatus.ACTIVE):
                other_prompt.status = PromptStatus.DEPRECATED
                other_prompt.updated_at = datetime.now()
                self._save_prompt(other_prompt)
        
        # Aktiviere den neuen Prompt
        prompt.status = PromptStatus.ACTIVE
        prompt.updated_at = datetime.now()
        self._save_prompt(prompt)
        
        print(f"Prompt {prompt.template_name} Version {prompt.version} aktiviert")
        return True
    
    def render_prompt(
        self,
        template_name: str,
        variables: Dict[str, str],
        prompt_id: Optional[str] = None
    ) -> str:
        """Rendert einen Prompt mit gegebenen Variablen"""
        
        # Hole den zu verwendenden Prompt
        if prompt_id:
            prompt = self.get_prompt(prompt_id)
        else:
            prompt = self.get_active_prompt(template_name)
        
        if not prompt:
            # Fallback auf Standard-Template
            template_config = get_prompt_template(template_name)
            if not template_config:
                raise ValueError(f"Kein Prompt für Template {template_name} gefunden")
            
            return template_config["template"].format(**variables)
        
        # Validiere Variablen
        missing_vars = set(prompt.variables) - set(variables.keys())
        if missing_vars:
            raise ValueError(f"Fehlende Variablen: {missing_vars}")
        
        # Rendere Prompt
        try:
            rendered_prompt = prompt.template.format(**variables)
            return rendered_prompt
        except KeyError as e:
            raise ValueError(f"Ungültige Variable im Template: {e}")
    
    def start_ab_test(
        self,
        template_name: str,
        prompt_id_a: str,
        prompt_id_b: str,
        traffic_split: float = 0.5
    ) -> bool:
        """Startet einen A/B Test zwischen zwei Prompts"""
        
        if not settings.ab_test_enabled:
            print("A/B Testing ist deaktiviert")
            return False
        
        prompt_a = self.get_prompt(prompt_id_a)
        prompt_b = self.get_prompt(prompt_id_b)
        
        if not prompt_a or not prompt_b:
            print("Einer oder beide Prompts nicht gefunden")
            return False
        
        # Setze beide Prompts auf Testing-Status
        prompt_a.status = PromptStatus.TESTING
        prompt_b.status = PromptStatus.TESTING
        prompt_a.updated_at = datetime.now()
        prompt_b.updated_at = datetime.now()
        
        self._save_prompt(prompt_a)
        self._save_prompt(prompt_b)
        
        # Speichere A/B Test Konfiguration
        ab_test_config = {
            "template_name": template_name,
            "prompt_a": prompt_id_a,
            "prompt_b": prompt_id_b,
            "traffic_split": traffic_split,
            "started_at": datetime.now().isoformat(),
            "active": True
        }
        
        self.redis_client.setex(
            f"ab_test:{template_name}",
            86400,  # 24 Stunden
            json.dumps(ab_test_config)
        )
        
        print(f"A/B Test für {template_name} gestartet")
        return True
    
    def get_ab_test_prompt(
        self,
        template_name: str,
        user_id: Optional[str] = None
    ) -> Optional[PromptVersion]:
        """Holt einen Prompt für A/B Testing"""
        
        # Prüfe ob A/B Test aktiv ist
        ab_test_data = self.redis_client.get(f"ab_test:{template_name}")
        if not ab_test_data:
            return self.get_active_prompt(template_name)
        
        ab_test_config = json.loads(ab_test_data)
        if not ab_test_config.get("active", False):
            return self.get_active_prompt(template_name)
        
        # Bestimme welche Version verwendet werden soll
        if user_id:
            # Konsistente Zuweisung basierend auf User ID
            user_hash = hash(user_id) % 100
            use_version_b = user_hash < (ab_test_config["traffic_split"] * 100)
        else:
            # Zufällige Zuweisung
            use_version_b = random.random() < ab_test_config["traffic_split"]
        
        prompt_id = ab_test_config["prompt_b"] if use_version_b else ab_test_config["prompt_a"]
        return self.get_prompt(prompt_id)
    
    def update_prompt_metrics(
        self,
        prompt_id: str,
        metrics: Dict[str, float]
    ) -> bool:
        """Aktualisiert Metriken für einen Prompt"""
        
        if prompt_id not in self.prompts:
            return False
        
        prompt = self.prompts[prompt_id]
        prompt.performance_metrics.update(metrics)
        prompt.updated_at = datetime.now()
        
        self._save_prompt(prompt)
        return True
    
    def list_prompts(
        self,
        template_name: Optional[str] = None,
        status: Optional[PromptStatus] = None
    ) -> List[PromptVersion]:
        """Listet Prompts mit optionalen Filtern"""
        
        prompts = list(self.prompts.values())
        
        if template_name:
            prompts = [p for p in prompts if p.template_name == template_name]
        
        if status:
            prompts = [p for p in prompts if p.status == status]
        
        return sorted(prompts, key=lambda p: p.updated_at, reverse=True)
    
    def delete_prompt(self, prompt_id: str) -> bool:
        """Löscht einen Prompt"""
        
        if prompt_id not in self.prompts:
            return False
        
        # Lösche aus Redis
        self.redis_client.delete(f"prompt:{prompt_id}")
        
        # Lösche aus lokalem Cache
        del self.prompts[prompt_id]
        
        print(f"Prompt {prompt_id} gelöscht")
        return True


# Global prompt manager instance
prompt_manager = PromptManager()
