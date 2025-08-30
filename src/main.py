"""
Hauptanwendung für LLM-Ops Beispielprojekt
Demonstriert alle Konzepte in der Praxis
"""

import time
import uuid
from typing import Dict, Any
from datetime import datetime

from config.settings import settings, ModelProvider
from src.models.model_manager import model_manager
from src.prompts.prompt_manager import prompt_manager
from src.monitoring.monitor import llm_monitor
from src.evaluation.evaluator import model_evaluator


class LLMOpsDemo:
    """Demonstrationsklasse für LLM-Ops Konzepte"""
    
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def run_complete_demo(self):
        """Führt eine vollständige LLM-Ops Demonstration durch"""
        
        print("🚀 LLM-Ops Beispielprojekt - Vollständige Demonstration")
        print("=" * 60)
        
        # 1. Model Management Demo
        print("\n📊 1. MODEL MANAGEMENT")
        print("-" * 30)
        self._demo_model_management()
        
        # 2. Prompt Engineering Demo
        print("\n🎯 2. PROMPT ENGINEERING")
        print("-" * 30)
        self._demo_prompt_engineering()
        
        # 3. A/B Testing Demo
        print("\n🔬 3. A/B TESTING")
        print("-" * 30)
        self._demo_ab_testing()
        
        # 4. Monitoring Demo
        print("\n📈 4. MONITORING & OBSERVABILITY")
        print("-" * 30)
        self._demo_monitoring()
        
        # 5. Evaluation Demo
        print("\n🧪 5. MODEL EVALUATION")
        print("-" * 30)
        self._demo_evaluation()
        
        # 6. Cost Management Demo
        print("\n💰 6. COST MANAGEMENT")
        print("-" * 30)
        self._demo_cost_management()
        
        print("\n✅ Demonstration abgeschlossen!")
    
    def _demo_model_management(self):
        """Demonstriert Model Management"""
        
        print("Registriere verschiedene Modelle...")
        
        # Registriere GPT-4
        gpt4_version = model_manager.register_model(
            name="gpt-4",
            provider=ModelProvider.OPENAI,
            parameters={
                "temperature": 0.7,
                "max_tokens": 4096,
                "model": "gpt-4"
            },
            description="GPT-4 für komplexe Aufgaben"
        )
        
        # Registriere GPT-3.5
        gpt35_version = model_manager.register_model(
            name="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            parameters={
                "temperature": 0.7,
                "max_tokens": 2048,
                "model": "gpt-3.5-turbo"
            },
            description="GPT-3.5 für einfache Aufgaben"
        )
        
        # Registriere Claude
        claude_version = model_manager.register_model(
            name="claude-3-sonnet",
            provider=ModelProvider.ANTHROPIC,
            parameters={
                "temperature": 0.7,
                "max_tokens": 4096,
                "model": "claude-3-sonnet"
            },
            description="Claude für kreative Aufgaben"
        )
        
        # Deploye ein Modell
        model_manager.deploy_model("gpt-4", gpt4_version)
        
        # Zeige alle Modelle
        models = model_manager.list_models()
        print(f"Registrierte Modelle: {len(models)}")
        for model in models:
            print(f"  - {model.name} v{model.version} ({model.status.value})")
    
    def _demo_prompt_engineering(self):
        """Demonstriert Prompt Engineering"""
        
        print("Erstelle verschiedene Prompt-Versionen...")
        
        # Erstelle Chatbot-Prompts
        chat_prompt_v1 = prompt_manager.create_prompt(
            template_name="chatbot",
            template="""
Du bist ein hilfreicher Assistent. Antworte auf Deutsch und sei freundlich.

Frage: {question}

Antwort:""",
            variables=["question"],
            description="Einfacher Chatbot-Prompt v1"
        )
        
        chat_prompt_v2 = prompt_manager.create_prompt(
            template_name="chatbot",
            template="""
Du bist ein professioneller Assistent mit umfangreichem Wissen. 
Antworte auf Deutsch, sei freundlich und gib detaillierte, hilfreiche Antworten.

Kontext: {context}
Frage: {question}

Antwort:""",
            variables=["context", "question"],
            description="Verbesserter Chatbot-Prompt v2"
        )
        
        # Aktiviere den neueren Prompt
        prompt_manager.activate_prompt(chat_prompt_v2)
        
        # Teste Prompt-Rendering
        test_vars = {
            "context": "Der Benutzer ist neu hier",
            "question": "Wie kann ich dir helfen?"
        }
        
        rendered_prompt = prompt_manager.render_prompt("chatbot", test_vars)
        print(f"Gerenderter Prompt:\n{rendered_prompt[:200]}...")
        
        # Zeige alle Prompts
        prompts = prompt_manager.list_prompts(template_name="chatbot")
        print(f"Chatbot-Prompts: {len(prompts)}")
        for prompt in prompts:
            print(f"  - {prompt.template_name} v{prompt.version} ({prompt.status.value})")
    
    def _demo_ab_testing(self):
        """Demonstriert A/B Testing"""
        
        print("Starte A/B Test zwischen Prompt-Versionen...")
        
        # Erstelle zwei verschiedene Prompts für A/B Testing
        prompt_a = prompt_manager.create_prompt(
            template_name="ab_test",
            template="Antworte kurz und prägnant: {question}",
            variables=["question"],
            description="Kurze Antworten"
        )
        
        prompt_b = prompt_manager.create_prompt(
            template_name="ab_test",
            template="Gib eine ausführliche und detaillierte Antwort: {question}",
            variables=["question"],
            description="Ausführliche Antworten"
        )
        
        # Starte A/B Test
        prompt_manager.start_ab_test("ab_test", prompt_a, prompt_b, traffic_split=0.5)
        
        # Simuliere Requests mit verschiedenen User IDs
        test_question = "Was ist Machine Learning?"
        
        for i in range(10):
            user_id = f"user_{i}"
            prompt = prompt_manager.get_ab_test_prompt("ab_test", user_id)
            
            if prompt:
                print(f"User {user_id}: Prompt Version {prompt.version}")
        
        print("A/B Test läuft - Prompts werden basierend auf User ID zugewiesen")
    
    def _demo_monitoring(self):
        """Demonstriert Monitoring und Observability"""
        
        print("Simuliere LLM-Requests und überwache Performance...")
        
        # Simuliere verschiedene Requests
        test_requests = [
            {
                "prompt": "Erkläre mir Machine Learning",
                "model": "gpt-4",
                "version": "latest"
            },
            {
                "prompt": "Was ist Python?",
                "model": "gpt-3.5-turbo",
                "version": "latest"
            },
            {
                "prompt": "Schreibe eine Kurzgeschichte",
                "model": "claude-3-sonnet",
                "version": "latest"
            }
        ]
        
        for i, request_data in enumerate(test_requests):
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            
            # Simuliere LLM-Antwort
            start_time = time.time()
            response = f"Simulierte Antwort für: {request_data['prompt']}"
            latency_ms = (time.time() - start_time) * 1000 + 500  # Simuliere Latenz
            
            # Logge Request
            llm_monitor.log_request(
                request_id=request_id,
                model_name=request_data["model"],
                model_version=request_data["version"],
                prompt=request_data["prompt"],
                response=response,
                latency_ms=latency_ms,
                success=True,
                user_id=f"demo_user_{i}"
            )
            
            print(f"Request {i+1} geloggt: {request_data['model']} ({latency_ms:.0f}ms)")
        
        # Zeige Monitoring-Metriken
        performance_metrics = llm_monitor.get_performance_metrics(hours=1)
        print(f"\nPerformance-Metriken (letzte Stunde):")
        print(f"  - Durchschnittliche Latenz: {performance_metrics['avg_latency_ms']:.0f}ms")
        print(f"  - Erfolgsrate: {performance_metrics['success_rate']:.1%}")
        print(f"  - Requests pro Stunde: {performance_metrics['requests_per_hour']:.1f}")
    
    def _demo_evaluation(self):
        """Demonstriert Model Evaluation"""
        
        print("Führe Model-Evaluation durch...")
        
        # Teste Prompt-Template
        test_prompt_template = """
Du bist ein hilfreicher Assistent. Antworte auf Deutsch.

Frage: {question}

Antwort:"""
        
        # Evaluations-Testfälle
        test_cases = [
            {
                "id": "eval_001",
                "input_data": {"question": "Was ist Python?"},
                "expected_output": "Programmiersprache",
                "category": "basic_qa"
            },
            {
                "id": "eval_002", 
                "input_data": {"question": "Erkläre Machine Learning"},
                "expected_output": "künstliche Intelligenz",
                "category": "technical_qa"
            }
        ]
        
        # Füge Testfälle hinzu
        for test_case in test_cases:
            from src.evaluation.evaluator import TestCase
            tc = TestCase(**test_case)
            model_evaluator.add_test_case(tc)
        
        # Führe Evaluation durch
        evaluation_id = model_evaluator.evaluate_model(
            model_name="gpt-4",
            model_version="latest",
            prompt_template=test_prompt_template
        )
        
        print(f"Evaluation abgeschlossen: {evaluation_id}")
        
        # Vergleiche Modelle
        comparison = model_evaluator.compare_models(
            model1_name="gpt-4",
            model1_version="latest",
            model2_name="gpt-3.5-turbo", 
            model2_version="latest",
            prompt_template=test_prompt_template
        )
        
        print(f"\nModell-Vergleich:")
        print(f"  GPT-4 Accuracy: {comparison['model1']['avg_accuracy']:.2f}")
        print(f"  GPT-3.5 Accuracy: {comparison['model2']['avg_accuracy']:.2f}")
        print(f"  Unterschied: {comparison['differences']['accuracy_diff']:.2f}")
    
    def _demo_cost_management(self):
        """Demonstriert Cost Management"""
        
        print("Analysiere Kosten und erstelle Alerts...")
        
        # Hole Kosten-Metriken
        cost_metrics = llm_monitor.get_cost_metrics()
        
        print(f"Kosten-Metriken (letzte 24h):")
        print(f"  - Gesamtkosten: ${cost_metrics.total_cost_usd:.4f}")
        print(f"  - Kosten pro Request: ${cost_metrics.cost_per_request:.4f}")
        print(f"  - Kosten pro Token: ${cost_metrics.cost_per_token:.6f}")
        print(f"  - Anzahl Requests: {cost_metrics.requests_count}")
        print(f"  - Anzahl Tokens: {cost_metrics.tokens_count}")
        
        # Prüfe Alerts
        alerts = llm_monitor.check_cost_alerts()
        if alerts:
            print(f"\n⚠️  Kosten-Alerts:")
            for alert in alerts:
                print(f"  - {alert['message']}")
        else:
            print(f"\n✅ Keine Kosten-Alerts - Budget im Rahmen")
        
        # Zeige Error-Summary
        error_summary = llm_monitor.get_error_summary(hours=24)
        print(f"\nFehler-Zusammenfassung (letzte 24h):")
        print(f"  - Gesamtfehler: {error_summary['total_errors']}")
        print(f"  - Fehlerrate: {error_summary['error_rate']:.1%}")
        
        if error_summary['error_types']:
            print(f"  - Fehlertypen:")
            for error_type, count in error_summary['error_types'].items():
                print(f"    * {error_type}: {count}")


def main():
    """Hauptfunktion"""
    
    # Konfiguriere Logging
    import structlog
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
    
    # Starte Demo
    demo = LLMOpsDemo()
    demo.run_complete_demo()


if __name__ == "__main__":
    main()
