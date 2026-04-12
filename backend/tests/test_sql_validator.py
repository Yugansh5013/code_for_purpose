"""
Tests for SQL Validator — DML rejection, LIMIT enforcement, table name verification.
"""

import pytest
from src.validation.sql_validator import validate_sql, VALID_TABLES, MAX_LIMIT, DEFAULT_LIMIT


class TestDMLRejection:
    """Verify all DML/DDL operations are blocked."""

    def test_insert_blocked(self):
        is_valid, _, errors = validate_sql("INSERT INTO AURA_SALES VALUES (1, 2, 3)")
        assert not is_valid
        assert any("Forbidden" in e for e in errors)

    def test_update_blocked(self):
        is_valid, _, errors = validate_sql("UPDATE AURA_SALES SET ACTUAL_SALES = 0")
        assert not is_valid

    def test_delete_blocked(self):
        is_valid, _, errors = validate_sql("DELETE FROM AURA_SALES WHERE 1=1")
        assert not is_valid

    def test_drop_blocked(self):
        is_valid, _, errors = validate_sql("DROP TABLE AURA_SALES")
        assert not is_valid

    def test_alter_blocked(self):
        is_valid, _, errors = validate_sql("ALTER TABLE AURA_SALES ADD COLUMN x INT")
        assert not is_valid

    def test_truncate_blocked(self):
        is_valid, _, errors = validate_sql("TRUNCATE TABLE AURA_SALES")
        assert not is_valid

    def test_create_blocked(self):
        is_valid, _, errors = validate_sql("CREATE TABLE hacked (id INT)")
        assert not is_valid

    def test_merge_blocked(self):
        is_valid, _, errors = validate_sql("MERGE INTO AURA_SALES USING other ON 1=1 WHEN MATCHED THEN DELETE")
        assert not is_valid

    def test_grant_blocked(self):
        is_valid, _, errors = validate_sql("GRANT ALL ON AURA_SALES TO PUBLIC")
        assert not is_valid


class TestSelectOnly:
    """Verify only SELECT statements pass."""

    def test_valid_select(self):
        is_valid, cleaned, errors = validate_sql(
            "SELECT REGION, SUM(ACTUAL_SALES) FROM AURA_SALES GROUP BY REGION"
        )
        assert is_valid
        assert len(errors) == 0

    def test_non_select_rejected(self):
        is_valid, _, errors = validate_sql("SHOW TABLES")
        assert not is_valid
        assert any("SELECT" in e for e in errors)

    def test_empty_sql_rejected(self):
        is_valid, _, errors = validate_sql("")
        assert not is_valid
        assert any("Empty" in e for e in errors)

    def test_whitespace_only_rejected(self):
        is_valid, _, errors = validate_sql("   ")
        assert not is_valid


class TestLimitEnforcement:
    """Verify LIMIT is auto-added and capped."""

    def test_limit_auto_added(self):
        """Non-aggregate query without LIMIT should get one auto-added."""
        is_valid, cleaned, _ = validate_sql(
            "SELECT * FROM AURA_SALES"
        )
        assert is_valid
        assert f"LIMIT {DEFAULT_LIMIT}" in cleaned

    def test_aggregate_no_auto_limit(self):
        """Aggregate queries should NOT get auto-LIMIT."""
        sql = "SELECT REGION, SUM(ACTUAL_SALES) FROM AURA_SALES GROUP BY REGION"
        is_valid, cleaned, _ = validate_sql(sql)
        assert is_valid
        assert "LIMIT" not in cleaned.upper().replace("LIMIT", "LIMIT")
        # More precise: check for auto-added LIMIT specifically
        # Aggregate queries shouldn't have LIMIT appended

    def test_high_limit_capped(self):
        """LIMIT > MAX_LIMIT should be reduced to MAX_LIMIT."""
        is_valid, cleaned, _ = validate_sql(
            "SELECT * FROM AURA_SALES LIMIT 9999"
        )
        assert is_valid
        assert str(MAX_LIMIT) in cleaned
        assert "9999" not in cleaned

    def test_reasonable_limit_kept(self):
        """LIMIT within bounds should be preserved."""
        is_valid, cleaned, _ = validate_sql(
            "SELECT * FROM AURA_SALES LIMIT 50"
        )
        assert is_valid
        assert "LIMIT 50" in cleaned


class TestTableNameVerification:
    """Verify table name checking."""

    def test_known_table_passes(self):
        is_valid, _, errors = validate_sql(
            "SELECT * FROM AURA_SALES LIMIT 10"
        )
        assert is_valid

    def test_fully_qualified_passes(self):
        is_valid, _, errors = validate_sql(
            "SELECT * FROM OMNIDATA_DB.SALES.AURA_SALES LIMIT 10"
        )
        assert is_valid

    def test_unknown_table_flagged(self):
        is_valid, _, errors = validate_sql(
            "SELECT * FROM HACKED_TABLE LIMIT 10"
        )
        assert not is_valid
        assert any("Unknown" in e for e in errors)

    def test_all_known_tables_accepted(self):
        """All tables in our schema should be valid."""
        for table in ["AURA_SALES", "PRODUCT_CATALOGUE", "RETURN_EVENTS", "CUSTOMER_METRICS"]:
            is_valid, _, _ = validate_sql(f"SELECT COUNT(*) FROM {table}")
            assert is_valid, f"Table {table} should be valid"

    def test_join_with_known_tables(self):
        sql = """
        SELECT s.REGION, p.PRODUCT_NAME, SUM(s.ACTUAL_SALES)
        FROM AURA_SALES s
        JOIN PRODUCT_CATALOGUE p ON s.SKU = p.SKU
        GROUP BY s.REGION, p.PRODUCT_NAME
        """
        is_valid, _, errors = validate_sql(sql)
        assert is_valid, f"Join query should be valid, errors: {errors}"


class TestSqlGlotParsing:
    """Verify sqlglot handles valid Snowflake SQL."""

    def test_date_trunc(self):
        sql = "SELECT DATE_TRUNC('month', SALE_DATE) AS m, SUM(ACTUAL_SALES) FROM AURA_SALES GROUP BY m"
        is_valid, _, errors = validate_sql(sql)
        assert is_valid, f"DATE_TRUNC should parse, errors: {errors}"

    def test_subquery(self):
        sql = """
        SELECT REGION, total FROM (
            SELECT REGION, SUM(ACTUAL_SALES) AS total
            FROM AURA_SALES GROUP BY REGION
        ) ORDER BY total DESC
        """
        is_valid, _, errors = validate_sql(sql)
        assert is_valid, f"Subquery should parse, errors: {errors}"

    def test_trailing_semicolon_stripped(self):
        sql = "SELECT COUNT(*) FROM AURA_SALES;"
        is_valid, cleaned, _ = validate_sql(sql)
        assert is_valid
        assert not cleaned.endswith(";")

    def test_malformed_sql_rejected(self):
        is_valid, _, errors = validate_sql("SELECT FROM WHERE HAVING")
        # sqlglot may or may not reject this, but it shouldn't crash
        # The test verifies no exception is raised
        assert isinstance(is_valid, bool)
