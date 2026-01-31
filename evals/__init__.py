"""
CFG Eval Suite

Coverage for:

1. Grammar Validity     : Does the model always respect the CFG?
2. Semantic Correctness : Does SQL match intent AND return correct data?
3. Safety Guardrails    : Can adversarial inputs break the system?
4. Robustness           : Edge cases and boundaries
"""

from .grammar_validity import GrammarValidityEval
from .semantic_correctness import SemanticCorrectnessEval
from .safety_guardrails import SafetyGuardrailsEval
from .robustness import RobustnessEval
from .runner import EvalRunner

__all__ = [
    "GrammarValidityEval",
    "SemanticCorrectnessEval",
    "SafetyGuardrailsEval",
    "RobustnessEval",
    "EvalRunner",
]
