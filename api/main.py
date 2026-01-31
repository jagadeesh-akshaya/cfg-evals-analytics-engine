"""
FastAPI backend that handles:
1. Request validation
2. NL -> SQL generation via GPT-5 with CFG constraints  
3. Query execution against ClickHouse
4. Response formatting
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.query_generator import QueryGenerator, GenerationResult
from engine.clickhouse_client import ClickHouseClient, QueryResult

# Request/Response Models

class QueryRequest(BaseModel):
    """Request model for the /query endpoint."""
    question: str = Field(
        ..., 
        min_length=3,
        max_length=500,
        description="Natural language question about the data"
    )
    model: str = Field(
        default="gpt-5",
        description="GPT-5 model"
    )


class QueryResponse(BaseModel):
    """Response model for the /query endpoint."""
    success: bool
    question: str
    generated_sql: str | None
    result: dict | None
    error: str | None


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""
    status: str
    openai_configured: bool
    clickhouse_connected: bool


# App Lifecycle

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: verify configuration
    print("Starting CFG Eval Analytics Engine...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set")
    if not os.getenv("CLICKHOUSE_HOST"):
        print("WARNING: CLICKHOUSE_HOST not set")
    
    yield
    
    print("Shutting down...")


app = FastAPI(
    title="CFG Eval Analytics Engine",
    description="Natural language to ClickHouse SQL using GPT-5 with Context-Free Grammar constraints",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints

@app.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "service": "CFG Eval Analytics Engine",
        "version": "0.1.0",
        "endpoints": {
            "POST /query": "Submit a natural language question",
            "GET /health": "Check service health",
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    
    # Check ClickHouse connection
    clickhouse_connected = False
    if os.getenv("CLICKHOUSE_HOST"):
        try:
            client = ClickHouseClient()
            clickhouse_connected = client.test_connection()
            client.close()
        except Exception:
            pass
    
    status = "healthy" if (openai_configured and clickhouse_connected) else "degraded"
    
    return HealthResponse(
        status=status,
        openai_configured=openai_configured,
        clickhouse_connected=clickhouse_connected,
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Main query endpoint.
    
    Flow:
    1. Validate request
    2. Generate SQL from natural language using GPT-5 + CFG
    3. Execute SQL against ClickHouse
    4. Return results
    """
    
    # Step 1: Generate SQL using GPT-5 with CFG constraints
    generator = QueryGenerator(model=request.model)
    generation_result = generator.generate(request.question)
    
    if not generation_result.success:
        return QueryResponse(
            success=False,
            question=request.question,
            generated_sql=None,
            result=None,
            error=f"SQL generation failed: {generation_result.error}",
        )
    
    # Step 2: Execute the generated SQL against ClickHouse
    client = ClickHouseClient()
    try:
        query_result = client.execute(generation_result.sql)
    finally:
        client.close()
    
    if not query_result.success:
        return QueryResponse(
            success=False,
            question=request.question,
            generated_sql=generation_result.sql,
            result=None,
            error=f"Query execution failed: {query_result.error}",
        )
    
    # Step 3: Return successful response
    return QueryResponse(
        success=True,
        question=request.question,
        generated_sql=generation_result.sql,
        result={
            "data": query_result.data,
            "columns": query_result.columns,
            "row_count": query_result.row_count,
            "execution_time_ms": query_result.execution_time_ms,
        },
        error=None,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
