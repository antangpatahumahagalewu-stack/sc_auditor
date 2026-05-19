"""Intelligence Engine for Mythril Scanner Service (standalone).

Tidak bisa import vyper_lib karena dependency conflict. Semua model
dan logic bersifat self-contained.

Levels:
  L2 — SWC-based Classifier (Mythril sudah provide SWC ID)
  L3 — FP/TP Database
  L4 — Composite Scorer, Fix Generator, Exploit Chain, NLP
"""

from src.intelligence.models import (
    IntelFinding,
    IntelScore,
    IntelFix,
    IntelAnalysis,
)
from src.intelligence.classifier import MythrilClassifier, create_classifier
from src.intelligence.scorer import MythrilScorer, create_scorer
from src.intelligence.fixer import MythrilFixer, create_fixer
from src.intelligence.path_predictor import MythrilChainPredictor, create_path_predictor
from src.intelligence.nlp import MythrilNLP, create_nlp

__all__ = [
    "IntelAnalysis",
    "IntelFinding",
    "IntelFix",
    "IntelScore",
    "MythrilChainPredictor",
    "MythrilClassifier",
    "MythrilFixer",
    "MythrilNLP",
    "MythrilScorer",
    "create_classifier",
    "create_fixer",
    "create_nlp",
    "create_path_predictor",
    "create_scorer",
]
