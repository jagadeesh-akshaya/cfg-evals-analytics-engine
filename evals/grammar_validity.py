"""
Eval for Grammar Validity and Constrained Generation

Tests whether the model always respects the CFG constraints.

Pass Criteria:
- 100% grammar-valid output
- Any invalid request: clean failure, not malformed SQL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lark import Lark, LarkError
from grammar.clickhouse_grammar import CLICKHOUSE_GRAMMAR
from evals.base import BaseEval, EvalResult


class GrammarValidityEval(BaseEval):
    """
    Evaluates whether generated SQL always conforms to the CFG.
    """
    
    name = "grammar_validity"
    description = "Tests if all generated SQL conforms to the Lark grammar"
    
    def __init__(self):
        self.parser = Lark(CLICKHOUSE_GRAMMAR, start='start', parser='lalr')
    
    def get_test_cases(self) -> list[dict]:
       
        return [
            # Basic aggregations
            {"id": "basic_count", "query": "How many transactions are there?", "category": "basic"},
            {"id": "basic_sum", "query": "What is the total transaction amount?", "category": "basic"},
            {"id": "basic_avg", "query": "What is the average transaction amount?", "category": "basic"},
            {"id": "basic_min", "query": "What is the minimum transaction amount?", "category": "basic"},
            {"id": "basic_max", "query": "What is the maximum transaction amount?", "category": "basic"},
            
            # Filtered queries
            {"id": "filter_fraud", "query": "How many fraudulent transactions are there?", "category": "filter"},
            {"id": "filter_type", "query": "How many transfer transactions are there?", "category": "filter"},
            {"id": "filter_type_cashout", "query": "Count all cash-out transactions", "category": "filter"},
            {"id": "filter_amount_gt", "query": "How many transactions are above 100000?", "category": "filter"},
            {"id": "filter_non_fraud", "query": "Count transactions that are not fraudulent", "category": "filter"},
            
            # Time-based queries
            {"id": "time_recent", "query": "How many transactions in the last 24 hours of the simulation?", "category": "time"},
            {"id": "time_range", "query": "Count transactions between step 500 and 600", "category": "time"},
            {"id": "time_early", "query": "How many transactions in the first 100 hours?", "category": "time"},
            {"id": "time_late", "query": "Sum amounts after step 700", "category": "time"},
            
            # Group by queries
            {"id": "group_type", "query": "Show transaction count by type", "category": "group"},
            {"id": "group_fraud", "query": "Show average amount for fraud vs non-fraud", "category": "group"},
            {"id": "group_type_sum", "query": "Total amount for each transaction type", "category": "group"},
            
            # Complex queries
            {"id": "complex_multi_filter", "query": "Count fraudulent transfers", "category": "complex"},
            {"id": "complex_time_type", "query": "Sum of transfers in the last 48 hours", "category": "complex"},
            {"id": "complex_ordered", "query": "Show transaction types ordered by total amount descending", "category": "complex"},
            {"id": "complex_limit", "query": "Top 5 transaction types by count", "category": "complex"},
            {"id": "complex_full", "query": "Show fraudulent transaction counts by type, ordered by count, limit 10", "category": "complex"},
            
            # Edge cases
            {"id": "edge_verbose", "query": "I want to know the total sum of all the amounts for transactions that are of type TRANSFER", "category": "edge"},
            {"id": "edge_casual", "query": "give me fraud stats", "category": "edge"},
            {"id": "edge_multi_type", "query": "Count transfers and cash-outs combined", "category": "edge"},
        ]
    
    def evaluate_case(self, case: dict, generated_sql: str | None, error: str | None) -> EvalResult:
        """
        Evaluate if generated SQL parses correctly.
        """
        case_id = case["id"]
        query = case["query"]
        
        if generated_sql is None:
            return EvalResult(
                case_id=case_id,
                passed=True,  # Clean failure is acceptable
                input_query=query,
                generated_sql=None,
                expected="Valid SQL or clean failure",
                actual="Clean failure (no SQL generated)",
                error=error,
                details={"category": case.get("category"), "failure_type": "generation_failed"}
            )
        
        # Try to parse the generated SQL
        try:
            self.parser.parse(generated_sql)
            parse_success = True
            parse_error = None
        except LarkError as e:
            parse_success = False
            parse_error = str(e)
        
        return EvalResult(
            case_id=case_id,
            passed=parse_success,
            input_query=query,
            generated_sql=generated_sql,
            expected="Grammar-valid SQL",
            actual="Valid" if parse_success else f"Parse error: {parse_error}",
            error=parse_error,
            details={"category": case.get("category"), "parse_success": parse_success}
        )


if __name__ == "__main__":

    eval = GrammarValidityEval()
    cases = eval.get_test_cases()
    print(f"Grammar Validity Eval: {len(cases)} test cases")
    for case in cases[:5]:
        print(f"  - [{case['category']}] {case['query']}")
