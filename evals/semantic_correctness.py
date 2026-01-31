"""
Eval for Semantic Correctness

Combines two aspects of "did we get it right?":
1. Intent Fidelity: Does the SQL capture what the user asked for?
2. Execution Correctness: Does the SQL return the right data?
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from evals.base import BaseEval, EvalResult
from engine.clickhouse_client import ClickHouseClient


class SemanticCorrectnessEval(BaseEval):
    """
    Evaluates whether generated SQL correctly captures user intent
    AND returns correct data when executed.
    """
    
    name = "semantic_correctness"
    description = "Tests if SQL captures user intent and returns correct data"
    
    def __init__(self):
        self.client = ClickHouseClient()
    
    def get_test_cases(self) -> list[dict]:
       
        return [
            # Part A: Intent Fidelity Tests
            # Verify SQL contains the right semantic elements
            
            # Metric extraction
            {
                "id": "intent_count_metric",
                "query": "How many transactions are there?",
                "verification": "intent",
                "expected_elements": {
                    "metric": "count",
                    "table": "Transactions",
                },
                "category": "metric",
            },
            {
                "id": "intent_sum_metric",
                "query": "What is the total amount of all transactions?",
                "verification": "intent",
                "expected_elements": {
                    "metric": "sum",
                    "columns": ["amount"],
                    "table": "Transactions",
                },
                "category": "metric",
            },
            {
                "id": "intent_avg_metric",
                "query": "What's the average transaction amount?",
                "verification": "intent",
                "expected_elements": {
                    "metric": "avg",
                    "columns": ["amount"],
                },
                "category": "metric",
            },
            
            # Filter extraction
            {
                "id": "intent_fraud_filter",
                "query": "Show me fraudulent transactions",
                "verification": "intent",
                "expected_elements": {
                    "filters": [{"column": "isFraud", "value": "1"}],
                },
                "category": "filter",
            },
            {
                "id": "intent_type_filter",
                "query": "Count all TRANSFER type transactions",
                "verification": "intent",
                "expected_elements": {
                    "metric": "count",
                    "filters": [{"column": "type", "value": "TRANSFER"}],
                },
                "category": "filter",
            },
            {
                "id": "intent_amount_filter",
                "query": "How many transactions are above 100000?",
                "verification": "intent",
                "expected_elements": {
                    "metric": "count",
                    "filters": [{"column": "amount", "operator": ">", "value": "100000"}],
                },
                "category": "filter",
            },
            
            # Time-based
            {
                "id": "intent_time_range",
                "query": "Show transactions between step 100 and 200",
                "verification": "intent",
                "expected_elements": {
                    "filters": [{"column": "step", "operator": "between", "values": ["100", "200"]}],
                },
                "category": "time",
            },
            
            # Grouping
            {
                "id": "intent_group_by_type",
                "query": "Show transaction counts for each type",
                "verification": "intent",
                "expected_elements": {
                    "metric": "count",
                    "group_by": ["type"],
                },
                "category": "grouping",
            },
            {
                "id": "intent_group_by_fraud",
                "query": "Compare fraudulent vs non-fraudulent transaction counts",
                "verification": "intent",
                "expected_elements": {
                    "metric": "count",
                    "group_by": ["isFraud"],
                },
                "category": "grouping",
            },
            
            # Complex combinations
            {
                "id": "intent_complex_1",
                "query": "What's the average amount of fraudulent TRANSFER transactions?",
                "verification": "intent",
                "expected_elements": {
                    "metric": "avg",
                    "columns": ["amount"],
                    "filters": [
                        {"column": "isFraud", "value": "1"},
                        {"column": "type", "value": "TRANSFER"},
                    ],
                },
                "category": "complex",
            },
            {
                "id": "intent_complex_2",
                "query": "Count CASH-OUT transactions over 50000 grouped by fraud status",
                "verification": "intent",
                "expected_elements": {
                    "metric": "count",
                    "filters": [
                        {"column": "type", "value": "CASH-OUT"},
                        {"column": "amount", "operator": ">", "value": "50000"},
                    ],
                    "group_by": ["isFraud"],
                },
                "category": "complex",
            },
            
            # PART B: Execution Correctness Tests
            # Run golden SQL and compare actual results
            
            # Exact counts
            {
                "id": "exec_count_all",
                "query": "How many transactions are there in total?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions;",
                "comparison": "exact",
                "category": "count",
            },
            {
                "id": "exec_count_fraud",
                "query": "How many fraudulent transactions are there?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions WHERE isFraud = 1;",
                "comparison": "exact",
                "category": "count",
            },
            {
                "id": "exec_count_transfers",
                "query": "How many transfer transactions are there?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions WHERE type = 'TRANSFER';",
                "comparison": "exact",
                "category": "count",
            },
            {
                "id": "exec_count_cashout",
                "query": "How many cash-out transactions are there?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions WHERE type = 'CASH-OUT';",
                "comparison": "exact",
                "category": "count",
            },
            
            # Aggregations with tolerance
            {
                "id": "exec_sum_all",
                "query": "What is the total sum of all transaction amounts?",
                "verification": "execution",
                "golden_sql": "SELECT sum(amount) FROM Transactions;",
                "comparison": "tolerance",
                "tolerance": 0.01,
                "category": "aggregation",
            },
            {
                "id": "exec_avg_amount",
                "query": "What is the average transaction amount?",
                "verification": "execution",
                "golden_sql": "SELECT avg(amount) FROM Transactions;",
                "comparison": "tolerance",
                "tolerance": 0.01,
                "category": "aggregation",
            },
            {
                "id": "exec_sum_fraud",
                "query": "What is the total amount of fraudulent transactions?",
                "verification": "execution",
                "golden_sql": "SELECT sum(amount) FROM Transactions WHERE isFraud = 1;",
                "comparison": "tolerance",
                "tolerance": 0.01,
                "category": "aggregation",
            },
            
            # Row counts for grouped queries
            {
                "id": "exec_group_type",
                "query": "Show me the count of transactions for each type",
                "verification": "execution",
                "golden_sql": "SELECT type, count(*) FROM Transactions GROUP BY type;",
                "comparison": "row_count",
                "expected_rows": 5,
                "category": "grouped",
            },
            {
                "id": "exec_group_fraud",
                "query": "Show me transaction counts grouped by fraud status",
                "verification": "execution",
                "golden_sql": "SELECT isFraud, count(*) FROM Transactions GROUP BY isFraud;",
                "comparison": "row_count",
                "expected_rows": 2,
                "category": "grouped",
            },
            
            # Filtered counts
            {
                "id": "exec_fraud_transfers",
                "query": "How many fraudulent transfer transactions are there?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions WHERE isFraud = 1 AND type = 'TRANSFER';",
                "comparison": "exact",
                "category": "filtered",
            },
            {
                "id": "exec_time_range",
                "query": "How many transactions between step 100 and 200?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions WHERE step BETWEEN 100 AND 200;",
                "comparison": "exact",
                "category": "filtered",
            },
            {
                "id": "exec_high_value",
                "query": "How many transactions are above 1000000?",
                "verification": "execution",
                "golden_sql": "SELECT count(*) FROM Transactions WHERE amount > 1000000;",
                "comparison": "exact",
                "category": "filtered",
            },
        ]
    
    def evaluate_case(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
       
        verification = case.get("verification", "intent")
        
        if verification == "intent":
            return self._evaluate_intent(case, generated_sql, error)
        elif verification == "execution":
            return self._evaluate_execution(case, generated_sql, error)
        else:
            raise ValueError(f"Unknown verification type: {verification}")
    
    def _evaluate_intent(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        """Check if SQL contains expected semantic elements."""
        case_id = case["id"]
        query = case["query"]
        expected = case.get("expected_elements", {})
        
        if generated_sql is None:
            return EvalResult(
                case_id=case_id,
                passed=False,
                input_query=query,
                generated_sql=None,
                expected=str(expected),
                actual="No SQL generated",
                error=error,
            )
        
        sql_upper = generated_sql.upper()
        checks = []
        all_passed = True
        
        if "metric" in expected:
            metric = expected["metric"].upper()
            found = metric in sql_upper
            checks.append(f"metric:{metric}={found}")
            all_passed = all_passed and found
        
        if "table" in expected:
            table = expected["table"].upper()
            found = table in sql_upper
            checks.append(f"table:{table}={found}")
            all_passed = all_passed and found
        
        if "columns" in expected:
            for col in expected["columns"]:
                found = col.upper() in sql_upper
                checks.append(f"col:{col}={found}")
                all_passed = all_passed and found
        
        if "filters" in expected:
            for f in expected["filters"]:
                col = f["column"].upper()
                found = col in sql_upper
                if "value" in f:
                    found = found and f["value"].upper() in sql_upper
                if "values" in f:
                    found = found and all(v in sql_upper for v in f["values"])
                checks.append(f"filter:{col}={found}")
                all_passed = all_passed and found
        
        if "group_by" in expected:
            for col in expected["group_by"]:
                pattern = rf"GROUP\s+BY.*{col.upper()}"
                found = bool(re.search(pattern, sql_upper))
                checks.append(f"groupby:{col}={found}")
                all_passed = all_passed and found
        
        return EvalResult(
            case_id=case_id,
            passed=all_passed,
            input_query=query,
            generated_sql=generated_sql,
            expected=str(expected),
            actual=", ".join(checks),
            details={"checks": checks, "category": case.get("category")},
        )
    
    def _evaluate_execution(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        """Execute both golden and generated SQL, compare results."""
        case_id = case["id"]
        query = case["query"]
        golden_sql = case["golden_sql"]
        comparison = case.get("comparison", "exact")
        
        if generated_sql is None:
            return EvalResult(
                case_id=case_id,
                passed=False,
                input_query=query,
                generated_sql=None,
                expected=f"Golden: {golden_sql}",
                actual="No SQL generated",
                error=error,
            )
        
        # Execute golden SQL
        golden_result = self.client.execute(golden_sql)
        if not golden_result.success:
            return EvalResult(
                case_id=case_id,
                passed=False,
                input_query=query,
                generated_sql=generated_sql,
                expected="Golden SQL should execute",
                actual=f"Golden failed: {golden_result.error}",
                error=golden_result.error,
            )
        
        # Execute generated SQL
        gen_result = self.client.execute(generated_sql)
        if not gen_result.success:
            return EvalResult(
                case_id=case_id,
                passed=False,
                input_query=query,
                generated_sql=generated_sql,
                expected="Generated SQL should execute",
                actual=f"Execution failed: {gen_result.error}",
                error=gen_result.error,
            )
        
        # Compare based on method
        if comparison == "exact":
            passed, details = self._compare_exact(golden_result.data, gen_result.data)
        elif comparison == "row_count":
            expected_rows = case.get("expected_rows", golden_result.row_count)
            passed = gen_result.row_count == expected_rows
            details = {"expected_rows": expected_rows, "actual_rows": gen_result.row_count}
        elif comparison == "tolerance":
            tolerance = case.get("tolerance", 0.01)
            passed, details = self._compare_tolerance(golden_result.data, gen_result.data, tolerance)
        else:
            passed, details = False, {"error": f"Unknown comparison: {comparison}"}
        
        return EvalResult(
            case_id=case_id,
            passed=passed,
            input_query=query,
            generated_sql=generated_sql,
            expected={"golden_sql": golden_sql, "golden_data": golden_result.data},
            actual={"generated_data": gen_result.data},
            details={"comparison": comparison, "category": case.get("category"), **details},
        )
    
    def _compare_exact(self, golden: list, generated: list) -> tuple[bool, dict]:
        if len(golden) != len(generated):
            return False, {"reason": "row_count_mismatch"}
        
        if len(golden) == 1 and len(generated) == 1:
            g_val = list(golden[0].values())[0]
            gen_val = list(generated[0].values())[0]
            return g_val == gen_val, {"golden": g_val, "generated": gen_val}
        
        return golden == generated, {"exact_match": golden == generated}
    
    def _compare_tolerance(self, golden: list, generated: list, tolerance: float) -> tuple[bool, dict]:
        """Compare numeric values with tolerance."""
        if len(golden) != len(generated) or len(golden) != 1:
            return False, {"reason": "structure_mismatch"}
        
        g_val = list(golden[0].values())[0]
        gen_val = list(generated[0].values())[0]
        
        if g_val == 0:
            passed = gen_val == 0
        else:
            diff = abs(g_val - gen_val) / abs(g_val)
            passed = diff <= tolerance
        
        return passed, {"golden": g_val, "generated": gen_val, "tolerance": tolerance}


if __name__ == "__main__":
    eval_instance = SemanticCorrectnessEval()
    cases = eval_instance.get_test_cases()
    intent_cases = [c for c in cases if c.get("verification") == "intent"]
    exec_cases = [c for c in cases if c.get("verification") == "execution"]
    print(f"Semantic Correctness Eval: {len(cases)} total test cases")
    print(f"  - Part A (Intent Fidelity): {len(intent_cases)} cases")
    print(f"  - Part B (Execution): {len(exec_cases)} cases")
