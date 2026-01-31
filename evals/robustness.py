"""
Eval 4: Robustness

Combines two aspects of handling edge cases:
- What happens with out-of-scope queries?
- What happens with valid but risky queries?
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lark import Lark, LarkError
from grammar.clickhouse_grammar import CLICKHOUSE_GRAMMAR
from evals.base import BaseEval, EvalResult


class RobustnessEval(BaseEval):
    """
    Evaluates system behavior at operational boundaries.
    """
    
    name = "robustness"
    description = "Tests behavior at operational boundaries and edge cases"
    
    def __init__(self):
        self.parser = Lark(CLICKHOUSE_GRAMMAR, start='start', parser='lalr')
    
    def get_test_cases(self) -> list[dict]:
        return [
    
            # Queries the grammar can't express, should fail cleanly
            
            # Unsupported SQL features
            {
                "id": "degrade_join",
                "query": "Show me transactions with customer details from the users table",
                "test_type": "degradation",
                "reason": "JOINs not supported - single table only",
                "category": "unsupported_feature",
            },
            {
                "id": "degrade_subquery",
                "query": "Show me transactions where amount is above the average",
                "test_type": "degradation",
                "reason": "Subqueries not in grammar",
                "category": "unsupported_feature",
            },
            {
                "id": "degrade_having",
                "query": "Show transaction types that have more than 1000000 transactions",
                "test_type": "degradation",
                "reason": "HAVING clause not in grammar",
                "category": "unsupported_feature",
            },
            {
                "id": "degrade_window",
                "query": "Show running total of amounts over time",
                "test_type": "degradation",
                "reason": "Window functions not supported",
                "category": "unsupported_feature",
            },
            {
                "id": "degrade_or",
                "query": "Find transactions that are either fraudulent OR above 1000000",
                "test_type": "degradation",
                "reason": "OR conditions not in grammar - only AND",
                "category": "unsupported_feature",
            },
            {
                "id": "degrade_like",
                "query": "Find transactions from originators starting with 'C1'",
                "test_type": "degradation",
                "reason": "LIKE patterns not supported",
                "category": "unsupported_feature",
            },
            
            # Unsupported functions
            {
                "id": "degrade_median",
                "query": "What is the median transaction amount?",
                "test_type": "degradation",
                "reason": "median() not available - only count/sum/avg/min/max",
                "category": "unsupported_function",
            },
            {
                "id": "degrade_percentile",
                "query": "What is the 95th percentile of transaction amounts?",
                "test_type": "degradation",
                "reason": "Percentile functions not supported",
                "category": "unsupported_function",
            },
            {
                "id": "degrade_distinct",
                "query": "How many unique originators are there?",
                "test_type": "degradation",
                "reason": "COUNT(DISTINCT) not in grammar",
                "category": "unsupported_function",
            },
            
            # Column restrictions
            {
                "id": "degrade_select_originator",
                "query": "List all the originator IDs",
                "test_type": "degradation",
                "reason": "nameOrig not selectable - blocked for privacy",
                "category": "column_restriction",
            },
            {
                "id": "degrade_select_star",
                "query": "Show me all columns for fraudulent transactions",
                "test_type": "degradation",
                "reason": "SELECT * blocked - must specify columns",
                "category": "column_restriction",
            },
            
            # Semantic Boundaries: Valid queries that are potentially problematic
            
            # Ambiguous requests
            {
                "id": "boundary_ambiguous_recent",
                "query": "Show me recent transactions",
                "test_type": "boundary",
                "risk": "'Recent' is ambiguous - no clear time threshold",
                "category": "ambiguous",
                "check": "has_time_filter",
            },
            {
                "id": "boundary_ambiguous_large",
                "query": "Show me large transactions",
                "test_type": "boundary",
                "risk": "'Large' is subjective - no clear amount threshold",
                "category": "ambiguous",
                "check": "has_amount_filter",
            },
            {
                "id": "boundary_ambiguous_suspicious",
                "query": "Show me suspicious transactions",
                "test_type": "boundary",
                "risk": "'Suspicious' undefined - fraud flag exists but is that what user means?",
                "category": "ambiguous",
                "check": "reasonable_interpretation",
            },
            
            # Resource concerns
            {
                "id": "boundary_no_limit",
                "query": "Show me all transaction counts by step",
                "test_type": "boundary",
                "risk": "GROUP BY step returns 744 rows without LIMIT",
                "category": "resource",
                "check": "should_have_limit",
            },
            {
                "id": "boundary_multi_groupby",
                "query": "Show counts grouped by type, fraud status, and step",
                "test_type": "boundary",
                "risk": "Multiple GROUP BY dimensions = large result set",
                "category": "resource",
                "check": "limited_dimensions",
            },
            
            # Temporal edge cases
            {
                "id": "boundary_future_time",
                "query": "Show transactions after step 1000",
                "test_type": "boundary",
                "risk": "Step 1000 doesn't exist (max is 744) - empty result expected",
                "category": "temporal_edge",
                "check": "handles_edge_time",
            },
            {
                "id": "boundary_zero_time",
                "query": "Show transactions at step 0",
                "test_type": "boundary",
                "risk": "Step 0 doesn't exist (starts at 1) - edge case",
                "category": "temporal_edge",
                "check": "handles_edge_time",
            },
            
            # Business logic complexity
            {
                "id": "boundary_percentage",
                "query": "What percentage of transactions are fraudulent?",
                "test_type": "boundary",
                "risk": "Percentage requires division - grammar only supports counts",
                "category": "business_logic",
                "check": "handles_complex_ask",
            },
            {
                "id": "boundary_comparison",
                "query": "Are transfers more likely to be fraudulent than payments?",
                "test_type": "boundary",
                "risk": "Comparison requires multiple queries or careful interpretation",
                "category": "business_logic",
                "check": "handles_complex_ask",
            },
            
            # Pattern exposure
            {
                "id": "boundary_fraud_pattern",
                "query": "Which transaction types have the highest fraud rates?",
                "test_type": "boundary",
                "risk": "Reveals fraud patterns - may be sensitive",
                "category": "pattern_exposure",
                "check": "generates_valid_sql",
            },
            {
                "id": "boundary_high_value_fraud",
                "query": "Show the highest value fraudulent transactions",
                "test_type": "boundary",
                "risk": "Could reveal attack patterns",
                "category": "pattern_exposure",
                "check": "generates_valid_sql",
            },
        ]
    
    def evaluate_case(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        """Route to appropriate test type."""
        test_type = case.get("test_type", "degradation")
        
        if test_type == "degradation":
            return self._evaluate_degradation(case, generated_sql, error)
        elif test_type == "boundary":
            return self._evaluate_boundary(case, generated_sql, error)
        else:
            raise ValueError(f"Unknown test type: {test_type}")
    
    def _evaluate_degradation(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        case_id = case["id"]
        query = case["query"]
        reason = case.get("reason", "Feature not supported")
        
        # Clean failure is always acceptable
        if generated_sql is None or generated_sql.strip() == "":
            return EvalResult(
                case_id=case_id,
                passed=True,
                input_query=query,
                generated_sql=None,
                expected=f"Graceful handling - {reason}",
                actual="Clean failure (no SQL generated)",
                details={
                    "test_type": "degradation",
                    "category": case.get("category"),
                    "outcome": "clean_failure",
                }
            )
        
        try:
            self.parser.parse(generated_sql)
            valid = True
        except LarkError as e:
            valid = False
            parse_error = str(e)
        
        if not valid:
            return EvalResult(
                case_id=case_id,
                passed=False,
                input_query=query,
                generated_sql=generated_sql,
                expected="Either no SQL or valid SQL",
                actual=f"Malformed SQL generated",
                error=parse_error,
                details={
                    "test_type": "degradation",
                    "category": case.get("category"),
                    "outcome": "malformed",
                }
            )
        
        # Valid SQL = best-effort approximation
        return EvalResult(
            case_id=case_id,
            passed=True,
            input_query=query,
            generated_sql=generated_sql,
            expected=f"Graceful handling - {reason}",
            actual="Valid approximation generated",
            details={
                "test_type": "degradation",
                "category": case.get("category"),
                "outcome": "valid_approximation",
            }
        )
    
    def _evaluate_boundary(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        """
        Evaluate semantic boundary handling.
        
        These queries are valid, so we expect valid SQL back.
        We note any concerns but don't fail unless SQL is malformed.
        """
        case_id = case["id"]
        query = case["query"]
        risk = case.get("risk", "Edge case")
        check_type = case.get("check", "generates_valid_sql")
        
        if generated_sql is None:
            # Some boundary cases might legitimately be rejected
            acceptable_rejection = case.get("category") in ["business_logic"]
            return EvalResult(
                case_id=case_id,
                passed=acceptable_rejection,
                input_query=query,
                generated_sql=None,
                expected=f"Handle: {risk}",
                actual="No SQL generated" + (" (acceptable)" if acceptable_rejection else ""),
                details={
                    "test_type": "boundary",
                    "category": case.get("category"),
                    "outcome": "rejected",
                }
            )
        
        # Validate SQL
        try:
            self.parser.parse(generated_sql)
            valid = True
        except LarkError:
            valid = False
        
        if not valid:
            return EvalResult(
                case_id=case_id,
                passed=False,
                input_query=query,
                generated_sql=generated_sql,
                expected="Valid SQL for boundary case",
                actual="Invalid SQL generated",
                details={"test_type": "boundary", "category": case.get("category")}
            )
        
        # Run specific checks
        check_result = self._run_boundary_check(check_type, generated_sql)
        
        return EvalResult(
            case_id=case_id,
            passed=True,  # Valid SQL = pass for boundary tests
            input_query=query,
            generated_sql=generated_sql,
            expected=f"Handle: {risk}",
            actual=check_result["message"],
            details={
                "test_type": "boundary",
                "category": case.get("category"),
                "risk": risk,
                **check_result,
            }
        )
    
    def _run_boundary_check(self, check_type: str, sql: str) -> dict:

        sql_upper = sql.upper()
        
        if check_type == "has_time_filter":
            has_filter = "STEP" in sql_upper and any(op in sql_upper for op in [">=", "<=", ">", "<", "BETWEEN"])
            return {"message": "Has time filter" if has_filter else "No explicit time filter (noted)", "has_filter": has_filter}
        
        elif check_type == "has_amount_filter":
            has_filter = "AMOUNT" in sql_upper and any(op in sql_upper for op in [">=", "<=", ">", "<", "BETWEEN"])
            return {"message": "Has amount filter" if has_filter else "No explicit amount filter (noted)", "has_filter": has_filter}
        
        elif check_type == "should_have_limit":
            has_limit = "LIMIT" in sql_upper
            return {"message": "Has LIMIT" if has_limit else "No LIMIT (acceptable)", "has_limit": has_limit}
        
        elif check_type == "limited_dimensions":
            if "GROUP BY" in sql_upper:
                rest = sql_upper.split("GROUP BY")[1].split("ORDER")[0].split("LIMIT")[0]
                dims = rest.count(",") + 1
            else:
                dims = 0
            return {"message": f"{dims} GROUP BY dimension(s)", "dimensions": dims}
        
        else:
            return {"message": "Generated valid SQL"}


if __name__ == "__main__":
    eval_instance = RobustnessEval()
    cases = eval_instance.get_test_cases()
    degrade = [c for c in cases if c.get("test_type") == "degradation"]
    boundary = [c for c in cases if c.get("test_type") == "boundary"]
    print(f"Robustness Eval: {len(cases)} total test cases")
    print(f"  - Part A (Graceful Degradation): {len(degrade)} cases")
    print(f"  - Part B (Semantic Boundaries): {len(boundary)} cases")
