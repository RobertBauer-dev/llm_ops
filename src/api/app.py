"""
FastAPI-Anwendung für LLM-Ops mit Prometheus-Metriken
"""

import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import time
import structlog

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from src.models.model_manager import model_manager
from src.prompts.prompt_manager import prompt_manager
from src.monitoring.monitor import llm_monitor
from src.evaluation.evaluator import model_evaluator

# Konfiguriere Logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# FastAPI App
app = FastAPI(
    title="LLM-Ops API",
    description="API für LLM-Operations mit Monitoring",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metriken
REQUEST_COUNT = Counter(
    'llm_ops_requests_total',
    'Total number of LLM-Ops API requests',
    ['endpoint', 'method', 'status']
)

REQUEST_DURATION = Histogram(
    'llm_ops_request_duration_seconds',
    'LLM-Ops API request duration in seconds',
    ['endpoint', 'method']
)

ACTIVE_MODELS = Gauge(
    'llm_ops_active_models',
    'Number of active models in registry'
)

ACTIVE_PROMPTS = Gauge(
    'llm_ops_active_prompts',
    'Number of active prompts'
)

# Pydantic Models
class LLMRequest(BaseModel):
    model_name: str
    model_version: Optional[str] = None
    prompt: str
    user_id: Optional[str] = None
    prompt_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class LLMResponse(BaseModel):
    request_id: str
    response: str
    model_name: str
    model_version: str
    latency_ms: float
    cost_usd: float
    input_tokens: int
    output_tokens: int

class ModelRegistration(BaseModel):
    name: str
    provider: str
    parameters: Dict[str, Any]
    description: Optional[str] = None

class PromptCreation(BaseModel):
    template_name: str
    template: str
    variables: list[str]
    description: Optional[str] = None
    tags: Optional[list[str]] = None

# Middleware für Metriken
@app.middleware("http")
async def add_metrics_middleware(request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_DURATION.labels(
        endpoint=request.url.path,
        method=request.method
    ).observe(duration)
    
    REQUEST_COUNT.labels(
        endpoint=request.url.path,
        method=request.method,
        status=response.status_code
    ).inc()
    
    return response

# Prometheus Metrics Endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus Metriken Endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Health Check
@app.get("/health")
async def health_check():
    """Health Check Endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "model_manager": "active",
            "prompt_manager": "active",
            "monitor": "active"
        }
    }

# LLM Request Endpoint
@app.post("/llm/request", response_model=LLMResponse)
async def llm_request(request_data: LLMRequest):
    """Verarbeitet eine LLM-Anfrage mit vollständigem Monitoring"""
    
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Hole Modell
        model = model_manager.get_model(
            request_data.model_name,
            request_data.model_version
        )
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Hole Prompt (falls prompt_id angegeben)
        prompt_template = request_data.prompt
        if request_data.prompt_id:
            prompt = prompt_manager.get_prompt(request_data.prompt_id)
            if prompt:
                prompt_template = prompt.template
        
        # Simuliere LLM-Antwort (in echtem System würde hier der LLM-Call stehen)
        response_text = f"Simulierte Antwort für: {request_data.prompt[:50]}..."
        
        # Berechne Latenz
        latency_ms = (time.time() - start_time) * 1000
        
        # Logge Request mit Monitoring
        llm_request = llm_monitor.log_request(
            request_id=request_id,
            model_name=request_data.model_name,
            model_version=model.version,
            prompt=request_data.prompt,
            response=response_text,
            latency_ms=latency_ms,
            success=True,
            prompt_id=request_data.prompt_id,
            user_id=request_data.user_id,
            metadata=request_data.metadata
        )
        
        # Update Prometheus Metriken
        ACTIVE_MODELS.set(len(model_manager.list_models()))
        ACTIVE_PROMPTS.set(len(prompt_manager.list_prompts()))
        
        return LLMResponse(
            request_id=request_id,
            response=response_text,
            model_name=request_data.model_name,
            model_version=model.version,
            latency_ms=latency_ms,
            cost_usd=llm_request.cost_usd,
            input_tokens=llm_request.input_tokens,
            output_tokens=llm_request.output_tokens
        )
        
    except Exception as e:
        # Logge Fehler
        llm_monitor.log_request(
            request_id=request_id,
            model_name=request_data.model_name,
            model_version=request_data.model_version or "unknown",
            prompt=request_data.prompt,
            response="",
            latency_ms=(time.time() - start_time) * 1000,
            success=False,
            error_message=str(e),
            prompt_id=request_data.prompt_id,
            user_id=request_data.user_id
        )
        raise HTTPException(status_code=500, detail=str(e))

# Model Management Endpoints
@app.post("/models/register")
async def register_model(model_data: ModelRegistration):
    """Registriert ein neues Modell"""
    try:
        version = model_manager.register_model(
            name=model_data.name,
            provider=model_data.provider,
            parameters=model_data.parameters,
            description=model_data.description
        )
        
        ACTIVE_MODELS.set(len(model_manager.list_models()))
        
        return {
            "message": "Model registered successfully",
            "model_name": model_data.name,
            "version": version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """Listet alle registrierten Modelle"""
    models = model_manager.list_models()
    return {
        "models": [
            {
                "name": model.name,
                "version": model.version,
                "provider": model.provider,
                "status": model.status,
                "created_at": model.created_at.isoformat()
            }
            for model in models
        ]
    }

# Prompt Management Endpoints
@app.post("/prompts/create")
async def create_prompt(prompt_data: PromptCreation):
    """Erstellt einen neuen Prompt"""
    try:
        prompt_id = prompt_manager.create_prompt(
            template_name=prompt_data.template_name,
            template=prompt_data.template,
            variables=prompt_data.variables,
            description=prompt_data.description,
            tags=prompt_data.tags
        )
        
        ACTIVE_PROMPTS.set(len(prompt_manager.list_prompts()))
        
        return {
            "message": "Prompt created successfully",
            "prompt_id": prompt_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prompts")
async def list_prompts():
    """Listet alle Prompts"""
    prompts = prompt_manager.list_prompts()
    return {
        "prompts": [
            {
                "id": prompt.id,
                "template_name": prompt.template_name,
                "version": prompt.version,
                "status": prompt.status,
                "created_at": prompt.created_at.isoformat()
            }
            for prompt in prompts
        ]
    }

# Monitoring Endpoints
@app.get("/monitoring/metrics")
async def get_metrics():
    """Holt aktuelle Metriken"""
    try:
        cost_metrics = llm_monitor.get_cost_metrics()
        performance_metrics = llm_monitor.get_performance_metrics()
        error_summary = llm_monitor.get_error_summary()
        
        return {
            "cost_metrics": {
                "total_cost_usd": cost_metrics.total_cost_usd,
                "cost_per_request": cost_metrics.cost_per_request,
                "requests_count": cost_metrics.requests_count
            },
            "performance_metrics": performance_metrics,
            "error_summary": error_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/alerts")
async def get_alerts():
    """Holt aktuelle Alerts"""
    try:
        alerts = llm_monitor.check_cost_alerts()
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
