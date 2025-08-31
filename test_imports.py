#!/usr/bin/env python3
"""
Einfacher Test für alle Imports
"""

import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Testet alle wichtigen Imports"""
    
    print("🧪 Teste Imports...")
    
    try:
        # Test 1: Config
        print("1. Teste config.settings...")
        from config.settings import settings, ModelProvider
        print("   ✅ config.settings erfolgreich")
        
        # Test 2: Model Manager
        print("2. Teste src.models.model_manager...")
        from src.models.model_manager import model_manager
        print("   ✅ model_manager erfolgreich")
        
        # Test 3: Prompt Manager
        print("3. Teste src.prompts.prompt_manager...")
        from src.prompts.prompt_manager import prompt_manager
        print("   ✅ prompt_manager erfolgreich")
        
        # Test 4: Monitor
        print("4. Teste src.monitoring.monitor...")
        from src.monitoring.monitor import llm_monitor
        print("   ✅ llm_monitor erfolgreich")
        
        # Test 5: Evaluator
        print("5. Teste src.evaluation.evaluator...")
        from src.evaluation.evaluator import model_evaluator
        print("   ✅ model_evaluator erfolgreich")
        
        # Test 6: Settings
        print("6. Teste Settings...")
        print(f"   Environment: {settings.environment}")
        print(f"   Default Model: {settings.default_model}")
        print(f"   Evaluation Metrics: {settings.evaluation_metrics}")
        print("   ✅ Settings erfolgreich")
        
        print("\n🎉 Alle Imports erfolgreich!")
        return True
        
    except Exception as e:
        print(f"\n❌ Fehler beim Import: {e}")
        print(f"   Typ: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
