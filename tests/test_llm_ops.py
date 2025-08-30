"""
Tests für das LLM-Ops System
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from config.settings import settings, ModelProvider
from src.models.model_manager import model_manager, ModelStatus
from src.prompts.prompt_manager import prompt_manager, PromptStatus
from src.monitoring.monitor import llm_monitor
from src.evaluation.evaluator import model_evaluator, TestCase


class TestModelManager:
    """Tests für Model Management"""
    
    def test_register_model(self):
        """Test für Model-Registrierung"""
        version = model_manager.register_model(
            name="test-model",
            provider=ModelProvider.OPENAI,
            parameters={"temperature": 0.5},
            description="Test Model"
        )
        
        assert version is not None
        assert len(version) > 0
        
        # Prüfe ob Modell in der Liste ist
        models = model_manager.list_models()
        test_models = [m for m in models if m.name == "test-model"]
        assert len(test_models) > 0
    
    def test_deploy_model(self):
        """Test für Model-Deployment"""
        # Registriere ein Test-Modell
        version = model_manager.register_model(
            name="deploy-test",
            provider=ModelProvider.OPENAI,
            parameters={"temperature": 0.7}
        )
        
        # Deploye das Modell
        success = model_manager.deploy_model("deploy-test", version)
        assert success is True
        
        # Prüfe Status
        model = model_manager.get_model("deploy-test", version)
        assert model.status == ModelStatus.DEPLOYED
    
    def test_model_comparison(self):
        """Test für Modell-Vergleich"""
        # Registriere zwei Modelle
        version1 = model_manager.register_model(
            name="compare-1",
            provider=ModelProvider.OPENAI,
            parameters={"temperature": 0.5}
        )
        
        version2 = model_manager.register_model(
            name="compare-2",
            provider=ModelProvider.ANTHROPIC,
            parameters={"temperature": 0.7}
        )
        
        # Vergleiche Modelle
        comparison = model_manager.compare_models(
            "compare-1", version1,
            "compare-2", version2
        )
        
        assert "model1" in comparison
        assert "model2" in comparison
        assert "cost_difference" in comparison


class TestPromptManager:
    """Tests für Prompt Management"""
    
    def test_create_prompt(self):
        """Test für Prompt-Erstellung"""
        prompt_id = prompt_manager.create_prompt(
            template_name="test-template",
            template="Hallo {name}, wie geht es dir?",
            variables=["name"],
            description="Test Prompt"
        )
        
        assert prompt_id is not None
        
        # Prüfe ob Prompt existiert
        prompt = prompt_manager.get_prompt(prompt_id)
        assert prompt is not None
        assert prompt.template_name == "test-template"
    
    def test_render_prompt(self):
        """Test für Prompt-Rendering"""
        # Erstelle einen Prompt
        prompt_id = prompt_manager.create_prompt(
            template_name="render-test",
            template="Hallo {name}, du bist {age} Jahre alt.",
            variables=["name", "age"]
        )
        
        # Rendere Prompt
        variables = {"name": "Max", "age": "25"}
        rendered = prompt_manager.render_prompt("render-test", variables, prompt_id)
        
        assert "Hallo Max, du bist 25 Jahre alt." in rendered
    
    def test_activate_prompt(self):
        """Test für Prompt-Aktivierung"""
        # Erstelle zwei Prompts
        prompt1 = prompt_manager.create_prompt(
            template_name="activate-test",
            template="Version 1",
            variables=[]
        )
        
        prompt2 = prompt_manager.create_prompt(
            template_name="activate-test",
            template="Version 2",
            variables=[]
        )
        
        # Aktiviere zweiten Prompt
        success = prompt_manager.activate_prompt(prompt2)
        assert success is True
        
        # Prüfe Status
        active_prompt = prompt_manager.get_active_prompt("activate-test")
        assert active_prompt.id == prompt2
    
    def test_ab_testing(self):
        """Test für A/B Testing"""
        # Erstelle zwei Prompts für A/B Test
        prompt_a = prompt_manager.create_prompt(
            template_name="ab-test",
            template="Kurze Antwort: {question}",
            variables=["question"]
        )
        
        prompt_b = prompt_manager.create_prompt(
            template_name="ab-test",
            template="Lange Antwort: {question}",
            variables=["question"]
        )
        
        # Starte A/B Test
        success = prompt_manager.start_ab_test("ab-test", prompt_a, prompt_b, 0.5)
        assert success is True
        
        # Teste A/B Test Prompt-Auswahl
        prompt = prompt_manager.get_ab_test_prompt("ab-test", "user123")
        assert prompt is not None


class TestMonitoring:
    """Tests für Monitoring"""
    
    def test_log_request(self):
        """Test für Request-Logging"""
        request_id = "test-request-123"
        
        # Logge Request
        request = llm_monitor.log_request(
            request_id=request_id,
            model_name="gpt-4",
            model_version="latest",
            prompt="Test prompt",
            response="Test response",
            latency_ms=1000,
            success=True
        )
        
        assert request.request_id == request_id
        assert request.model_name == "gpt-4"
        assert request.success is True
    
    def test_cost_calculation(self):
        """Test für Kosten-Berechnung"""
        cost = llm_monitor.calculate_cost("gpt-4", 100, 50)
        assert cost > 0
        
        # Teste verschiedene Modelle
        cost_gpt35 = llm_monitor.calculate_cost("gpt-3.5-turbo", 100, 50)
        cost_claude = llm_monitor.calculate_cost("claude-3-sonnet", 100, 50)
        
        # Kosten sollten unterschiedlich sein
        assert cost != cost_gpt35 or cost != cost_claude
    
    def test_performance_metrics(self):
        """Test für Performance-Metriken"""
        # Logge einige Test-Requests
        for i in range(5):
            llm_monitor.log_request(
                request_id=f"perf-test-{i}",
                model_name="gpt-4",
                model_version="latest",
                prompt=f"Test prompt {i}",
                response=f"Test response {i}",
                latency_ms=1000 + i * 100,
                success=True
            )
        
        # Hole Performance-Metriken
        metrics = llm_monitor.get_performance_metrics(hours=1)
        
        assert "avg_latency_ms" in metrics
        assert "success_rate" in metrics
        assert "requests_per_hour" in metrics
        assert metrics["total_requests"] >= 5
    
    def test_cost_metrics(self):
        """Test für Kosten-Metriken"""
        # Logge einige Requests
        for i in range(3):
            llm_monitor.log_request(
                request_id=f"cost-test-{i}",
                model_name="gpt-4",
                model_version="latest",
                prompt=f"Test prompt {i}",
                response=f"Test response {i}",
                latency_ms=1000,
                success=True
            )
        
        # Hole Kosten-Metriken
        cost_metrics = llm_monitor.get_cost_metrics()
        
        assert cost_metrics.total_cost_usd >= 0
        assert cost_metrics.requests_count >= 3
        assert cost_metrics.cost_per_request >= 0


class TestEvaluation:
    """Tests für Evaluation"""
    
    def test_add_test_case(self):
        """Test für Testfall-Hinzufügung"""
        test_case = TestCase(
            id="test-case-001",
            input_data={"question": "Was ist Python?"},
            expected_output="Programmiersprache",
            category="basic_qa"
        )
        
        model_evaluator.add_test_case(test_case)
        
        # Prüfe ob Testfall existiert
        assert test_case.id in model_evaluator.test_cases
    
    def test_evaluate_model(self):
        """Test für Model-Evaluation"""
        # Füge Testfall hinzu
        test_case = TestCase(
            id="eval-test-001",
            input_data={"question": "Was ist ML?"},
            expected_output="Machine Learning",
            category="technical"
        )
        model_evaluator.add_test_case(test_case)
        
        # Führe Evaluation durch
        evaluation_id = model_evaluator.evaluate_model(
            model_name="gpt-4",
            model_version="latest",
            prompt_template="Frage: {question}\nAntwort:"
        )
        
        assert evaluation_id is not None
        assert evaluation_id in model_evaluator.evaluation_results
    
    def test_model_comparison(self):
        """Test für Modell-Vergleich in Evaluation"""
        # Füge Testfälle hinzu
        for i in range(2):
            test_case = TestCase(
                id=f"compare-test-{i}",
                input_data={"question": f"Test question {i}"},
                expected_output=f"Expected answer {i}",
                category="test"
            )
            model_evaluator.add_test_case(test_case)
        
        # Vergleiche Modelle
        comparison = model_evaluator.compare_models(
            model1_name="gpt-4",
            model1_version="latest",
            model2_name="gpt-3.5-turbo",
            model2_version="latest",
            prompt_template="Frage: {question}\nAntwort:"
        )
        
        assert "model1" in comparison
        assert "model2" in comparison
        assert "differences" in comparison


class TestIntegration:
    """Integration Tests"""
    
    def test_full_workflow(self):
        """Test für vollständigen Workflow"""
        # 1. Registriere Modell
        model_version = model_manager.register_model(
            name="integration-test",
            provider=ModelProvider.OPENAI,
            parameters={"temperature": 0.7}
        )
        
        # 2. Erstelle Prompt
        prompt_id = prompt_manager.create_prompt(
            template_name="integration-test",
            template="Antworte auf: {question}",
            variables=["question"]
        )
        
        # 3. Aktiviere Prompt
        prompt_manager.activate_prompt(prompt_id)
        
        # 4. Logge Request
        request = llm_monitor.log_request(
            request_id="integration-test-123",
            model_name="integration-test",
            model_version=model_version,
            prompt="Antworte auf: Was ist Python?",
            response="Python ist eine Programmiersprache",
            latency_ms=1500,
            success=True,
            prompt_id=prompt_id
        )
        
        # 5. Prüfe Ergebnisse
        assert request.success is True
        assert request.model_name == "integration-test"
        
        # 6. Hole Performance-Metriken
        metrics = llm_monitor.get_performance_metrics(hours=1)
        assert metrics["total_requests"] >= 1


if __name__ == "__main__":
    pytest.main([__file__])
