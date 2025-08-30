"""
Monitoring System für LLM-Ops
Überwacht Performance, Kosten und Fehler
"""

import time
import json
import tiktoken
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from config.settings import settings


class MetricType(str, Enum):
    """Typen von Metriken"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class LLMRequest:
    """Repräsentiert eine LLM-Anfrage"""
    request_id: str
    model_name: str
    model_version: str
    prompt_id: Optional[str]
    user_id: Optional[str]
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class CostMetrics:
    """Kosten-Metriken"""
    total_cost_usd: float
    cost_per_request: float
    cost_per_token: float
    requests_count: int
    tokens_count: int
    period_start: datetime
    period_end: datetime


class LLMMonitor:
    """Zentrale Monitoring-Klasse für LLM-Operationen"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url)
        self.logger = structlog.get_logger()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 Tokenizer
        
        # Prometheus Metriken
        self.request_counter = Counter(
            'llm_requests_total',
            'Total number of LLM requests',
            ['model', 'status', 'prompt_id']
        )
        
        self.latency_histogram = Histogram(
            'llm_request_duration_seconds',
            'LLM request latency in seconds',
            ['model', 'prompt_id']
        )
        
        self.token_counter = Counter(
            'llm_tokens_total',
            'Total number of tokens processed',
            ['model', 'token_type']
        )
        
        self.cost_gauge = Gauge(
            'llm_cost_usd',
            'Total cost in USD',
            ['model', 'period']
        )
        
        # Starte Prometheus Server
        if settings.environment.value != "development":
            start_http_server(settings.prometheus_port)
    
    def count_tokens(self, text: str) -> int:
        """Zählt Tokens in einem Text"""
        return len(self.tokenizer.encode(text))
    
    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Berechnet die Kosten für eine Anfrage"""
        from config.settings import get_model_config
        
        model_config = get_model_config(model_name)
        cost_per_1k = model_config.get("cost_per_1k_tokens", 0.0)
        
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * cost_per_1k
    
    def log_request(
        self,
        request_id: str,
        model_name: str,
        model_version: str,
        prompt: str,
        response: str,
        latency_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        prompt_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Loggt eine LLM-Anfrage"""
        
        # Token-Zählung
        input_tokens = self.count_tokens(prompt)
        output_tokens = self.count_tokens(response) if response else 0
        
        # Kosten-Berechnung
        cost_usd = self.calculate_cost(model_name, input_tokens, output_tokens)
        
        # Erstelle Request-Objekt
        request = LLMRequest(
            request_id=request_id,
            model_name=model_name,
            model_version=model_version,
            prompt_id=prompt_id,
            user_id=user_id,
            timestamp=datetime.now(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        # Speichere in Redis
        self._save_request(request)
        
        # Update Prometheus Metriken
        self._update_prometheus_metrics(request)
        
        # Logge Request
        self.logger.info(
            "LLM request processed",
            request_id=request_id,
            model=model_name,
            version=model_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success
        )
        
        return request
    
    def _save_request(self, request: LLMRequest):
        """Speichert eine Request in Redis"""
        try:
            # Speichere Request-Details
            request_key = f"request:{request.request_id}"
            self.redis_client.setex(
                request_key,
                86400,  # 24 Stunden
                json.dumps(asdict(request), default=str)
            )
            
            # Speichere für Aggregation
            date_key = f"requests:{request.timestamp.strftime('%Y-%m-%d')}"
            self.redis_client.lpush(date_key, request.request_id)
            self.redis_client.expire(date_key, 2592000)  # 30 Tage
            
            # Speichere für Model-spezifische Aggregation
            model_key = f"model_requests:{request.model_name}:{request.timestamp.strftime('%Y-%m-%d')}"
            self.redis_client.lpush(model_key, request.request_id)
            self.redis_client.expire(model_key, 2592000)  # 30 Tage
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern der Request: {e}")
    
    def _update_prometheus_metrics(self, request: LLMRequest):
        """Aktualisiert Prometheus Metriken"""
        try:
            # Request Counter
            status = "success" if request.success else "error"
            self.request_counter.labels(
                model=request.model_name,
                status=status,
                prompt_id=request.prompt_id or "unknown"
            ).inc()
            
            # Latency Histogram
            self.latency_histogram.labels(
                model=request.model_name,
                prompt_id=request.prompt_id or "unknown"
            ).observe(request.latency_ms / 1000)  # Konvertiere zu Sekunden
            
            # Token Counter
            self.token_counter.labels(
                model=request.model_name,
                token_type="input"
            ).inc(request.input_tokens)
            
            self.token_counter.labels(
                model=request.model_name,
                token_type="output"
            ).inc(request.output_tokens)
            
            # Cost Gauge (tägliche Kosten)
            self.cost_gauge.labels(
                model=request.model_name,
                period="daily"
            ).inc(request.cost_usd)
            
        except Exception as e:
            self.logger.error(f"Fehler beim Update der Prometheus Metriken: {e}")
    
    def get_cost_metrics(
        self,
        model_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CostMetrics:
        """Holt Kosten-Metriken für einen Zeitraum"""
        
        if not start_date:
            start_date = datetime.now() - timedelta(days=1)
        if not end_date:
            end_date = datetime.now()
        
        total_cost = 0.0
        total_requests = 0
        total_tokens = 0
        
        current_date = start_date
        while current_date <= end_date:
            date_key = f"requests:{current_date.strftime('%Y-%m-%d')}"
            
            if model_name:
                date_key = f"model_requests:{model_name}:{current_date.strftime('%Y-%m-%d')}"
            
            request_ids = self.redis_client.lrange(date_key, 0, -1)
            
            for request_id in request_ids:
                request_data = self.redis_client.get(f"request:{request_id.decode()}")
                if request_data:
                    request_dict = json.loads(request_data)
                    total_cost += request_dict.get("cost_usd", 0.0)
                    total_requests += 1
                    total_tokens += request_dict.get("input_tokens", 0) + request_dict.get("output_tokens", 0)
            
            current_date += timedelta(days=1)
        
        return CostMetrics(
            total_cost_usd=total_cost,
            cost_per_request=total_cost / total_requests if total_requests > 0 else 0.0,
            cost_per_token=total_cost / total_tokens if total_tokens > 0 else 0.0,
            requests_count=total_requests,
            tokens_count=total_tokens,
            period_start=start_date,
            period_end=end_date
        )
    
    def get_performance_metrics(
        self,
        model_name: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Holt Performance-Metriken"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        requests = []
        current_date = start_time
        
        while current_date <= end_time:
            date_key = f"requests:{current_date.strftime('%Y-%m-%d')}"
            
            if model_name:
                date_key = f"model_requests:{model_name}:{current_date.strftime('%Y-%m-%d')}"
            
            request_ids = self.redis_client.lrange(date_key, 0, -1)
            
            for request_id in request_ids:
                request_data = self.redis_client.get(f"request:{request_id.decode()}")
                if request_data:
                    request_dict = json.loads(request_data)
                    request_time = datetime.fromisoformat(request_dict["timestamp"])
                    
                    if start_time <= request_time <= end_time:
                        requests.append(request_dict)
            
            current_date += timedelta(days=1)
        
        if not requests:
            return {
                "avg_latency_ms": 0.0,
                "success_rate": 0.0,
                "requests_per_hour": 0.0,
                "total_requests": 0
            }
        
        # Berechne Metriken
        latencies = [r["latency_ms"] for r in requests]
        successes = [r["success"] for r in requests]
        
        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "success_rate": sum(successes) / len(successes),
            "requests_per_hour": len(requests) / hours,
            "total_requests": len(requests),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)]
        }
    
    def check_cost_alerts(self) -> List[Dict[str, Any]]:
        """Prüft auf Kosten-Alerts"""
        alerts = []
        
        # Prüfe tägliche Kosten
        daily_metrics = self.get_cost_metrics(
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        if daily_metrics.total_cost_usd > settings.cost_alert_threshold:
            alerts.append({
                "type": "cost_alert",
                "message": f"Tägliche Kosten ({daily_metrics.total_cost_usd:.2f} USD) über Schwellenwert ({settings.cost_alert_threshold} USD)",
                "severity": "high",
                "timestamp": datetime.now()
            })
        
        return alerts
    
    def get_error_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Holt eine Zusammenfassung der Fehler"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        errors = []
        current_date = start_time
        
        while current_date <= end_time:
            date_key = f"requests:{current_date.strftime('%Y-%m-%d')}"
            request_ids = self.redis_client.lrange(date_key, 0, -1)
            
            for request_id in request_ids:
                request_data = self.redis_client.get(f"request:{request_id.decode()}")
                if request_data:
                    request_dict = json.loads(request_data)
                    request_time = datetime.fromisoformat(request_dict["timestamp"])
                    
                    if (start_time <= request_time <= end_time and 
                        not request_dict.get("success", True)):
                        errors.append(request_dict)
            
            current_date += timedelta(days=1)
        
        error_types = {}
        for error in errors:
            error_msg = error.get("error_message", "Unknown error")
            error_types[error_msg] = error_types.get(error_msg, 0) + 1
        
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "error_rate": len(errors) / max(1, len(errors) + 100)  # Schätzung
        }


# Global monitor instance
llm_monitor = LLMMonitor()
