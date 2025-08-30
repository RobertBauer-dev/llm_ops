"""
Evaluation System für LLM-Ops
Testet Model-Performance und Prompt-Effektivität
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from config.settings import settings
from src.monitoring.monitor import llm_monitor
from src.prompts.prompt_manager import prompt_manager


class EvaluationType(str, Enum):
    """Typen von Evaluationen"""
    ACCURACY = "accuracy"
    LATENCY = "latency"
    COST = "cost"
    USER_SATISFACTION = "user_satisfaction"
    A_B_TEST = "a_b_test"


@dataclass
class TestCase:
    """Ein Testfall für die Evaluation"""
    id: str
    input_data: Dict[str, Any]
    expected_output: Optional[str] = None
    expected_tokens: Optional[int] = None
    max_latency_ms: Optional[float] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None


@dataclass
class EvaluationResult:
    """Ergebnis einer Evaluation"""
    test_case_id: str
    model_name: str
    model_version: str
    prompt_id: Optional[str]
    actual_output: str
    actual_tokens: int
    latency_ms: float
    cost_usd: float
    success: bool
    error_message: Optional[str] = None
    accuracy_score: Optional[float] = None
    user_satisfaction_score: Optional[float] = None
    timestamp: datetime


@dataclass
class EvaluationSummary:
    """Zusammenfassung einer Evaluation"""
    evaluation_id: str
    model_name: str
    model_version: str
    prompt_id: Optional[str]
    total_tests: int
    successful_tests: int
    avg_accuracy: float
    avg_latency_ms: float
    total_cost_usd: float
    avg_cost_per_test: float
    success_rate: float
    start_time: datetime
    end_time: datetime
    test_categories: Dict[str, int]
    error_summary: Dict[str, int]


class ModelEvaluator:
    """Zentrale Klasse für Model Evaluation"""
    
    def __init__(self):
        self.test_cases: Dict[str, TestCase] = {}
        self.evaluation_results: Dict[str, List[EvaluationResult]] = {}
        self._load_test_cases()
    
    def _load_test_cases(self):
        """Lädt Testfälle aus der Konfiguration"""
        # Beispiel-Testfälle für verschiedene Szenarien
        test_cases = [
            TestCase(
                id="chat_001",
                input_data={"context": "Hallo, wie geht es dir?", "question": "Kannst du mir bei einer Frage helfen?"},
                expected_output="freundlich und hilfsbereit",
                category="chat",
                difficulty="easy"
            ),
            TestCase(
                id="summarization_001",
                input_data={"text": "Dies ist ein langer Text über künstliche Intelligenz und maschinelles Lernen. Die Technologie entwickelt sich schnell und wird in vielen Bereichen eingesetzt."},
                expected_tokens=50,
                category="summarization",
                difficulty="medium"
            ),
            TestCase(
                id="translation_001",
                input_data={"source_language": "Deutsch", "target_language": "Englisch", "text": "Guten Tag, wie geht es Ihnen?"},
                expected_output="Good day, how are you?",
                category="translation",
                difficulty="easy"
            ),
            TestCase(
                id="complex_001",
                input_data={"context": "Ein komplexes technisches Problem", "question": "Erkläre mir die Unterschiede zwischen verschiedenen Machine Learning Algorithmen"},
                max_latency_ms=5000,
                category="complex_qa",
                difficulty="hard"
            )
        ]
        
        for test_case in test_cases:
            self.test_cases[test_case.id] = test_case
    
    def add_test_case(self, test_case: TestCase):
        """Fügt einen neuen Testfall hinzu"""
        self.test_cases[test_case.id] = test_case
    
    def evaluate_model(
        self,
        model_name: str,
        model_version: str,
        prompt_template: str,
        test_case_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Führt eine vollständige Evaluation eines Modells durch"""
        
        evaluation_id = f"eval_{uuid.uuid4().hex[:8]}"
        results = []
        
        # Bestimme Testfälle
        if test_case_ids:
            test_cases = [self.test_cases[tc_id] for tc_id in test_case_ids if tc_id in self.test_cases]
        else:
            test_cases = list(self.test_cases.values())
        
        print(f"Starte Evaluation für Modell {model_name} mit {len(test_cases)} Testfällen")
        
        start_time = datetime.now()
        
        for test_case in test_cases:
            try:
                result = self._run_single_test(
                    test_case=test_case,
                    model_name=model_name,
                    model_version=model_version,
                    prompt_template=prompt_template,
                    user_id=user_id
                )
                results.append(result)
                
                # Kurze Pause zwischen Tests
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Fehler bei Testfall {test_case.id}: {e}")
                # Erstelle Fehler-Result
                error_result = EvaluationResult(
                    test_case_id=test_case.id,
                    model_name=model_name,
                    model_version=model_version,
                    prompt_id=None,
                    actual_output="",
                    actual_tokens=0,
                    latency_ms=0,
                    cost_usd=0,
                    success=False,
                    error_message=str(e),
                    timestamp=datetime.now()
                )
                results.append(error_result)
        
        end_time = datetime.now()
        
        # Erstelle Zusammenfassung
        summary = self._create_evaluation_summary(
            evaluation_id=evaluation_id,
            model_name=model_name,
            model_version=model_version,
            results=results,
            start_time=start_time,
            end_time=end_time
        )
        
        # Speichere Ergebnisse
        self.evaluation_results[evaluation_id] = results
        
        # Speichere Zusammenfassung
        self._save_evaluation_summary(summary)
        
        print(f"Evaluation abgeschlossen. Erfolgsrate: {summary.success_rate:.2%}")
        
        return evaluation_id
    
    def _run_single_test(
        self,
        test_case: TestCase,
        model_name: str,
        model_version: str,
        prompt_template: str,
        user_id: Optional[str] = None
    ) -> EvaluationResult:
        """Führt einen einzelnen Test durch"""
        
        # Rendere Prompt
        try:
            rendered_prompt = prompt_template.format(**test_case.input_data)
        except KeyError as e:
            raise ValueError(f"Fehlende Variable im Prompt: {e}")
        
        # Simuliere LLM-Antwort (in der Praxis würde hier der echte LLM-Call stehen)
        start_time = time.time()
        
        # Simulierte Antwort basierend auf Testfall
        if test_case.category == "chat":
            actual_output = "Hallo! Gerne helfe ich dir bei deiner Frage. Was möchtest du wissen?"
        elif test_case.category == "summarization":
            actual_output = "Text über KI und ML, der sich schnell entwickelt und vielfältig eingesetzt wird."
        elif test_case.category == "translation":
            actual_output = "Good day, how are you?"
        else:
            actual_output = "Dies ist eine simulierte Antwort für den Testfall."
        
        # Simuliere Latenz
        latency_ms = np.random.normal(1000, 200)  # 1s ± 200ms
        if test_case.max_latency_ms and latency_ms > test_case.max_latency_ms:
            latency_ms = test_case.max_latency_ms
        
        end_time = time.time()
        actual_latency_ms = (end_time - start_time) * 1000
        
        # Token-Zählung
        actual_tokens = llm_monitor.count_tokens(rendered_prompt + actual_output)
        
        # Kosten-Berechnung
        cost_usd = llm_monitor.calculate_cost(model_name, llm_monitor.count_tokens(rendered_prompt), llm_monitor.count_tokens(actual_output))
        
        # Accuracy-Bewertung
        accuracy_score = None
        if test_case.expected_output:
            accuracy_score = self._calculate_accuracy(actual_output, test_case.expected_output)
        
        # Erstelle Result
        result = EvaluationResult(
            test_case_id=test_case.id,
            model_name=model_name,
            model_version=model_version,
            prompt_id=None,  # Wird später gesetzt
            actual_output=actual_output,
            actual_tokens=actual_tokens,
            latency_ms=actual_latency_ms,
            cost_usd=cost_usd,
            success=True,
            accuracy_score=accuracy_score,
            timestamp=datetime.now()
        )
        
        return result
    
    def _calculate_accuracy(self, actual: str, expected: str) -> float:
        """Berechnet die Accuracy zwischen tatsächlicher und erwarteter Ausgabe"""
        # Einfache String-Ähnlichkeit (in der Praxis würde hier eine komplexere Metrik stehen)
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        
        if expected_lower in actual_lower:
            return 1.0
        
        # Wort-basierte Ähnlichkeit
        actual_words = set(actual_lower.split())
        expected_words = set(expected_lower.split())
        
        if not expected_words:
            return 1.0
        
        intersection = actual_words.intersection(expected_words)
        return len(intersection) / len(expected_words)
    
    def _create_evaluation_summary(
        self,
        evaluation_id: str,
        model_name: str,
        model_version: str,
        results: List[EvaluationResult],
        start_time: datetime,
        end_time: datetime
    ) -> EvaluationSummary:
        """Erstellt eine Zusammenfassung der Evaluation"""
        
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return EvaluationSummary(
                evaluation_id=evaluation_id,
                model_name=model_name,
                model_version=model_version,
                prompt_id=None,
                total_tests=len(results),
                successful_tests=0,
                avg_accuracy=0.0,
                avg_latency_ms=0.0,
                total_cost_usd=0.0,
                avg_cost_per_test=0.0,
                success_rate=0.0,
                start_time=start_time,
                end_time=end_time,
                test_categories={},
                error_summary={}
            )
        
        # Berechne Metriken
        accuracies = [r.accuracy_score for r in successful_results if r.accuracy_score is not None]
        latencies = [r.latency_ms for r in successful_results]
        costs = [r.cost_usd for r in successful_results]
        
        # Kategorien zählen
        categories = {}
        for result in results:
            test_case = self.test_cases.get(result.test_case_id)
            if test_case and test_case.category:
                categories[test_case.category] = categories.get(test_case.category, 0) + 1
        
        # Fehler zusammenfassen
        error_summary = {}
        for result in results:
            if not result.success and result.error_message:
                error_summary[result.error_message] = error_summary.get(result.error_message, 0) + 1
        
        return EvaluationSummary(
            evaluation_id=evaluation_id,
            model_name=model_name,
            model_version=model_version,
            prompt_id=None,
            total_tests=len(results),
            successful_tests=len(successful_results),
            avg_accuracy=sum(accuracies) / len(accuracies) if accuracies else 0.0,
            avg_latency_ms=sum(latencies) / len(latencies),
            total_cost_usd=sum(costs),
            avg_cost_per_test=sum(costs) / len(results),
            success_rate=len(successful_results) / len(results),
            start_time=start_time,
            end_time=end_time,
            test_categories=categories,
            error_summary=error_summary
        )
    
    def _save_evaluation_summary(self, summary: EvaluationSummary):
        """Speichert eine Evaluation-Zusammenfassung"""
        # Hier würde normalerweise die Speicherung in einer Datenbank erfolgen
        print(f"Evaluation Summary gespeichert: {summary.evaluation_id}")
    
    def compare_models(
        self,
        model1_name: str,
        model1_version: str,
        model2_name: str,
        model2_version: str,
        prompt_template: str,
        test_case_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Vergleicht zwei Modelle"""
        
        print(f"Starte Modell-Vergleich: {model1_name} vs {model2_name}")
        
        # Führe Evaluationen durch
        eval1_id = self.evaluate_model(model1_name, model1_version, prompt_template, test_case_ids)
        eval2_id = self.evaluate_model(model2_name, model2_version, prompt_template, test_case_ids)
        
        # Hole Ergebnisse
        results1 = self.evaluation_results.get(eval1_id, [])
        results2 = self.evaluation_results.get(eval2_id, [])
        
        # Erstelle Vergleich
        comparison = {
            "model1": {
                "name": model1_name,
                "version": model1_version,
                "evaluation_id": eval1_id,
                "total_tests": len(results1),
                "successful_tests": len([r for r in results1 if r.success]),
                "avg_accuracy": np.mean([r.accuracy_score for r in results1 if r.accuracy_score is not None]),
                "avg_latency_ms": np.mean([r.latency_ms for r in results1 if r.success]),
                "total_cost_usd": sum([r.cost_usd for r in results1]),
                "success_rate": len([r for r in results1 if r.success]) / len(results1) if results1 else 0
            },
            "model2": {
                "name": model2_name,
                "version": model2_version,
                "evaluation_id": eval2_id,
                "total_tests": len(results2),
                "successful_tests": len([r for r in results2 if r.success]),
                "avg_accuracy": np.mean([r.accuracy_score for r in results2 if r.accuracy_score is not None]),
                "avg_latency_ms": np.mean([r.latency_ms for r in results2 if r.success]),
                "total_cost_usd": sum([r.cost_usd for r in results2]),
                "success_rate": len([r for r in results2 if r.success]) / len(results2) if results2 else 0
            }
        }
        
        # Berechne Unterschiede
        comparison["differences"] = {
            "accuracy_diff": comparison["model2"]["avg_accuracy"] - comparison["model1"]["avg_accuracy"],
            "latency_diff": comparison["model2"]["avg_latency_ms"] - comparison["model1"]["avg_latency_ms"],
            "cost_diff": comparison["model2"]["total_cost_usd"] - comparison["model1"]["total_cost_usd"],
            "success_rate_diff": comparison["model2"]["success_rate"] - comparison["model1"]["success_rate"]
        }
        
        return comparison
    
    def get_evaluation_history(
        self,
        model_name: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Holt Evaluations-Historie"""
        # Hier würde normalerweise die Abfrage der Datenbank erfolgen
        # Für das Beispiel geben wir eine leere Liste zurück
        return []
    
    def export_evaluation_results(
        self,
        evaluation_id: str,
        format: str = "json"
    ) -> str:
        """Exportiert Evaluations-Ergebnisse"""
        
        results = self.evaluation_results.get(evaluation_id, [])
        
        if format == "json":
            return json.dumps([asdict(r) for r in results], default=str, indent=2)
        elif format == "csv":
            df = pd.DataFrame([asdict(r) for r in results])
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Nicht unterstütztes Format: {format}")


# Global evaluator instance
model_evaluator = ModelEvaluator()
