#!/usr/bin/env python3

from typing import Optional

from .client import fetch_all


def fq_table_name(database: str, schema: str, table: str) -> str:
    return f"{database}.{schema}.\"{table}\""


def get_table_row_count(database: str, schema: str, table: str) -> int:
    table_fq = fq_table_name(database, schema, table)
    rows = fetch_all(f"SELECT COUNT(*) FROM {table_fq}")
    return int(rows[0][0]) if rows else 0


def row_exists(database: str, schema: str, table: str, where_clause: str) -> bool:
    table_fq = fq_table_name(database, schema, table)
    query = f"SELECT COUNT(*) FROM {table_fq} WHERE {where_clause}"
    rows = fetch_all(query)
    return bool(rows and int(rows[0][0]) > 0)


def escape_sql_literal(value: Optional[str]) -> str:
    if value is None:
        return ''
    return str(value).replace("'", "''")



