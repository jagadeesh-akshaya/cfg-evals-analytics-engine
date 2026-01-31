"""
End-to-End Query API Tests

Tests the full NL → SQL → ClickHouse flow via the API.
Run with: pytest tests/test_query_api.py -v
"""

import pytest
import requests

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "http://localhost:8000"
QUERY_ENDPOINT = f"{BASE_URL}/query"
HEALTH_ENDPOINT = f"{BASE_URL}/health"


# =============================================================================
# Test Cases - Organized by Query Category
# =============================================================================

# Each test case: (name, question, expected_sql_contains, expected_result_check)
# expected_result_check is a lambda that validates the result

BASIC_AGGREGATION_TESTS = [
    (
        "count_all_transactions",
        "How many transactions are there?",
        ["count(*)", "FROM Transactions"],
        lambda r: r["row_count"] == 1 and r["data"][0]["count()"] > 0,
    ),
    (
        "sum_all_amounts",
        "What is the total transaction amount?",
        ["sum(amount)", "FROM Transactions"],
        lambda r: r["row_count"] == 1,
    ),
    (
        "average_transaction_amount",
        "What is the average transaction amount?",
        ["avg(amount)", "FROM Transactions"],
        lambda r: r["row_count"] == 1,
    ),
]

FILTER_TESTS = [
    (
        "count_fraudulent_transactions",
        "How many fraudulent transactions are there?",
        ["count(*)", "isFraud = 1"],
        lambda r: r["row_count"] == 1 and r["data"][0]["count()"] > 0,
    ),
    (
        "count_transfers",
        "How many transfer transactions are there?",
        ["count(*)", "type = 'TRANSFER'"],
        lambda r: r["row_count"] == 1,
    ),
    (
        "sum_cash_out_amounts",
        "What is the total amount of cash-out transactions?",
        ["sum(amount)", "type = 'CASH-OUT'"],
        lambda r: r["row_count"] == 1,
    ),
    (
        "count_non_payment_transactions",
        "How many transactions are not payments?",
        ["count(*)", "type != 'PAYMENT'"],
        lambda r: r["row_count"] == 1,
    ),
]

GROUP_BY_TESTS = [
    (
        "count_by_transaction_type",
        "How many transactions are there for each type?",
        ["count(*)", "GROUP BY type"],
        lambda r: r["row_count"] == 5,  # 5 transaction types
    ),
    (
        "sum_amount_by_type",
        "What is the total amount for each transaction type?",
        ["sum(amount)", "GROUP BY type"],
        lambda r: r["row_count"] == 5,
    ),
    (
        "avg_amount_by_fraud_status",
        "What is the average amount for fraudulent vs non-fraudulent transactions?",
        ["avg(amount)", "GROUP BY isFraud"],
        lambda r: r["row_count"] == 2,  # 0 and 1
    ),
]

TIME_BASED_TESTS = [
    (
        "transactions_after_step_700",
        "How many transactions happened after step 700?",
        ["count(*)", "step >=", "700"],
        lambda r: r["row_count"] == 1,
    ),
    (
        "last_24_hours_transfers",
        "How many transfers happened in the last 24 hours of the simulation?",
        ["count(*)", "type = 'TRANSFER'", "step", "BETWEEN", "721", "744"],
        lambda r: r["row_count"] == 1,
    ),
    (
        "fraud_in_time_range",
        "How many fraudulent transactions occurred between step 500 and 600?",
        ["count(*)", "isFraud = 1", "step", "BETWEEN", "500", "600"],
        lambda r: r["row_count"] == 1,
    ),
]

