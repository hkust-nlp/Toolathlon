#!/usr/bin/env python3
"""
Snowflake client helpers built on top of the official Python connector.
Credentials are sourced from configs.token_key_session.
"""

import logging
import snowflake.connector
from snowflake.connector import DictCursor
from configs.token_key_session import all_token_key_session as GLOBAL_TOKENS

logger = logging.getLogger(__name__)


def _build_conn_kwargs() -> dict:
    """Build connection parameters from global token configuration."""
    kwargs = {
        'user': GLOBAL_TOKENS.snowflake_user,
        'password': GLOBAL_TOKENS.snowflake_password,
        'account': GLOBAL_TOKENS.snowflake_account,
        'warehouse': GLOBAL_TOKENS.snowflake_warehouse,
        'role': GLOBAL_TOKENS.snowflake_role,
    }
    if getattr(GLOBAL_TOKENS, 'snowflake_database', None):
        kwargs['database'] = GLOBAL_TOKENS.snowflake_database
    if getattr(GLOBAL_TOKENS, 'snowflake_schema', None):
        kwargs['schema'] = GLOBAL_TOKENS.snowflake_schema
    return kwargs


def get_connection():
    """Get a new Snowflake connection using configured credentials."""
    try:
        return snowflake.connector.connect(**_build_conn_kwargs())
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
        raise


def fetch_all(query: str) -> list:
    """Execute a query and return all results as a list of row arrays."""
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        return [list(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to execute query: {query}, Error: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def fetch_all_dict(query: str) -> list:
    """Execute a query and return all results as a list of dictionaries."""
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor(DictCursor)
        cur.execute(query)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Failed to execute query: {query}, Error: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def execute_query(query: str) -> int:
    """Execute a query and return the number of affected rows."""
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        logger.error(f"Failed to execute query: {query}, Error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
