"""
OmniData -- Snowflake Column Comments & Jargon Overrides Seed

Non-destructive: uses ALTER TABLE ... ALTER COLUMN ... COMMENT
to attach JSON metadata to existing columns, and creates the
SYSTEM.JARGON_OVERRIDES table for persistent jargon storage.

Safe to re-run -- uses IF NOT EXISTS and idempotent ALTER statements.

Usage:
    cd backend
    python -m seed.snowflake_comments_seed
    python -m seed.snowflake_comments_seed --verify
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import get_settings
from src.warehouse.connector import SnowflakeConnector


# ============================================================
# Column Comment Definitions (JSON metadata)
# ============================================================

COLUMN_COMMENTS = [
    ("OMNIDATA_DB.SALES.AURA_SALES", "ACTUAL_SALES", {
        "display_name": "Total Sales",
        "aliases": ["money", "income", "earnings", "revenue", "sales", "turnover", "how much we made"],
        "unit": "GBP",
        "description": "Total transaction value in GBP before returns."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "UNITS_SOLD", {
        "display_name": "Units Sold",
        "aliases": ["volume", "quantity sold", "how many sold", "units"],
        "unit": "count",
        "description": "Number of individual product units sold."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "AD_SPEND", {
        "display_name": "Ad Spend",
        "aliases": ["advertising spend", "marketing spend", "ad budget", "marketing budget"],
        "unit": "GBP",
        "description": "Marketing spend attributed to the transaction in GBP."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "DISCOUNT_RATE", {
        "display_name": "Discount Rate",
        "aliases": ["discounts", "discount percentage", "price reduction", "markdown"],
        "unit": "percentage",
        "description": "Percentage discount applied to the transaction."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "GEO_TERRITORY", {
        "display_name": "Region",
        "aliases": ["region", "territory", "area", "location"],
        "unit": None,
        "description": "Geographic sales territory (North, South, East, West)."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "CHANNEL", {
        "display_name": "Sales Channel",
        "aliases": ["channel", "sales channel", "distribution channel"],
        "unit": None,
        "description": "Distribution channel: Online, Retail, or Partner."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "SALE_DATE", {
        "display_name": "Sale Date",
        "aliases": ["date", "transaction date", "when"],
        "unit": "date",
        "description": "Date of the transaction."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "PRODUCT_SKU", {
        "display_name": "Product Code",
        "aliases": ["product", "sku", "product code", "item"],
        "unit": None,
        "description": "Unique product identifier (SKU)."
    }),
    ("OMNIDATA_DB.SALES.AURA_SALES", "PRODUCT_CATEGORY", {
        "display_name": "Product Category",
        "aliases": ["category", "product type", "product category"],
        "unit": None,
        "description": "Product grouping: Electronics, Cables, Accessories."
    }),
    ("OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE", "PRODUCT_NAME", {
        "display_name": "Product Name",
        "aliases": ["product name", "name", "item name"],
        "unit": None,
        "description": "Full product display name."
    }),
    ("OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE", "RRP_GBP", {
        "display_name": "Retail Price",
        "aliases": ["price", "retail price", "rrp", "cost"],
        "unit": "GBP",
        "description": "Recommended retail price in GBP."
    }),
    ("OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE", "LAUNCH_DATE", {
        "display_name": "Launch Date",
        "aliases": ["launch date", "release date", "when launched"],
        "unit": "date",
        "description": "Date the product was first available."
    }),
    ("OMNIDATA_DB.RETURNS.RETURN_EVENTS", "RETURN_RATE", {
        "display_name": "Return Rate",
        "aliases": ["returns", "product returns", "refunds rate", "return percentage"],
        "unit": "percentage",
        "description": "Percentage of units sold that were returned."
    }),
    ("OMNIDATA_DB.RETURNS.RETURN_EVENTS", "REFUND_AMOUNT", {
        "display_name": "Refund Amount",
        "aliases": ["refund", "refund value", "money back"],
        "unit": "GBP",
        "description": "Amount refunded to the customer."
    }),
    ("OMNIDATA_DB.RETURNS.RETURN_EVENTS", "RETURN_REASON", {
        "display_name": "Return Reason",
        "aliases": ["reason", "why returned", "return reason"],
        "unit": None,
        "description": "Reason for the product return."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "CHURN_RATE", {
        "display_name": "Customer Churn Rate",
        "aliases": ["churn", "lost customers", "customer loss", "attrition", "cancellations"],
        "unit": "percentage",
        "description": "Percentage of customers who did not repurchase in the period."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "ACTIVE_CUSTOMER_COUNT", {
        "display_name": "Active Customers",
        "aliases": ["active customers", "engaged users", "buying customers"],
        "unit": "count",
        "description": "Customers who made at least one purchase in the period."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "NEW_CUSTOMER_COUNT", {
        "display_name": "New Customers",
        "aliases": ["new customers", "new signups", "acquisitions"],
        "unit": "count",
        "description": "First-time customers in the period."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "CHURNED_CUSTOMER_COUNT", {
        "display_name": "Lost Customers",
        "aliases": ["lost customers", "churned customers", "departed"],
        "unit": "count",
        "description": "Customers who did not return from the prior period."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "AVG_ORDER_VALUE", {
        "display_name": "Average Order Value",
        "aliases": ["average order", "aov", "average basket", "average spend"],
        "unit": "GBP",
        "description": "Mean transaction value across all orders."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "REPEAT_PURCHASE_RATE", {
        "display_name": "Repeat Purchase Rate",
        "aliases": ["repeat buyers", "returning customers", "loyalty rate", "repeat rate"],
        "unit": "percentage",
        "description": "Proportion of customers with two or more purchases."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "CUSTOMER_SEGMENT", {
        "display_name": "Customer Segment",
        "aliases": ["segment", "customer type", "customer group"],
        "unit": None,
        "description": "Customer grouping: Enterprise, SMB, Consumer."
    }),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "METRIC_MONTH", {
        "display_name": "Month",
        "aliases": ["month", "period", "time period"],
        "unit": "date",
        "description": "Calendar month for this metrics snapshot."
    }),
]


# ============================================================
# Default Jargon Overrides (migrated from jargon_overrides.yaml)
# ============================================================

DEFAULT_OVERRIDES = [
    ("OMNIDATA_DB.SALES.AURA_SALES", "the sales database", "snowflake"),
    ("OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE", "the product catalogue", "snowflake"),
    ("OMNIDATA_DB.RETURNS.RETURN_EVENTS", "the returns database", "snowflake"),
    ("OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", "the customer metrics database", "snowflake"),
    ("AURA_SALES", "sales records", "snowflake"),
    ("PRODUCT_CATALOGUE", "product catalogue", "snowflake"),
    ("RETURN_EVENTS", "return records", "snowflake"),
    ("CUSTOMER_METRICS", "customer metrics", "snowflake"),
    ("GEO_TERRITORY", "region", "snowflake"),
    ("SALE_DATE", "date", "snowflake"),
    ("PRODUCT_SKU", "product code", "snowflake"),
    ("PRODUCT_CATEGORY", "product category", "snowflake"),
    ("ACTUAL_SALES", "total sales", "snowflake"),
    ("UNITS_SOLD", "units sold", "snowflake"),
    ("AD_SPEND", "advertising spend", "snowflake"),
    ("DISCOUNT_RATE", "discount rate", "snowflake"),
    ("SALE_ID", "transaction ID", "snowflake"),
    ("METRIC_MONTH", "month", "snowflake"),
    ("ACTIVE_CUSTOMER_COUNT", "active customers", "snowflake"),
    ("NEW_CUSTOMER_COUNT", "new customers", "snowflake"),
    ("CHURNED_CUSTOMER_COUNT", "lost customers", "snowflake"),
    ("CHURN_RATE", "churn rate", "snowflake"),
    ("AVG_ORDER_VALUE", "average order value", "snowflake"),
    ("REPEAT_PURCHASE_RATE", "repeat purchase rate", "snowflake"),
    ("RETURN_RATE", "return rate", "snowflake"),
    ("REFUND_AMOUNT", "refund amount", "snowflake"),
    ("RETURN_REASON", "return reason", "snowflake"),
    ("RRP_GBP", "retail price", "snowflake"),
    ("CUSTOMER_SEGMENT", "customer segment", "snowflake"),
    ("ChurnRisk__c", "Churn Risk Score", "salesforce"),
    ("Region__c", "Region", "salesforce"),
    ("CustomerSegment__c", "Customer Segment", "salesforce"),
    ("LastPurchaseDate__c", "Last Purchase Date", "salesforce"),
    ("AnnualContractValue__c", "Annual Contract Value", "salesforce"),
    ("PartnerTier__c", "Partner Tier", "salesforce"),
    ("ProductSKU__c", "Product", "salesforce"),
    ("StageName", "deal stage", "salesforce"),
    ("CloseDate", "expected close date", "salesforce"),
    ("AccountId", "account", "salesforce"),
    ("OpportunityId", "deal", "salesforce"),
    ("SELECT", "query result", "sql"),
    ("GROUP BY", "grouped by", "sql"),
    ("ORDER BY", "sorted by", "sql"),
    ("WHERE", "filtered for", "sql"),
    ("ACV", "Annual Contract Value", "internal"),
    ("MRR", "Monthly Recurring Revenue", "internal"),
    ("CSAT", "Customer Satisfaction Score", "internal"),
    ("NPS", "Net Promoter Score", "internal"),
    ("YoY", "Year over Year", "internal"),
    ("MoM", "Month over Month", "internal"),
    ("QoQ", "Quarter over Quarter", "internal"),
]


# ============================================================
# Seed Logic
# ============================================================

def apply_column_comments(connector: SnowflakeConnector):
    """Apply JSON COMMENTs to all business-relevant columns."""
    print("Applying column comments...")
    connector.execute_ddl("USE DATABASE OMNIDATA_DB")

    success = 0
    for table, column, metadata in COLUMN_COMMENTS:
        comment_json = json.dumps(metadata, ensure_ascii=False)
        # Escape single quotes using SQL-standard doubling
        comment_escaped = comment_json.replace("'", "''")
        sql = f"ALTER TABLE {table} ALTER COLUMN {column} COMMENT '{comment_escaped}'"
        try:
            connector.execute_ddl(sql)
            success += 1
        except Exception as e:
            print(f"  [!] Failed to comment {table}.{column}: {e}")

    print(f"  [OK] Applied {success}/{len(COLUMN_COMMENTS)} column comments")


def create_overrides_table(connector: SnowflakeConnector):
    """Create the SYSTEM.JARGON_OVERRIDES table."""
    print("Creating SYSTEM.JARGON_OVERRIDES table...")
    connector.execute_ddl("USE DATABASE OMNIDATA_DB")
    connector.execute_ddl("CREATE SCHEMA IF NOT EXISTS OMNIDATA_DB.SYSTEM")
    connector.execute_ddl("""
        CREATE TABLE IF NOT EXISTS OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES (
            TERM VARCHAR NOT NULL,
            REPLACEMENT VARCHAR NOT NULL,
            CATEGORY VARCHAR DEFAULT 'custom',
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (TERM)
        )
    """)
    print("  [OK] Table created")


def seed_overrides(connector: SnowflakeConnector):
    """Seed the overrides table with default data (MERGE for idempotency)."""
    print("Seeding jargon overrides...")
    connector.execute_ddl("USE DATABASE OMNIDATA_DB")

    success = 0
    for term, replacement, category in DEFAULT_OVERRIDES:
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
        try:
            connector.execute_ddl(sql)
            success += 1
        except Exception as e:
            print(f"  [!] Failed to seed '{term}': {e}")

    print(f"  [OK] Seeded {success}/{len(DEFAULT_OVERRIDES)} override rules")


def verify(connector: SnowflakeConnector):
    """Verify the setup."""
    print("")
    print("Verifying...")

    # Check column comments
    try:
        rows = connector.execute_query("""
            SELECT TABLE_NAME, COLUMN_NAME, COMMENT
            FROM OMNIDATA_DB.INFORMATION_SCHEMA.COLUMNS
            WHERE COMMENT IS NOT NULL
              AND TABLE_SCHEMA IN ('SALES', 'PRODUCTS', 'RETURNS', 'CUSTOMERS')
            ORDER BY TABLE_NAME, COLUMN_NAME
        """)
        print(f"  Column Comments: {len(rows)} columns with JSON metadata")
        for row in rows[:5]:
            print(f"    {row['TABLE_NAME']}.{row['COLUMN_NAME']}: {row['COMMENT'][:60]}...")
        if len(rows) > 5:
            print(f"    ... and {len(rows) - 5} more")
    except Exception as e:
        print(f"  [FAIL] Column comments check failed: {e}")

    print()

    # Check overrides table
    try:
        rows = connector.execute_query(
            "SELECT COUNT(*) AS CNT FROM OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES"
        )
        count = rows[0]["CNT"]
        print(f"  Jargon Overrides: {count} rules in SYSTEM.JARGON_OVERRIDES")

        samples = connector.execute_query(
            "SELECT TERM, REPLACEMENT, CATEGORY FROM OMNIDATA_DB.SYSTEM.JARGON_OVERRIDES LIMIT 5"
        )
        for s in samples:
            print(f"    '{s['TERM']}' -> '{s['REPLACEMENT']}' [{s['CATEGORY']}]")
    except Exception as e:
        print(f"  [FAIL] Overrides table check failed: {e}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Seed Snowflake column comments & jargon overrides")
    parser.add_argument("--verify", action="store_true", help="Only verify, don't seed")
    parser.add_argument("--comments-only", action="store_true", help="Only apply column comments")
    parser.add_argument("--overrides-only", action="store_true", help="Only seed overrides table")
    args = parser.parse_args()

    settings = get_settings()
    connector = SnowflakeConnector(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
    )

    print("Testing Snowflake connection...")
    if not connector.test_connection():
        print("[FAIL] Connection failed. Check your credentials.")
        return
    print("[OK] Connected to Snowflake")
    print("")

    if args.verify:
        verify(connector)
        connector.close()
        return

    if args.comments_only:
        apply_column_comments(connector)
    elif args.overrides_only:
        create_overrides_table(connector)
        seed_overrides(connector)
    else:
        apply_column_comments(connector)
        create_overrides_table(connector)
        seed_overrides(connector)

    verify(connector)
    connector.close()
    print("[OK] Snowflake comments & overrides seed complete!")


if __name__ == "__main__":
    main()
