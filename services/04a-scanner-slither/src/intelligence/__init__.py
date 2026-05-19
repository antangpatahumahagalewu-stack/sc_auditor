"""Intelligence Engine for Slither Scanner Service.

Provides context-aware analysis, composite scoring, exploit path prediction,
auto-fix generation, and natural language query capabilities.

Levels:
  L2 — Contract Classifier + Smart Detector Selection
  L3 — FP/TP Database (self-learning from feedback)
  L4 — Composite Risk Scoring, Exploit Path Prediction, Auto-Fix, NLP
"""

from src.intelligence.classifier import ContractClassifier, ContractType, create_classifier
from src.intelligence.scorer import CompositeScorer, RiskScore, create_scorer
from src.intelligence.fp_db import FalsePositiveDB, create_fp_db
from src.intelligence.fixer import FixGenerator, create_fixer
from src.intelligence.path_predictor import ExploitPathPredictor, create_path_predictor
from src.intelligence.nlp import NaturalLanguageQuery, create_nlp

__all__ = [
    "CompositeScorer",
    "ContractClassifier",
    "ContractType",
    "ExploitPathPredictor",
    "FalsePositiveDB",
    "FixGenerator",
    "NaturalLanguageQuery",
    "RiskScore",
    "create_classifier",
    "create_fixer",
    "create_fp_db",
    "create_nlp",
    "create_path_predictor",
    "create_scorer",
]
