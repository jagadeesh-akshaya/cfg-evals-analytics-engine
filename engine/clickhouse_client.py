"""
Handles connection and query execution against ClickHouse Cloud.
"""

import os
import time
from dataclasses import dataclass, asdict
from typing import Any

import clickhouse_connect


@dataclass
class QueryResult:
    """Result of a ClickHouse query execution."""
    success: bool
    data: list[dict] | None
    columns: list[str] | None
    row_count: int
    execution_time_ms: float | None
    error: str | None
    
    def to_dict(self) -> dict:
        return asdict(self)


class ClickHouseClient:
    """
    Client for executing queries against ClickHouse Cloud.
    """
    
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        database: str | None = None,
        secure: bool = True,
    ):
    
        self.host = host or os.getenv("CLICKHOUSE_HOST")
        self.port = port or int(os.getenv("CLICKHOUSE_PORT", "8443"))
        self.username = username or os.getenv("CLICKHOUSE_USER", "default")
        self.password = password or os.getenv("CLICKHOUSE_PASSWORD", "")
        self.database = database or os.getenv("CLICKHOUSE_DATABASE", "default")
        self.secure = secure
        
        self._client = None
        
    def _get_client(self):
        """Get or create the ClickHouse client connection."""
        if self._client is None:
            if not self.host:
                raise ValueError("CLICKHOUSE_HOST not configured")
            
            self._client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                database=self.database,
                secure=self.secure,
            )
        return self._client
    
    def execute(self, sql: str) -> QueryResult:
        """
        Execute a SQL query and return results.
        
        Args:
            sql: The SQL query to execute
            
        Returns:
            QueryResult with data or error information
        """
        try:
            client = self._get_client()
            
            start_time = time.perf_counter()
            result = client.query(sql)
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Convert to list of dicts for JSON serialization
            columns = list(result.column_names)
            data = []
            for row in result.result_rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    
                    if isinstance(value, (bytes,)):
                        value = value.decode('utf-8')
                    row_dict[col] = value
                data.append(row_dict)
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=len(data),
                execution_time_ms=round(execution_time_ms, 2),
                error=None,
            )
            
        except Exception as e:
            return QueryResult(
                success=False,
                data=None,
                columns=None,
                row_count=0,
                execution_time_ms=None,
                error=str(e),
            )
    
    def test_connection(self) -> bool:
        result = self.execute("SELECT 1")
        return result.success
    
    def close(self):
        if self._client is not None:
            self._client.close()
            self._client = None


def execute_query(sql: str) -> QueryResult:
    """Execute a SQL query using default configuration."""
    client = ClickHouseClient()
    try:
        return client.execute(sql)
    finally:
        client.close()
