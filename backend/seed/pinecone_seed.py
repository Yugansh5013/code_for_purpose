"""
OmniData — Pinecone Seed Script

Seeds the omnidata-hybrid index with:
  - schema_store namespace (5 enriched table descriptions)
  - examples_store namespace (30 verified Q→SQL pairs)

Uses Pinecone integrated inference — records are auto-embedded
at upsert time. No local embedding model needed.

Idempotent: uses deterministic IDs, re-running overwrites not duplicates.

Usage:
    cd backend
    python -m seed.pinecone_seed
    python -m seed.pinecone_seed --verify
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import get_settings
from src.vector.pinecone_client import PineconeClient


# ============================================================
# Schema Store — 5 enriched table descriptions
# ============================================================

SCHEMA_DOCUMENTS = [
    {
        "_id": "schema_AURA_SALES",
        "text": (
            "Table OMNIDATA_DB.SALES.AURA_SALES tracks daily revenue, money made, total sales, "
            "and income for Aura Retail broken down by geographic region (North, South, East, West), "
            "sales channel (Online, Retail, Partner), and product. Columns: SALE_ID (primary key), "
            "SALE_DATE (date), GEO_TERRITORY (region), CHANNEL (sales channel), PRODUCT_SKU (product identifier), "
            "PRODUCT_CATEGORY (Electronics, Accessories, Cables), ACTUAL_SALES (revenue in GBP), "
            "UNITS_SOLD (number of units), AD_SPEND (marketing spend in GBP), DISCOUNT_RATE (discount percentage). "
            "Use this table when the user asks about revenue, earnings, sales figures, profit, how much money "
            "was made, financial performance, ad spend, discount rates, or units sold by region, product, or channel. "
            "Data covers October 2025 to March 2026."
        ),
        "table_name": "AURA_SALES",
        "schema": "SALES",
        "database": "OMNIDATA_DB",
    },
    {
        "_id": "schema_PRODUCT_CATALOGUE",
        "text": (
            "Table OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE contains the product master data for Aura Retail. "
            "Columns: PRODUCT_SKU (primary key, e.g. AURA-HP-001), PRODUCT_NAME (full name like AuraSound Pro Headphones), "
            "PRODUCT_CATEGORY (Electronics, Accessories, Cables), LAUNCH_DATE (when the product was first sold), "
            "RRP_GBP (recommended retail price in GBP), CHANNEL_AVAILABILITY (All, Online-only, Retail-only), "
            "IS_ACTIVE (whether the product is currently sold). Use this table when the user asks about products, "
            "product names, prices, product categories, what products we sell, or product launch dates. "
            "Join with AURA_SALES on PRODUCT_SKU for product-level revenue analysis."
        ),
        "table_name": "PRODUCT_CATALOGUE",
        "schema": "PRODUCTS",
        "database": "OMNIDATA_DB",
    },
    {
        "_id": "schema_RETURN_EVENTS",
        "text": (
            "Table OMNIDATA_DB.RETURNS.RETURN_EVENTS tracks product returns processed by Aura Retail. "
            "Columns: RETURN_ID (primary key), RETURN_DATE (when return was processed), SALE_DATE (original sale date), "
            "PRODUCT_SKU (returned product, FK to PRODUCT_CATALOGUE), GEO_TERRITORY (North, South, East, West), "
            "CHANNEL (Online, Retail, Partner), RETURN_REASON (Defective, Changed Mind, Wrong Item, Other), "
            "REFUND_AMOUNT (GBP refunded), RETURN_RATE (return rate percentage for that time period and segment). "
            "Use this table when the user asks about returns, refunds, return rates, product defects, "
            "why products are being returned, or quality issues. Notable: AuraSound Pro (AURA-HP-001) "
            "had an 18% return rate in January 2026 due to a firmware defect."
        ),
        "table_name": "RETURN_EVENTS",
        "schema": "RETURNS",
        "database": "OMNIDATA_DB",
    },
    {
        "_id": "schema_CUSTOMER_METRICS",
        "text": (
            "Table OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS contains aggregated monthly customer health metrics "
            "by region and customer segment. Columns: METRIC_ID (primary key), METRIC_MONTH (first day of month), "
            "GEO_TERRITORY (North, South, East, West), CUSTOMER_SEGMENT (Enterprise, SMB, Consumer), "
            "ACTIVE_CUSTOMER_COUNT (customers with a purchase that month), NEW_CUSTOMER_COUNT (first-time buyers), "
            "CHURNED_CUSTOMER_COUNT (customers who left), CHURN_RATE (churn as a decimal, e.g. 0.05 = 5%), "
            "AVG_ORDER_VALUE (average transaction value in GBP), REPEAT_PURCHASE_RATE (proportion with 2+ purchases). "
            "Use this table when the user asks about customer churn, retention, customer health, active customers, "
            "new customers, customer segments, or repeat purchase behaviour. "
            "Notable: SMB churn spiked to 14% in South region in March 2026."
        ),
        "table_name": "CUSTOMER_METRICS",
        "schema": "CUSTOMERS",
        "database": "OMNIDATA_DB",
    },
    {
        "_id": "schema_CROSS_TABLE_RELATIONSHIPS",
        "text": (
            "Cross-table relationships in OMNIDATA_DB: "
            "AURA_SALES.PRODUCT_SKU joins to PRODUCT_CATALOGUE.PRODUCT_SKU for product details and names. "
            "RETURN_EVENTS.PRODUCT_SKU joins to PRODUCT_CATALOGUE.PRODUCT_SKU for returned product details. "
            "All tables share GEO_TERRITORY (North, South, East, West) for regional analysis. "
            "AURA_SALES and RETURN_EVENTS share CHANNEL (Online, Retail, Partner). "
            "CUSTOMER_METRICS and AURA_SALES can be correlated on GEO_TERRITORY and time period "
            "to connect revenue trends with customer health metrics. "
            "Use joins when the user asks for product names with sales data, or return reasons with product details."
        ),
        "table_name": "CROSS_TABLE",
        "schema": "ALL",
        "database": "OMNIDATA_DB",
    },
]


# ============================================================
# Examples Store — 30 verified Q→SQL pairs
# ============================================================

SQL_EXAMPLES = [
    # ── Revenue queries ──────────────────────────────────
    {
        "_id": "example_001",
        "text": (
            "Question: What was total revenue by region last quarter?\n"
            "SQL: SELECT GEO_TERRITORY, SUM(ACTUAL_SALES) AS TOTAL_REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31' "
            "GROUP BY GEO_TERRITORY ORDER BY TOTAL_REVENUE DESC"
        ),
        "category": "revenue",
        "complexity": "simple",
    },
    {
        "_id": "example_002",
        "text": (
            "Question: Compare February and March revenue for the South region\n"
            "SQL: SELECT DATE_TRUNC('month', SALE_DATE) AS MONTH, SUM(ACTUAL_SALES) AS REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE GEO_TERRITORY = 'South' "
            "AND SALE_DATE >= '2026-02-01' AND SALE_DATE <= '2026-03-31' "
            "GROUP BY 1 ORDER BY 1"
        ),
        "category": "revenue",
        "complexity": "medium",
    },
    {
        "_id": "example_003",
        "text": (
            "Question: What is the revenue split by sales channel this year?\n"
            "SQL: SELECT CHANNEL, SUM(ACTUAL_SALES) AS REVENUE, "
            "ROUND(SUM(ACTUAL_SALES) * 100.0 / SUM(SUM(ACTUAL_SALES)) OVER(), 1) AS PCT_OF_TOTAL "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' "
            "GROUP BY CHANNEL ORDER BY REVENUE DESC"
        ),
        "category": "revenue",
        "complexity": "medium",
    },
    {
        "_id": "example_004",
        "text": (
            "Question: Show me monthly revenue trend for North region\n"
            "SQL: SELECT DATE_TRUNC('month', SALE_DATE) AS MONTH, SUM(ACTUAL_SALES) AS REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE GEO_TERRITORY = 'North' "
            "GROUP BY 1 ORDER BY 1"
        ),
        "category": "revenue",
        "complexity": "simple",
    },
    {
        "_id": "example_005",
        "text": (
            "Question: What was total sales in Q1 2026?\n"
            "SQL: SELECT SUM(ACTUAL_SALES) AS TOTAL_SALES "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31'"
        ),
        "category": "revenue",
        "complexity": "simple",
    },
    # ── Product queries ──────────────────────────────────
    {
        "_id": "example_006",
        "text": (
            "Question: Which were the top 5 products by revenue last month?\n"
            "SQL: SELECT p.PRODUCT_NAME, SUM(s.ACTUAL_SALES) AS REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES s "
            "JOIN OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE p ON s.PRODUCT_SKU = p.PRODUCT_SKU "
            "WHERE s.SALE_DATE >= '2026-03-01' AND s.SALE_DATE <= '2026-03-31' "
            "GROUP BY p.PRODUCT_NAME ORDER BY REVENUE DESC LIMIT 5"
        ),
        "category": "product",
        "complexity": "medium",
    },
    {
        "_id": "example_007",
        "text": (
            "Question: How much revenue did AuraSound Pro generate since launch?\n"
            "SQL: SELECT SUM(ACTUAL_SALES) AS TOTAL_REVENUE, SUM(UNITS_SOLD) AS TOTAL_UNITS "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE PRODUCT_SKU = 'AURA-HP-001'"
        ),
        "category": "product",
        "complexity": "simple",
    },
    {
        "_id": "example_008",
        "text": (
            "Question: What is revenue by product category?\n"
            "SQL: SELECT PRODUCT_CATEGORY, SUM(ACTUAL_SALES) AS REVENUE, SUM(UNITS_SOLD) AS UNITS "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "GROUP BY PRODUCT_CATEGORY ORDER BY REVENUE DESC"
        ),
        "category": "product",
        "complexity": "simple",
    },
    {
        "_id": "example_009",
        "text": (
            "Question: Show me all active products with their prices\n"
            "SQL: SELECT PRODUCT_NAME, PRODUCT_CATEGORY, RRP_GBP, LAUNCH_DATE "
            "FROM OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE "
            "WHERE IS_ACTIVE = TRUE ORDER BY RRP_GBP DESC"
        ),
        "category": "product",
        "complexity": "simple",
    },
    {
        "_id": "example_010",
        "text": (
            "Question: What products were launched in 2026?\n"
            "SQL: SELECT PRODUCT_NAME, PRODUCT_SKU, LAUNCH_DATE, RRP_GBP "
            "FROM OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE "
            "WHERE LAUNCH_DATE >= '2026-01-01' ORDER BY LAUNCH_DATE"
        ),
        "category": "product",
        "complexity": "simple",
    },
    # ── Return queries ──────────────────────────────────
    {
        "_id": "example_011",
        "text": (
            "Question: What is the return rate for online electronics this year?\n"
            "SQL: SELECT PRODUCT_SKU, COUNT(*) AS RETURN_COUNT, "
            "ROUND(AVG(RETURN_RATE) * 100, 1) AS AVG_RETURN_RATE_PCT "
            "FROM OMNIDATA_DB.RETURNS.RETURN_EVENTS "
            "WHERE CHANNEL = 'Online' AND RETURN_DATE >= '2026-01-01' "
            "GROUP BY PRODUCT_SKU ORDER BY RETURN_COUNT DESC"
        ),
        "category": "returns",
        "complexity": "medium",
    },
    {
        "_id": "example_012",
        "text": (
            "Question: Why are returns spiking for AuraSound Pro?\n"
            "SQL: SELECT DATE_TRUNC('month', RETURN_DATE) AS MONTH, "
            "RETURN_REASON, COUNT(*) AS COUNT "
            "FROM OMNIDATA_DB.RETURNS.RETURN_EVENTS "
            "WHERE PRODUCT_SKU = 'AURA-HP-001' "
            "GROUP BY 1, 2 ORDER BY 1, COUNT DESC"
        ),
        "category": "returns",
        "complexity": "medium",
    },
    {
        "_id": "example_013",
        "text": (
            "Question: What is the total refund amount by region?\n"
            "SQL: SELECT GEO_TERRITORY, SUM(REFUND_AMOUNT) AS TOTAL_REFUNDS, "
            "COUNT(*) AS RETURN_COUNT "
            "FROM OMNIDATA_DB.RETURNS.RETURN_EVENTS "
            "GROUP BY GEO_TERRITORY ORDER BY TOTAL_REFUNDS DESC"
        ),
        "category": "returns",
        "complexity": "simple",
    },
    {
        "_id": "example_014",
        "text": (
            "Question: Show me return reasons breakdown\n"
            "SQL: SELECT RETURN_REASON, COUNT(*) AS COUNT, "
            "ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS PERCENTAGE "
            "FROM OMNIDATA_DB.RETURNS.RETURN_EVENTS "
            "GROUP BY RETURN_REASON ORDER BY COUNT DESC"
        ),
        "category": "returns",
        "complexity": "medium",
    },
    {
        "_id": "example_015",
        "text": (
            "Question: What are the monthly return trends?\n"
            "SQL: SELECT DATE_TRUNC('month', RETURN_DATE) AS MONTH, "
            "COUNT(*) AS RETURN_COUNT, ROUND(AVG(RETURN_RATE) * 100, 1) AS AVG_RATE_PCT "
            "FROM OMNIDATA_DB.RETURNS.RETURN_EVENTS "
            "GROUP BY 1 ORDER BY 1"
        ),
        "category": "returns",
        "complexity": "simple",
    },
    # ── Churn / Customer queries ──────────────────────────
    {
        "_id": "example_016",
        "text": (
            "Question: What is the churn rate by customer segment in the South?\n"
            "SQL: SELECT CUSTOMER_SEGMENT, METRIC_MONTH, "
            "ROUND(CHURN_RATE * 100, 1) AS CHURN_PCT "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "WHERE GEO_TERRITORY = 'South' "
            "ORDER BY METRIC_MONTH, CUSTOMER_SEGMENT"
        ),
        "category": "churn",
        "complexity": "simple",
    },
    {
        "_id": "example_017",
        "text": (
            "Question: Which region has the highest churn rate?\n"
            "SQL: SELECT GEO_TERRITORY, ROUND(AVG(CHURN_RATE) * 100, 1) AS AVG_CHURN_PCT "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "WHERE METRIC_MONTH >= '2026-01-01' "
            "GROUP BY GEO_TERRITORY ORDER BY AVG_CHURN_PCT DESC"
        ),
        "category": "churn",
        "complexity": "simple",
    },
    {
        "_id": "example_018",
        "text": (
            "Question: How many active customers do we have by region?\n"
            "SQL: SELECT GEO_TERRITORY, SUM(ACTIVE_CUSTOMER_COUNT) AS TOTAL_ACTIVE "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "WHERE METRIC_MONTH = '2026-03-01' "
            "GROUP BY GEO_TERRITORY ORDER BY TOTAL_ACTIVE DESC"
        ),
        "category": "customers",
        "complexity": "simple",
    },
    {
        "_id": "example_019",
        "text": (
            "Question: What is the SMB churn trend over time?\n"
            "SQL: SELECT METRIC_MONTH, GEO_TERRITORY, "
            "ROUND(CHURN_RATE * 100, 1) AS CHURN_PCT "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "WHERE CUSTOMER_SEGMENT = 'SMB' "
            "ORDER BY METRIC_MONTH, GEO_TERRITORY"
        ),
        "category": "churn",
        "complexity": "medium",
    },
    {
        "_id": "example_020",
        "text": (
            "Question: How many new customers did we gain each month?\n"
            "SQL: SELECT METRIC_MONTH, SUM(NEW_CUSTOMER_COUNT) AS NEW_CUSTOMERS "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "GROUP BY METRIC_MONTH ORDER BY METRIC_MONTH"
        ),
        "category": "customers",
        "complexity": "simple",
    },
    # ── Ad Spend / Marketing queries ──────────────────────
    {
        "_id": "example_021",
        "text": (
            "Question: What was ad spend by region last quarter?\n"
            "SQL: SELECT GEO_TERRITORY, SUM(AD_SPEND) AS TOTAL_AD_SPEND "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31' "
            "GROUP BY GEO_TERRITORY ORDER BY TOTAL_AD_SPEND DESC"
        ),
        "category": "marketing",
        "complexity": "simple",
    },
    {
        "_id": "example_022",
        "text": (
            "Question: What is our marketing ROI by region?\n"
            "SQL: SELECT GEO_TERRITORY, SUM(ACTUAL_SALES) AS REVENUE, "
            "SUM(AD_SPEND) AS AD_SPEND, "
            "ROUND(SUM(ACTUAL_SALES) / NULLIF(SUM(AD_SPEND), 0), 2) AS ROI "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31' "
            "GROUP BY GEO_TERRITORY ORDER BY ROI DESC"
        ),
        "category": "marketing",
        "complexity": "medium",
    },
    {
        "_id": "example_023",
        "text": (
            "Question: Show me monthly ad spend for the South region\n"
            "SQL: SELECT DATE_TRUNC('month', SALE_DATE) AS MONTH, SUM(AD_SPEND) AS AD_SPEND "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE GEO_TERRITORY = 'South' "
            "GROUP BY 1 ORDER BY 1"
        ),
        "category": "marketing",
        "complexity": "simple",
    },
    # ── Channel analysis ──────────────────────────────────
    {
        "_id": "example_024",
        "text": (
            "Question: Which channel is performing best this quarter?\n"
            "SQL: SELECT CHANNEL, SUM(ACTUAL_SALES) AS REVENUE, SUM(UNITS_SOLD) AS UNITS "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31' "
            "GROUP BY CHANNEL ORDER BY REVENUE DESC"
        ),
        "category": "channel",
        "complexity": "simple",
    },
    {
        "_id": "example_025",
        "text": (
            "Question: How is the Partner channel trending?\n"
            "SQL: SELECT DATE_TRUNC('month', SALE_DATE) AS MONTH, "
            "GEO_TERRITORY, SUM(ACTUAL_SALES) AS REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE CHANNEL = 'Partner' "
            "GROUP BY 1, 2 ORDER BY 1, 2"
        ),
        "category": "channel",
        "complexity": "medium",
    },
    # ── Cross-table / Join queries ────────────────────────
    {
        "_id": "example_026",
        "text": (
            "Question: Top selling products by name and revenue\n"
            "SQL: SELECT p.PRODUCT_NAME, p.PRODUCT_CATEGORY, "
            "SUM(s.ACTUAL_SALES) AS REVENUE, SUM(s.UNITS_SOLD) AS UNITS "
            "FROM OMNIDATA_DB.SALES.AURA_SALES s "
            "JOIN OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE p ON s.PRODUCT_SKU = p.PRODUCT_SKU "
            "GROUP BY p.PRODUCT_NAME, p.PRODUCT_CATEGORY ORDER BY REVENUE DESC LIMIT 10"
        ),
        "category": "product",
        "complexity": "medium",
    },
    {
        "_id": "example_027",
        "text": (
            "Question: What is the average order value by region and segment?\n"
            "SQL: SELECT GEO_TERRITORY, CUSTOMER_SEGMENT, "
            "ROUND(AVG(AVG_ORDER_VALUE), 2) AS AVG_AOV "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "WHERE METRIC_MONTH >= '2026-01-01' "
            "GROUP BY GEO_TERRITORY, CUSTOMER_SEGMENT ORDER BY AVG_AOV DESC"
        ),
        "category": "customers",
        "complexity": "medium",
    },
    {
        "_id": "example_028",
        "text": (
            "Question: Revenue comparison: online vs retail vs partner for each region\n"
            "SQL: SELECT GEO_TERRITORY, CHANNEL, SUM(ACTUAL_SALES) AS REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31' "
            "GROUP BY GEO_TERRITORY, CHANNEL ORDER BY GEO_TERRITORY, REVENUE DESC"
        ),
        "category": "channel",
        "complexity": "medium",
    },
    # ── Time-series / Aggregation patterns ────────────────
    {
        "_id": "example_029",
        "text": (
            "Question: Show me daily sales for the last 30 days\n"
            "SQL: SELECT SALE_DATE, SUM(ACTUAL_SALES) AS DAILY_REVENUE "
            "FROM OMNIDATA_DB.SALES.AURA_SALES "
            "WHERE SALE_DATE >= DATEADD(day, -30, CURRENT_DATE()) "
            "GROUP BY SALE_DATE ORDER BY SALE_DATE"
        ),
        "category": "revenue",
        "complexity": "simple",
    },
    {
        "_id": "example_030",
        "text": (
            "Question: What is the repeat purchase rate trend for enterprise customers?\n"
            "SQL: SELECT METRIC_MONTH, GEO_TERRITORY, "
            "ROUND(REPEAT_PURCHASE_RATE * 100, 1) AS REPEAT_PCT "
            "FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS "
            "WHERE CUSTOMER_SEGMENT = 'Enterprise' "
            "ORDER BY METRIC_MONTH, GEO_TERRITORY"
        ),
        "category": "customers",
        "complexity": "medium",
    },
]


def seed(verify_only: bool = False):
    """Main seed function for Pinecone."""
    settings = get_settings()
    
    client = PineconeClient(api_key=settings.pinecone_api_key)
    index_name = settings.pinecone_hybrid_index
    
    # Test connection
    print("Testing Pinecone connection...")
    if not client.test_connection(index_name):
        print("✗ Connection failed. Check your API key and index name.")
        return
    print(f"✓ Connected to Pinecone index: {index_name}\n")
    
    if verify_only:
        verify(client, index_name)
        return
    
    # Seed schema_store
    print(f"Seeding schema_store ({len(SCHEMA_DOCUMENTS)} documents)...")
    client.upsert_records(index_name, "schema_store", SCHEMA_DOCUMENTS)
    print("✓ schema_store seeded\n")
    
    # Seed examples_store
    print(f"Seeding examples_store ({len(SQL_EXAMPLES)} documents)...")
    # Upsert in batches of 10 to avoid timeout
    batch_size = 10
    for i in range(0, len(SQL_EXAMPLES), batch_size):
        batch = SQL_EXAMPLES[i:i + batch_size]
        client.upsert_records(index_name, "examples_store", batch)
        print(f"  Batch {i // batch_size + 1}: {len(batch)} records upserted")
        time.sleep(1)  # Brief pause between batches
    print("✓ examples_store seeded\n")
    
    # Wait for indexing
    print("Waiting for indexing to complete...")
    time.sleep(5)
    
    verify(client, index_name)
    print("\n✓ Pinecone seeding complete!")


def verify(client: PineconeClient, index_name: str):
    """Verify namespace vector counts."""
    print("Verifying namespace stats...")
    from pinecone import Pinecone
    pc = Pinecone(api_key=get_settings().pinecone_api_key)
    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    
    print(f"  Total vectors: {stats.total_vector_count}")
    if stats.namespaces:
        for ns_name, ns_info in stats.namespaces.items():
            print(f"  {ns_name}: {ns_info.vector_count} vectors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Pinecone with schema and SQL examples")
    parser.add_argument("--verify", action="store_true", help="Only verify vector counts")
    args = parser.parse_args()
    
    seed(verify_only=args.verify)
