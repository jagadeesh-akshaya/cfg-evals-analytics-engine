"""
Base Eval Class

Defines the interface all evals must implement.
"""

from abc import abstractmethod, ABCMeta
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
import json


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    input_query: str
    generated_sql: str | None
    expected: Any
    actual: Any
    error: str | None = None
    details: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvalSummary:
    eval_name: str
    timestamp: str
    total_cases: int
    passed: int
    failed: int
    pass_rate: float
    results: list[EvalResult]
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "eval_name": self.eval_name,
            "timestamp": self.timestamp,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class BaseEval(metaclass=ABCMeta):
    
    name: str = "base_eval"
    description: str = "Base evaluation"
    
    @abstractmethod
    def get_test_cases(self) -> list[dict]:
        pass
    
    @abstractmethod
    def evaluate_case(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        pass
    
    def run(self, generator_fn, verbose: bool = True) -> EvalSummary:
        """
        Run the eval against a SQL generator function.
        
        Args:
            generator_fn: Function that takes a query string and returns (sql, error)
            verbose: Print progress to stdout
        
        Returns:
            EvalSummary with all results
        """
        import sys
        import time
        
        test_cases = self.get_test_cases()
        results = []
        
        total = len(test_cases)
        for i, case in enumerate(test_cases, 1):
            query = case["query"]
            
            if verbose:
                # Show what we're testing
                print(f"  [{i}/{total}] {case.get('id', 'unknown')[:30]}...", end=" ", flush=True)
            
            start_time = time.time()
            
            # Generate SQL
            try:
                sql, error = generator_fn(query)
            except Exception as e:
                sql, error = None, str(e)
            
            elapsed = time.time() - start_time
            
            result = self.evaluate_case(case, sql, error)
            results.append(result)
            
            if verbose:
                status = "✓" if result.passed else "✗"
                print(f"{status} ({elapsed:.1f}s)", flush=True)
        
        # Calculate summary
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        pass_rate = passed / len(results) if results else 0.0
        
        return EvalSummary(
            eval_name=self.name,
            timestamp=datetime.now().isoformat(),
            total_cases=len(results),
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            results=results,
            metadata={"description": self.description},
        )
