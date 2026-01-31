"""
ClickHouse SQL Grammar

This module defines a Lark grammar that constrains GPT-5 to generate only valid,
safe ClickHouse SQL queries against the transactions table.

Grammar enforces:
- Whitelisted table 
- Whitelisted columns
- Whitelisted aggregate functions
- Safe WHERE clause patterns (no injection possible)
- No dangerous operations (DROP, DELETE, UPDATE, etc.)
"""

# =============================================================================
# TABLE SCHEMA REFERENCE
# =============================================================================
# Column            Type      Description
# -----------------------------------------------------------------------------
# step              UInt16    Time step (1-744, each step = 1 hour, 30-day sim)
# type              String    Action type: CASH-IN, CASH-OUT, DEBIT, PAYMENT, TRANSFER
# amount            Float64   Transaction amount
# nameOrig          String    Origin agent ID
# oldbalanceOrg     Float64   Origin balance before
# newbalanceOrig    Float64   Origin balance after
# nameDest          String    Destination agent ID
# oldbalanceDest    Float64   Destination balance before
# newbalanceDest    Float64   Destination balance after
# isFraud           UInt8     Failure/anomaly flag (0 = normal, 1 = failure)
# =============================================================================


CLICKHOUSE_GRAMMAR = r"""
// =============================================================================
// CLICKHOUSE SQL GRAMMAR FOR AGENT TELEMETRY
// =============================================================================
// Constrains output to safe, read-only analytics queries.
// Only SELECT statements allowed. All tables/columns are whitelisted.
// =============================================================================

// -------------------- Tokens --------------------
// Compound keyword tokens (include leading space to avoid LALR conflicts)
KW_WHERE: " WHERE "
KW_AND: " AND "
KW_GROUP_BY: " GROUP BY "
KW_ORDER_BY: " ORDER BY "
KW_LIMIT: " LIMIT "
KW_BETWEEN: " BETWEEN "
KW_IN: " IN "
KW_ASC: " ASC"
KW_DESC: " DESC"

SP: " "
COMMA: ","
SEMI: ";"
LPAREN: "("
RPAREN: ")"
STAR: "*"

// -------------------- Start --------------------
start: select_stmt SEMI

// -------------------- SELECT Statement --------------------
select_stmt: "SELECT" SP select_list SP "FROM" SP table_name where_clause? group_by_clause? order_by_clause? limit_clause?

// -------------------- Select List --------------------
select_list: select_item (COMMA SP select_item)*

select_item: agg_func
           | groupable_col

// -------------------- Aggregate Functions --------------------
agg_func: "count" LPAREN STAR RPAREN
        | "count" LPAREN numeric_col RPAREN
        | "sum" LPAREN numeric_col RPAREN
        | "avg" LPAREN numeric_col RPAREN
        | "min" LPAREN numeric_col RPAREN
        | "max" LPAREN numeric_col RPAREN

// -------------------- Table (whitelisted) --------------------
table_name: "Transactions"

// -------------------- Columns (whitelisted) --------------------
// Numeric columns - can be used in aggregations
numeric_col: "step" | "amount" | "oldbalanceOrg" | "newbalanceOrig" | "oldbalanceDest" | "newbalanceDest" | "isFraud"

// Groupable columns - can appear in SELECT and GROUP BY
groupable_col: "type" | "isFraud" | "step"

// -------------------- WHERE Clause --------------------
where_clause: KW_WHERE condition and_condition*

and_condition: KW_AND condition

condition: step_condition
         | type_condition
         | fraud_condition
         | amount_condition

// Step (time) conditions
step_condition: "step" SP compare_op SP STEP_NUM
              | "step" KW_BETWEEN STEP_NUM KW_AND STEP_NUM

// Type conditions
type_condition: "type" SP "=" SP type_literal
              | "type" SP "!=" SP type_literal
              | "type" KW_IN LPAREN type_list RPAREN

type_literal: "'" type_value "'"
type_value: "CASH-IN" | "CASH-OUT" | "DEBIT" | "PAYMENT" | "TRANSFER"
type_list: type_literal (COMMA SP type_literal)*

// Fraud/failure conditions
fraud_condition: "isFraud" SP "=" SP FRAUD_VAL
               | "isFraud" SP "!=" SP FRAUD_VAL

// Amount conditions
amount_condition: "amount" SP compare_op SP AMOUNT_NUM
                | "amount" KW_BETWEEN AMOUNT_NUM KW_AND AMOUNT_NUM

// Comparison operators
compare_op: "=" | ">" | ">=" | "<" | "<="

// -------------------- GROUP BY --------------------
group_by_clause: KW_GROUP_BY groupable_col (COMMA SP groupable_col)*

// -------------------- ORDER BY --------------------
order_by_clause: KW_ORDER_BY order_item (COMMA SP order_item)*

order_item: order_target order_dir?

order_target: groupable_col
            | agg_func

order_dir: KW_ASC | KW_DESC

// -------------------- LIMIT --------------------
limit_clause: KW_LIMIT LIMIT_NUM

// -------------------- Terminal Patterns --------------------
// Step: 1-999 (covers 744 hours in simulation)
STEP_NUM: /[1-9][0-9]{0,2}/

// Amount: up to 12 digits with optional 2 decimal places
AMOUNT_NUM: /[0-9]{1,12}(\.[0-9]{1,2})?/

// Fraud flag: 0 or 1
FRAUD_VAL: "0" | "1"

// Limit: 1-9999
LIMIT_NUM: /[1-9][0-9]{0,3}/
"""


