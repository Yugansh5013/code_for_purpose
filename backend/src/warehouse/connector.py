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

    def close(self):
        """Close the active connection."""
        if self._connection and not self._connection.is_closed():
            self._connection.close()
            logger.info("Snowflake connection closed")
        self._connection = None
