"""
OmniData — Snowflake Connector

Provides connection pooling and query execution against Snowflake.
Used by both the seed script and the runtime SQL branch.
"""

import logging
from typing import Optional
from contextlib import contextmanager

import snowflake.connector
from snowflake.connector import DictCursor

logger = logging.getLogger(__name__)


class SnowflakeConnector:
    """
    Manages Snowflake connections with automatic retry and timeout.
    
    Usage:
        connector = SnowflakeConnector(
            account="nt29883.me-central2.gcp",
            user="yugansh5013",
            password="...",
            warehouse="COMPUTE_WH",
            database="OMNIDATA_DB"
        )
        rows = connector.execute_query("SELECT * FROM SALES.AURA_SALES LIMIT 10")
    """

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        warehouse: str = "COMPUTE_WH",
        database: str = "OMNIDATA_DB",
        query_timeout: int = 30,
    ):
        self._account = account
        self._user = user
        self._password = password
        self._warehouse = warehouse
        self._database = database
        self._query_timeout = query_timeout
        self._connection: Optional[snowflake.connector.SnowflakeConnection] = None

    @contextmanager
    def _get_connection(self):
        """Get a Snowflake connection, creating one if needed."""
        try:
            if self._connection is None or self._connection.is_closed():
                self._connection = snowflake.connector.connect(
                    account=self._account,
                    user=self._user,
                    password=self._password,
                    warehouse=self._warehouse,
                    database=self._database,
                    login_timeout=15,
                    network_timeout=self._query_timeout,
                )
                logger.info("Snowflake connection established")
            yield self._connection
        except snowflake.connector.errors.DatabaseError as e:
            logger.error(f"Snowflake connection error: {e}")
            self._connection = None
            raise

    def execute_query(self, sql: str, params: Optional[dict] = None) -> list[dict]:
        """
        Execute a SQL query and return results as a list of dictionaries.
        Includes 1 automatic retry on transient connection errors.
        
        Args:
            sql: The SQL query to execute
            params: Optional query parameters
            
        Returns:
            List of dictionaries, one per row
        """
        last_error = None
        
        for attempt in range(2):  # Max 2 attempts (original + 1 retry)
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor(DictCursor)
                    cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {self._query_timeout}")
                    
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)
                    
                    rows = cursor.fetchall()
                    cursor.close()
                    logger.info(f"Query executed: {len(rows)} rows returned")
                    return rows
                    
            except (snowflake.connector.errors.DatabaseError,
                    snowflake.connector.errors.OperationalError) as e:
                last_error = e
                if attempt == 0:
                    logger.warning(f"Transient Snowflake error (retrying): {e}")
                    # Force reconnect on next attempt
                    self._connection = None
                else:
                    logger.error(f"SQL execution failed after retry: {e}")
                    
            except snowflake.connector.errors.ProgrammingError as e:
                # Programming errors (bad SQL) should not be retried
                logger.error(f"SQL execution error: {e}")
                raise
        
        raise last_error

    def execute_ddl(self, sql: str) -> None:
        """Execute a DDL statement (CREATE, DROP, etc.) — no result returned."""
        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(sql)
                logger.info(f"DDL executed successfully")
            except snowflake.connector.errors.ProgrammingError as e:
                logger.error(f"DDL execution error: {e}")
                raise
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """Test the connection by running a simple query."""
        try:
            result = self.execute_query("SELECT CURRENT_TIMESTAMP() AS ts")
            logger.info(f"Connection test passed: {result[0]['TS']}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    # ── Metric Dictionary & Jargon Override Methods ──────────

    def fetch_metric_dictionary(self) -> dict[str, dict]:
        """
        Read column-level JSON COMMENTs from INFORMATION_SCHEMA.
        Returns a dict keyed by COLUMN_NAME with parsed metadata.
        """
        import json as _json

        sql = """
            SELECT TABLE_NAME, COLUMN_NAME, COMMENT
            FROM OMNIDATA_DB.INFORMATION_SCHEMA.COLUMNS
            WHERE COMMENT IS NOT NULL
              AND TABLE_SCHEMA IN ('SALES', 'PRODUCTS', 'RETURNS', 'CUSTOMERS')
        """
        rows = self.execute_query(sql)

        dictionary: dict[str, dict] = {}
        for row in rows:
            col = row["COLUMN_NAME"]
            comment = row.get("COMMENT", "")
            if not comment:
                continue
            try:
                meta = _json.loads(comment)
                meta["table"] = f"OMNIDATA_DB.{row.get('TABLE_SCHEMA', 'SALES')}.{row['TABLE_NAME']}"
                meta["canonical_column"] = col
                dictionary[col] = meta
            except _json.JSONDecodeError:
                logger.debug(f"Non-JSON comment on {row['TABLE_NAME']}.{col}, skipping")

        logger.info(f"Fetched metric dictionary: {len(dictionary)} columns with metadata")
        return dictionary

    def get_jargon_overrides(self) -> dict[str, dict]:
        """
        Read all jargon override rules from SYSTEM.JARGON_OVERRIDES.
        Returns: { "TERM": {"replacement": "...", "category": "..."} }
        """
        sql = "SELECT TERM, REPLACEMENT, CATEGORY FROM OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES"
        rows = self.execute_query(sql)

        overrides: dict[str, dict] = {}
        for row in rows:
            overrides[row["TERM"]] = {
                "replacement": row["REPLACEMENT"],
                "category": row.get("CATEGORY", "custom"),
            }

        logger.info(f"Fetched {len(overrides)} jargon overrides from Snowflake")
        return overrides

    def save_jargon_override(self, term: str, replacement: str, category: str = "custom") -> None:
        """
        Upsert a jargon override into SYSTEM.JARGON_OVERRIDES (MERGE for idempotency).
        """
        term_esc = term.replace("'", "''")
        repl_esc = replacement.replace("'", "''")
        cat_esc = category.replace("'", "''")

        sql = f"""
            MERGE INTO OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES AS target
            USING (SELECT '{term_esc}' AS TERM, '{repl_esc}' AS REPLACEMENT, '{cat_esc}' AS CATEGORY) AS source
            ON target.TERM = source.TERM
            WHEN MATCHED THEN UPDATE SET
                REPLACEMENT = source.REPLACEMENT,
                CATEGORY = source.CATEGORY
            WHEN NOT MATCHED THEN INSERT (TERM, REPLACEMENT, CATEGORY)
                VALUES (source.TERM, source.REPLACEMENT, source.CATEGORY)
        """
        self.execute_ddl(sql)
        logger.info(f"Saved jargon override: '{term}' → '{replacement}'")

    def delete_jargon_override(self, term: str) -> bool:
        """
        Delete a jargon override from SYSTEM.JARGON_OVERRIDES.
        Returns True if a row was deleted.
        """
        term_esc = term.replace("'", "''")
        try:
            # Check if it exists first
            rows = self.execute_query(
                f"SELECT 1 AS X FROM OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES WHERE TERM = '{term_esc}'"
            )
            if not rows:
                return False
            self.execute_ddl(
                f"DELETE FROM OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES WHERE TERM = '{term_esc}'"
            )
            logger.info(f"Deleted jargon override: '{term}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete jargon override '{term}': {e}")
            return False

    def close(self):
        """Close the active connection."""
        if self._connection and not self._connection.is_closed():
            self._connection.close()
            logger.info("Snowflake connection closed")
        self._connection = None