# Tool description
TOOL_DESCRIPTION = """Generates safe, read-only ClickHouse SQL queries for the transactions table.

You MUST use this tool to generate SQL. Reason carefully to ensure your query conforms to the grammar.

ALLOWED OPERATIONS:
- SELECT with aggregations: count(*), count(col), sum(col), avg(col), min(col), max(col)
- SELECT with groupable columns: type, isFraud, step
- FROM Transactions (this is the only allowed table)
- WHERE with conditions on: step, type, amount, isFraud
- GROUP BY: type, isFraud, step
- ORDER BY: columns or aggregations, with ASC/DESC
- LIMIT: 1-9999

COLUMN REFERENCE:
- step: Time step 1-744 (each step = 1 hour in 30-day simulation)
- type: 'CASH-IN', 'CASH-OUT', 'DEBIT', 'PAYMENT', 'TRANSFER'
- amount: Transaction amount (numeric)
- isFraud: Failure indicator (0 = normal, 1 = failure/anomaly)
- Balance columns: oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest

SUPPORTED FILTER PATTERNS:
- step >= 700, step BETWEEN 500 AND 700
- type = 'TRANSFER', type != 'PAYMENT', type IN ('TRANSFER', 'CASH-OUT')
- amount > 10000, amount BETWEEN 1000 AND 50000
- isFraud = 1, isFraud != 0

EXAMPLE VALID QUERIES:
- SELECT count(*) FROM Transactions;
- SELECT sum(amount) FROM Transactions WHERE type = 'TRANSFER';
- SELECT type, count(*) FROM Transactions WHERE isFraud = 1 GROUP BY type;
- SELECT sum(amount) FROM Transactions WHERE step BETWEEN 700 AND 744 AND type IN ('TRANSFER', 'CASH-OUT') GROUP BY type ORDER BY sum(amount) DESC LIMIT 10;
"""


# Example queries for testing
EXAMPLE_QUERIES = [
    # Basic aggregations
    "SELECT count(*) FROM Transactions;",
    "SELECT sum(amount) FROM Transactions;",
    "SELECT avg(amount) FROM Transactions;",
    
    # Simple filters
    "SELECT count(*) FROM Transactions WHERE isFraud = 1;",
    "SELECT sum(amount) FROM Transactions WHERE type = 'TRANSFER';",
    "SELECT count(*) FROM Transactions WHERE step >= 700;",
    
    # BETWEEN filters
    "SELECT count(*) FROM Transactions WHERE step BETWEEN 500 AND 700;",
    "SELECT sum(amount) FROM Transactions WHERE amount BETWEEN 10000 AND 100000;",
    
    # IN filters
    "SELECT count(*) FROM Transactions WHERE type IN ('TRANSFER', 'CASH-OUT');",
    
    # Not-equal filters
    "SELECT sum(amount) FROM Transactions WHERE type != 'PAYMENT';",
    "SELECT count(*) FROM Transactions WHERE isFraud != 0;",
    
    # Grouped queries
    "SELECT type, count(*) FROM Transactions GROUP BY type;",
    "SELECT type, sum(amount) FROM Transactions WHERE isFraud = 1 GROUP BY type;",
    "SELECT isFraud, avg(amount) FROM Transactions GROUP BY isFraud;",
    
    # Complex queries with multiple conditions
    "SELECT type, sum(amount) FROM Transactions WHERE step >= 500 AND isFraud = 1 GROUP BY type ORDER BY sum(amount) DESC LIMIT 10;",
    "SELECT type, count(*) FROM Transactions WHERE step BETWEEN 600 AND 744 AND type IN ('TRANSFER', 'CASH-OUT') AND amount > 50000 GROUP BY type;",
]


def get_grammar() -> str:
    return CLICKHOUSE_GRAMMAR


def get_tool_description() -> str:
    return TOOL_DESCRIPTION


def get_example_queries() -> list[str]:
    return EXAMPLE_QUERIES
