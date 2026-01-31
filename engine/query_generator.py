"""
Query Generator - GPT-5 with Context-Free Grammar Constraints

Handles NL → SQL generation using GPT-5's CFG tool feature.
The grammar ensures only valid, safe ClickHouse queries are produced.
"""

import os
import sys
from dataclasses import dataclass, asdict
from typing import Any

from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grammar.clickhouse_grammar import CLICKHOUSE_GRAMMAR, TOOL_DESCRIPTION


@dataclass
class GenerationResult:
    """Result of a query generation attempt."""
    success: bool
    sql: str | None
    error: str | None
    model: str | None = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class QueryGenerator:
    """
    Generates ClickHouse SQL from natural language using GPT-5 with CFG constraints.
    """
    
    def __init__(
        self,
        model: str = "gpt-5",
        api_key: str | None = None,
    ):
        """
        Initialize the query generator.
        
        Args:
            model: GPT-5 model variant (gpt-5, gpt-5-mini, gpt-5-nano)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
    def generate(self, natural_language_query: str) -> GenerationResult:
        """
        Generate a ClickHouse SQL query from natural language.
        
        Args:
            natural_language_query: The user's question in plain English
            
        Returns:
            GenerationResult with the SQL or error information
        """
        try:
            response = self.client.responses.create(
                model=self.model,
                input=self._build_prompt(natural_language_query),
                text={"format": {"type": "text"}},
                tools=[
                    {
                        "type": "custom",
                        "name": "clickhouse_query",
                        "description": TOOL_DESCRIPTION,
                        "format": {
                            "type": "grammar",
                            "syntax": "lark",
                            "definition": CLICKHOUSE_GRAMMAR,
                        },
                    }
                ],
                parallel_tool_calls=False,
            )
            
            # Extract the SQL from the tool call
            sql = self._extract_sql(response)
            
            if sql:
                return GenerationResult(
                    success=True,
                    sql=sql,
                    error=None,
                    model=self.model,
                )
            else:
                return GenerationResult(
                    success=False,
                    sql=None,
                    error="No SQL generated - model did not produce a tool call",
                    model=self.model,
                )
                
        except Exception as e:
            return GenerationResult(
                success=False,
                sql=None,
                error=str(e),
                model=self.model,
            )
    
    def _build_prompt(self, natural_language_query: str) -> str:
        """Build the prompt for the model."""
        return f"""You are an analytics assistant. Convert the following natural language question into a ClickHouse SQL query using the clickhouse_query tool.

The data is stored in a table called `Transactions` which contains transaction data:

SCHEMA:
- step: Time step (1-744, each step = 1 hour in a 30-day simulation)
- type: Action type ('CASH-IN', 'CASH-OUT', 'DEBIT', 'PAYMENT', 'TRANSFER')
- amount: Transaction/action amount (numeric)
- isFraud: Failure/anomaly indicator (0 = normal, 1 = failure detected)
- nameOrig: Origin agent identifier
- nameDest: Destination agent identifier
- oldbalanceOrg, newbalanceOrig: Origin balance before/after
- oldbalanceDest, newbalanceDest: Destination balance before/after

USER QUESTION: {natural_language_query}

Generate a SQL query using the clickhouse_query tool. Think carefully to ensure the query:
1. Answers the user's question
2. Conforms to the grammar constraints
3. Uses appropriate aggregations and filters"""

    def _extract_sql(self, response) -> str | None:
        """Extract the SQL from the response's tool call."""
        if not response.output:
            return None
            
        for item in response.output:
            # Look for custom tool call
            if hasattr(item, 'type') and item.type == 'custom_tool_call':
                if hasattr(item, 'input'):
                    return item.input
            # Also check for the name attribute
            if hasattr(item, 'name') and item.name == 'clickhouse_query':
                if hasattr(item, 'input'):
                    return item.input
                    
        return None


# Convenience function
def generate_sql(query: str, model: str = "gpt-5") -> GenerationResult:
    """Generate SQL from natural language query."""
    generator = QueryGenerator(model=model)
    return generator.generate(query)
