"""
Eval Runner

Executes all evaluations and generates:
- Clear terminal output with scores
- JSON log files with unique timestamps
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.base import EvalSummary
from evals.grammar_validity import GrammarValidityEval
from evals.semantic_correctness import SemanticCorrectnessEval
from evals.safety_guardrails import SafetyGuardrailsEval
from evals.robustness import RobustnessEval


class EvalRunner:
    """
    Runs all evaluations and produces reports.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.evals = [
            GrammarValidityEval(),
            SemanticCorrectnessEval(),
            SafetyGuardrailsEval(),
            RobustnessEval(),
        ]
        
        self.results: list[EvalSummary] = []
    
    def create_generator(self):
        """
        Create the SQL generator function that connects to the API.
        Returns a function that takes a query and returns (sql, error).
        """
        import requests
        
        API_URL = os.getenv("EVAL_API_URL", "http://localhost:8000")
        
        def generator_fn(query: str) -> tuple[str | None, str | None]:
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": query},
                    timeout=120,  # GPT-5 can be slow
                )
                data = response.json()
                
                if data.get("success"):
                    return data.get("generated_sql"), None
                else:
                    return None, data.get("error", "Unknown error")
            except Exception as e:
                return None, str(e)
        
        return generator_fn
    
    def run_all(self, generator_fn=None) -> list[EvalSummary]:
        """
        Run all evaluations.
        
        Args:
            generator_fn: Optional custom generator. If None, uses API.
        
        Returns:
            List of EvalSummary objects
        """
        if generator_fn is None:
            generator_fn = self.create_generator()
        
        self.results = []
        
        for eval in self.evals:
            print(f"\n{'='*60}")
            print(f"Running: {eval.name} ({len(eval.get_test_cases())} cases)")
            print(f"{'='*60}\n")
            
            summary = eval.run(generator_fn)
            self.results.append(summary)
            
            # Quick summary for this eval
            print(f"\n  → {summary.passed}/{summary.total_cases} passed ({summary.pass_rate*100:.0f}%)")
        
        return self.results
    
    def print_summary(self):
        """Print a formatted summary to terminal."""
        print("\n")
        print("=" * 70)
        print("                         EVAL RESULTS SUMMARY")
        print("=" * 70)
        print()
        
        total_cases = 0
        total_passed = 0
        
        for summary in self.results:
            total_cases += summary.total_cases
            total_passed += summary.passed
            
            # Color coding for pass rate
            if summary.pass_rate == 1.0:
                status = "✓ PASS"
                color = "\033[92m"  # Green
            elif summary.pass_rate >= 0.8:
                status = "⚠ WARN"
                color = "\033[93m"  # Yellow
            else:
                status = "✗ FAIL"
                color = "\033[91m"  # Red
            reset = "\033[0m"
            
            print(f"┌{'─'*68}┐")
            print(f"│ {summary.eval_name.upper():^66} │")
            print(f"├{'─'*68}┤")
            print(f"│  {color}{status}{reset}  Pass Rate: {summary.pass_rate*100:6.1f}%  ({summary.passed}/{summary.total_cases} cases)          │")
            print(f"└{'─'*68}┘")
            print()
            
            # Show failures if any
            failures = [r for r in summary.results if not r.passed]
            if failures:
                print(f"  Failed cases:")
                for f in failures[:5]:  # Show first 5 failures
                    print(f"    ✗ {f.case_id}: {f.input_query[:40]}...")
                    if f.error:
                        print(f"      Error: {f.error[:60]}...")
                if len(failures) > 5:
                    print(f"    ... and {len(failures)-5} more failures")
                print()
        
        # Overall summary
        overall_rate = total_passed / total_cases if total_cases > 0 else 0
        print("=" * 70)
        print(f"  OVERALL: {total_passed}/{total_cases} cases passed ({overall_rate*100:.1f}%)")
        print("=" * 70)
        print()
    
    def save_logs(self) -> list[str]:
        """
        Save detailed results to JSON log files.
        
        Returns:
            List of log file paths created
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_files = []
        
        for summary in self.results:
            filename = f"{summary.eval_name}_{timestamp}.json"
            filepath = self.logs_dir / filename
            
            with open(filepath, 'w') as f:
                f.write(summary.to_json())
            
            log_files.append(str(filepath))
            print(f"  Saved: {filepath}")
        
        # Also save a combined summary
        combined_filename = f"eval_summary_{timestamp}.json"
        combined_filepath = self.logs_dir / combined_filename
        
        combined = {
            "timestamp": timestamp,
            "evals": [s.to_dict() for s in self.results],
            "overall": {
                "total_cases": sum(s.total_cases for s in self.results),
                "total_passed": sum(s.passed for s in self.results),
                "total_failed": sum(s.failed for s in self.results),
            }
        }
        combined["overall"]["pass_rate"] = (
            combined["overall"]["total_passed"] / combined["overall"]["total_cases"]
            if combined["overall"]["total_cases"] > 0 else 0
        )
        
        with open(combined_filepath, 'w') as f:
            json.dump(combined, f, indent=2, default=str)
        
        log_files.append(str(combined_filepath))
        print(f"  Saved: {combined_filepath}")
        
        return log_files


def main():
    """Main entry point for running evals from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run CFG Eval Suite")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="API URL (default: http://localhost:8000)")
    parser.add_argument("--logs-dir", default="logs",
                       help="Directory for log files (default: logs)")
    parser.add_argument("--no-save", action="store_true",
                       help="Don't save log files")
    args = parser.parse_args()
    
    os.environ["EVAL_API_URL"] = args.api_url
    
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                    CFG EVAL SUITE                                ║")
    print("║                                                                  ║")
    print("║  1. Grammar Validity      - Does output respect the CFG?        ║")
    print("║  2. Semantic Correctness  - Does SQL match intent + data?       ║")
    print("║  3. Safety Guardrails     - Are adversarial inputs handled?     ║")
    print("║  4. Robustness            - How are edge cases handled?         ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    print(f"API URL: {args.api_url}")
    print(f"Logs:    {args.logs_dir}/")
    print()
    
    # Check API is reachable
    import requests
    try:
        response = requests.get(f"{args.api_url}/health", timeout=5)
        health = response.json()
        if health.get("status") != "healthy":
            print(f"⚠ API health check: {health}")
        else:
            print("✓ API is healthy")
    except Exception as e:
        print(f"✗ Cannot reach API: {e}")
        print("  Make sure the server is running: uvicorn api.main:app --reload")
        sys.exit(1)
    
    # Run evals
    runner = EvalRunner(logs_dir=args.logs_dir)
    runner.run_all()
    
    # Print summary
    runner.print_summary()
    
    # Save logs
    if not args.no_save:
        print("Saving logs...")
        runner.save_logs()
    
    # Exit code based on results
    all_passed = all(s.pass_rate == 1.0 for s in runner.results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
