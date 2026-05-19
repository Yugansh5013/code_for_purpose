"""
OmniData — Neon (PostgreSQL) Connector

Drop-in replacement for the original SnowflakeConnector, after the
Snowflake free trial expired. Uses Neon serverless PostgreSQL via psycopg2.

⚠️ Migration Note:
    Original implementation used Snowflake (snowflake-connector-python).
    Migrated to Neon (PostgreSQL) on 2026-05-19 because the Snowflake
    30-day free trial expired. All table schemas and data were re-seeded
    into Neon using seed/neon_seed.py. The original seed/snowflake_seed.py
    is preserved for reference.

Public API is identical to SnowflakeConnector so no callers had to change.
"""

import logging
from typing import Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class NeonConnector:
    """
    Manages a Neon (PostgreSQL) connection.

    Exposes the same public API as the original SnowflakeConnector:
        execute_query()         → list[dict]
        execute_ddl()           → None
        test_connection()       → bool
        get_jargon_overrides()  → dict
        save_jargon_override()  → None
        delete_jargon_override()→ bool
        fetch_metric_dictionary()→ dict
        close()                 → None

    Usage:
        connector = NeonConnector(database_url="postgresql://...")
        rows = connector.execute_query("SELECT * FROM aura_sales LIMIT 10")
    """

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._connection: Optional[psycopg2.extensions.connection] = None

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Return a live connection, reconnecting if necessary."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                self._database_url,
                connect_timeout=15,
            )
            self._connection.autocommit = True
            logger.info("Neon connection established")
        return self._connection

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> list[dict]:
        """
        Execute a SELECT query and return results as a list of dicts.
        Automatically retries once on a broken connection.
        """
        last_error = None
        for attempt in range(2):
            try:
                conn = self._get_connection()
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(sql, params)
                    rows = [dict(r) for r in cur.fetchall()]
                    logger.info(f"Query executed: {len(rows)} rows returned")
                    return rows
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                if attempt == 0:
                    logger.warning(f"Transient Neon error (retrying): {e}")
                    self._connection = None  # force reconnect
                else:
                    logger.error(f"SQL execution failed after retry: {e}")
            except psycopg2.ProgrammingError as e:
                logger.error(f"SQL execution error: {e}")
                raise
        raise last_error

    def execute_ddl(self, sql: str) -> None:
        """Execute a DDL or DML statement (no result returned)."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(sql)
            logger.info("DDL/DML executed successfully")
        except psycopg2.Error as e:
            logger.error(f"DDL execution error: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the connection with a simple query."""
        try:
            result = self.execute_query("SELECT NOW() AS ts")
            logger.info(f"Connection test passed: {result[0]['ts']}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    # ── Jargon Overrides ──────────────────────────────────────

    def get_jargon_overrides(self) -> dict[str, dict]:
        """
        Read all jargon override rules from public.jargon_overrides.
        Returns: { "TERM": {"replacement": "...", "category": "..."} }
        """
        sql = "SELECT term, replacement, category FROM jargon_overrides"
        rows = self.execute_query(sql)

        overrides: dict[str, dict] = {}
        for row in rows:
            overrides[row["term"]] = {
                "replacement": row["replacement"],
                "category": row.get("category", "custom"),
            }

        logger.info(f"Fetched {len(overrides)} jargon overrides from Neon")
        return overrides

    def save_jargon_override(self, term: str, replacement: str, category: str = "custom") -> None:
        """Upsert a jargon override (INSERT … ON CONFLICT DO UPDATE)."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jargon_overrides (term, replacement, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (term) DO UPDATE
                    SET replacement = EXCLUDED.replacement,
                        category    = EXCLUDED.category
                """,
                (term, replacement, category),
            )
        logger.info(f"Saved jargon override: '{term}' → '{replacement}'")

    def delete_jargon_override(self, term: str) -> bool:
        """Delete a jargon override. Returns True if a row was deleted."""
        try:
            rows = self.execute_query(
                "SELECT 1 AS x FROM jargon_overrides WHERE term = %s", (term,)
            )
            if not rows:
                return False
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM jargon_overrides WHERE term = %s", (term,))
            logger.info(f"Deleted jargon override: '{term}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete jargon override '{term}': {e}")
            return False

    # ── Metric Dictionary ─────────────────────────────────────

    def fetch_metric_dictionary(self) -> dict[str, dict]:
        """
        In the original Snowflake implementation, this read INFORMATION_SCHEMA
        column comments. In Neon, column comments are not commonly used, so we
        return an empty dict and let the YAML metric_dictionary.yaml take over
        (which is the primary source anyway).
        """
        logger.info("Metric dictionary: using YAML source (Neon has no column comments)")
        return {}

    def close(self):
        """Close the active connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Neon connection closed")
        self._connection = None
