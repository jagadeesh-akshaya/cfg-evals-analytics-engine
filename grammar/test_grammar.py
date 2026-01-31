"""
Test script to validate the Lark grammar parses correctly.

Run: python -m grammar.test_grammar
(from the cfg-evals-analytics-engine directory)

Or: python grammar/test_grammar.py
"""

from lark import Lark, LarkError
from clickhouse_grammar import CLICKHOUSE_GRAMMAR, EXAMPLE_QUERIES


def test_grammar():
    # Create the parser
    print("Loading grammar...")
    try:
        parser = Lark(CLICKHOUSE_GRAMMAR, start='start', parser='lalr')
        print("✓ Grammar loaded successfully\n")
    except Exception as e:
        print(f"✗ Failed to load grammar: {e}")
        return
    
    # Test each example query
    print("Testing example queries:")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for query in EXAMPLE_QUERIES:
        try:
            parser.parse(query)
            print(f"✓ {query}")
            passed += 1
        except LarkError as e:
            print(f"✗ {query}")
            print(f"  Error: {e}\n")
            failed += 1
    
    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    # Test some queries that SHOULD fail
    print("\n" + "=" * 60)
    print("Testing invalid queries (should be rejected):")
    print("-" * 60)
    
    invalid_queries = [
        ("DROP TABLE transactions;", "DROP not allowed"),
        ("SELECT * FROM Transactions;", "SELECT * not allowed"),
        ("SELECT count(*) FROM other_table;", "Wrong table name"),
        ("DELETE FROM Transactions WHERE isFraud = 1;", "DELETE not allowed"),
        ("SELECT count(*) FROM Transactions WHERE type = 'INVALID';", "Invalid type value"),
    ]
    
    for query, reason in invalid_queries:
        try:
            parser.parse(query)
            print(f"✗ SHOULD HAVE FAILED: {query}")
            print(f"  Reason: {reason}")
        except LarkError:
            print(f"✓ Correctly rejected: {query}")
    
    print("-" * 60)


if __name__ == "__main__":
    test_grammar()