COMPLEX_QUERY_TESTS = [
    (
        "fraud_by_type_ordered",
        "Show me the count of fraudulent transactions by type, ordered by count descending",
        ["count(*)", "isFraud = 1", "GROUP BY type", "ORDER BY", "DESC"],
        lambda r: r["row_count"] >= 1,
    ),
    (
        "large_transfers",
        "How many transfer transactions are above 100000 in amount?",
        ["count(*)", "type = 'TRANSFER'", "amount >", "100000"],
        lambda r: r["row_count"] == 1,
    ),
    (
        "multi_filter_with_in",
        "What is the total amount for transfers and cash-outs?",
        ["sum(amount)", "type", "IN"],
        lambda r: r["row_count"] == 1,
    ),
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def api_health():
    """Verify API is healthy before running tests."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        health = response.json()
        if health["status"] != "healthy":
            pytest.skip(f"API not healthy: {health}")
        return health
    except requests.exceptions.ConnectionError:
        pytest.skip("API server not running. Start with: uvicorn api.main:app --reload")


# =============================================================================
# Helper Functions
# =============================================================================

def run_query(question: str) -> dict:
    """Send a query to the API and return the response."""
    response = requests.post(
        QUERY_ENDPOINT,
        json={"question": question},
        timeout=60,  # GPT-5 can take a while
    )
    return response.json()


def assert_sql_contains(sql: str, expected_fragments: list[str], case_insensitive: bool = False):
    """Assert that generated SQL contains expected fragments."""
    check_sql = sql.lower() if case_insensitive else sql
    for fragment in expected_fragments:
        check_fragment = fragment.lower() if case_insensitive else fragment
        assert check_fragment in check_sql, f"Expected '{fragment}' in SQL: {sql}"


# =============================================================================
# Test Classes
# =============================================================================

class TestHealthCheck:
    """Tests for the health endpoint."""
    
    def test_health_endpoint_returns_200(self):
        """Health endpoint should return 200 OK."""
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        assert response.status_code == 200
    
    def test_health_shows_services_configured(self, api_health):
        """Health check should show OpenAI and ClickHouse configured."""
        assert api_health["openai_configured"] is True
        assert api_health["clickhouse_connected"] is True


class TestBasicAggregations:
    """Tests for basic aggregation queries (count, sum, avg)."""
    
    @pytest.mark.parametrize("name,question,expected_sql,result_check", BASIC_AGGREGATION_TESTS)
    def test_basic_aggregation(self, api_health, name, question, expected_sql, result_check):
        """Test basic aggregation queries."""
        response = run_query(question)
        
        assert response["success"] is True, f"Query failed: {response.get('error')}"
        assert response["generated_sql"] is not None
        assert_sql_contains(response["generated_sql"], expected_sql)
        assert result_check(response["result"]), f"Result check failed for {name}"


class TestFilterQueries:
    """Tests for queries with WHERE clause filters."""
    
    @pytest.mark.parametrize("name,question,expected_sql,result_check", FILTER_TESTS)
    def test_filter_query(self, api_health, name, question, expected_sql, result_check):
        """Test queries with various filter conditions."""
        response = run_query(question)
        
        assert response["success"] is True, f"Query failed: {response.get('error')}"
        assert response["generated_sql"] is not None
        assert_sql_contains(response["generated_sql"], expected_sql)
        assert result_check(response["result"]), f"Result check failed for {name}"


class TestGroupByQueries:
    """Tests for queries with GROUP BY clauses."""
    
    @pytest.mark.parametrize("name,question,expected_sql,result_check", GROUP_BY_TESTS)
    def test_group_by_query(self, api_health, name, question, expected_sql, result_check):
        """Test queries with GROUP BY."""
        response = run_query(question)
        
        assert response["success"] is True, f"Query failed: {response.get('error')}"
        assert response["generated_sql"] is not None
        assert_sql_contains(response["generated_sql"], expected_sql)
        assert result_check(response["result"]), f"Result check failed for {name}"


class TestTimeBasedQueries:
    """Tests for time-based queries using step column."""
    
    @pytest.mark.parametrize("name,question,expected_sql,result_check", TIME_BASED_TESTS)
    def test_time_based_query(self, api_health, name, question, expected_sql, result_check):
        """Test time-window queries."""
        response = run_query(question)
        
        assert response["success"] is True, f"Query failed: {response.get('error')}"
        assert response["generated_sql"] is not None
        assert_sql_contains(response["generated_sql"], expected_sql)
        assert result_check(response["result"]), f"Result check failed for {name}"


class TestComplexQueries:
    """Tests for complex queries combining multiple features."""
    
    @pytest.mark.parametrize("name,question,expected_sql,result_check", COMPLEX_QUERY_TESTS)
    def test_complex_query(self, api_health, name, question, expected_sql, result_check):
        """Test complex queries with multiple clauses."""
        response = run_query(question)
        
        assert response["success"] is True, f"Query failed: {response.get('error')}"
        assert response["generated_sql"] is not None
        assert_sql_contains(response["generated_sql"], expected_sql)
        assert result_check(response["result"]), f"Result check failed for {name}"


class TestGrammarEnforcement:
    """Tests verifying that CFG prevents invalid queries."""
    
    def test_sql_ends_with_semicolon(self, api_health):
        """Generated SQL should always end with semicolon (grammar enforced)."""
        response = run_query("How many transactions are there?")
        assert response["success"] is True
        assert response["generated_sql"].strip().endswith(";")
    
    def test_only_transactions_table(self, api_health):
        """Grammar should only allow Transactions table."""
        response = run_query("Count all records")
        assert response["success"] is True
        assert "FROM Transactions" in response["generated_sql"]


# =============================================================================
# Run with: pytest tests/test_query_api.py -v
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
