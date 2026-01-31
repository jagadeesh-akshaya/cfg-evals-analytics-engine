# CFG-Constrained SQL Generation

A natural language to SQL system that uses GPT-5's context-free grammar (CFG) support to generate **provably safe** ClickHouse queries. Instead of hoping the model produces valid SQL, the grammar enforces it at the decoding level.

**Live Demo:** [frontend-two-puce-42.vercel.app](https://frontend-two-puce-42.vercel.app)

---

## The Problem

When LLMs generate SQL from natural language, there's always risk: malformed queries, SQL injection, unauthorized table access, or dangerous operations like `DROP TABLE`. Prompt engineering helps, but it's not a guarantee.

## The Solution

GPT-5 supports custom tools with grammar constraints. By defining a Lark CFG that only permits safe query patterns, the model **cannot** produce output that violates the grammar.

The grammar whitelists:
- One table (`Transactions`)
- Specific columns (`step`, `type`, `amount`, `isFraud`, etc.)
- Read-only operations (`SELECT` with aggregations)
- Safe filter patterns (`WHERE`, `BETWEEN`, `IN`)

---

## Architecture

```
User Question
     │
     ▼
┌─────────────────┐
│  React Frontend │  (Vercel)
│  TypeScript     │
└────────┬────────┘
         │ POST /query
         ▼
┌─────────────────┐
│  FastAPI        │  
│  Backend        │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌──────────────┐
│ GPT-5 │  │  ClickHouse  │
│ + CFG │  │    Cloud     │
└───────┘  │   
           └──────────────┘
```

## Project Structure

```
├── api/                    # FastAPI backend
│   └── main.py            
├── engine/                 # Core logic
│   ├── query_generator.py  # GPT-5 integration with CFG tool
│   └── clickhouse_client.py
├── grammar/
│   ├── clickhouse_grammar.py  # Lark grammar definition
│   └── test_grammar.py        # Grammar validation tests
├── evals/                  # Evaluation suite
│   ├── grammar_validity.py    # Does output always parse?
│   ├── semantic_correctness.py # Does SQL match intent + return correct data?
│   ├── safety_guardrails.py   # Can adversarial inputs break it?
│   └── robustness.py          # Edge cases and boundaries
├── frontend/               # React + TypeScript + Tailwind
└── tests/                  # API integration tests
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key (GPT-5 access)
- ClickHouse Cloud instance

### Backend

```bash
cd cfg-evals-analytics-engine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run locally
uvicorn api.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Evaluations

```bash
# Start the backend first, then:
python -m evals.runner
```

## The Grammar

The CFG is defined in Lark syntax. Here's the core structure:

```
start: select_stmt ";"

select_stmt: "SELECT" select_list "FROM" table_name 
             where_clause? group_by_clause? order_by_clause? limit_clause?

table_name: "Transactions"

agg_func: "count" "(" "*" ")"
        | "sum" "(" numeric_col ")"
        | "avg" "(" numeric_col ")"
        ...

numeric_col: "step" | "amount" | "oldbalanceOrg" | ...
```

Every production rule restricts what the model can output. There's no rule for `DROP`, `DELETE`, `UPDATE`, or accessing tables other than `Transactions`—so the model simply can't generate them.

## Evaluations

Four evaluation suites test different aspects:

| Eval | What it tests | Pass criteria |
|------|---------------|---------------|
| **Grammar Validity** | Does output always conform to the CFG? | 100% must parse |
| **Semantic Correctness** | Does the SQL answer the question correctly? | Query results match expected |
| **Safety Guardrails** | Can adversarial prompts cause unsafe output? | No dangerous patterns |
| **Robustness** | How does it handle edge cases? | Graceful failure or correct handling |

## Dataset

The system runs against 6.3M rows of synthetic transaction data (PaySim fraud detection dataset).

## Deployment

- **Backend:** Railway (Docker)
- **Frontend:** Vercel
- **Database:** ClickHouse Cloud

The backend Dockerfile and `railway.toml` are included for deployment.

---
