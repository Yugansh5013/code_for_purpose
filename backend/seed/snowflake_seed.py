"""
OmniData — Snowflake Seed Script

Creates the OMNIDATA_DB database with all schemas and tables,
then generates and loads synthetic seed data for Aura Retail.

Idempotent: safe to run multiple times (uses CREATE OR REPLACE).

Usage:
    cd backend
    python -m seed.snowflake_seed
    python -m seed.snowflake_seed --verify  # Just check row counts
"""

import os
import sys
import csv
import random
import argparse
from datetime import date, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import get_settings
from src.warehouse.connector import SnowflakeConnector


# ============================================================
# Data Generation
# ============================================================

REGIONS = ["North", "South", "East", "West"]
CHANNELS = ["Online", "Retail", "Partner"]

PRODUCTS = [
    # Core products (from PRD)
    ("AURA-HP-001", "AuraSound Pro Headphones", "Electronics", "2026-01-08", 149.99),
    ("AURA-HP-002", "AuraSound Lite Headphones", "Electronics", "2024-03-01", 79.99),
    ("AURA-SPK-001", "AuraBoom Portable Speaker", "Electronics", "2024-06-15", 89.99),
    ("AURA-CBL-001", "AuraConnect USB-C Cable 2m", "Cables", "2023-01-01", 12.99),
    ("AURA-ACC-001", "AuraCase Pro Carry Case", "Accessories", "2024-09-01", 34.99),
    # Additional products
    ("AURA-HP-003", "AuraSound Studio Monitor", "Electronics", "2024-01-15", 199.99),
    ("AURA-HP-004", "AuraSound Kids Headphones", "Electronics", "2024-07-01", 39.99),
    ("AURA-SPK-002", "AuraBoom Mini Speaker", "Electronics", "2024-09-01", 49.99),
    ("AURA-SPK-003", "AuraBoom Max Soundbar", "Electronics", "2025-02-01", 179.99),
    ("AURA-SPK-004", "AuraBoom Party Speaker", "Electronics", "2025-06-01", 129.99),
    ("AURA-CBL-002", "AuraConnect Lightning Cable 1m", "Cables", "2023-03-01", 9.99),
    ("AURA-CBL-003", "AuraConnect HDMI Cable 3m", "Cables", "2023-06-01", 14.99),
    ("AURA-CBL-004", "AuraConnect USB-A to C Adapter", "Cables", "2023-09-01", 7.99),
    ("AURA-CBL-005", "AuraConnect Ethernet Cable 5m", "Cables", "2024-01-01", 11.99),
    ("AURA-CBL-006", "AuraConnect Display Port Cable 2m", "Cables", "2024-04-01", 13.99),
    ("AURA-ACC-002", "AuraCase Lite Carry Pouch", "Accessories", "2024-03-01", 19.99),
    ("AURA-ACC-003", "AuraStand Pro Headphone Stand", "Accessories", "2024-06-01", 29.99),
    ("AURA-ACC-004", "AuraPad Wireless Charging Pad", "Accessories", "2024-11-01", 24.99),
    ("AURA-ACC-005", "AuraClean Screen Cleaning Kit", "Accessories", "2023-05-01", 8.99),
    ("AURA-ACC-006", "AuraWrap Cable Organiser", "Accessories", "2023-08-01", 6.99),
    ("AURA-ACC-007", "AuraGrip Phone Mount", "Accessories", "2024-02-01", 15.99),
    ("AURA-ACC-008", "AuraShield Screen Protector Pack", "Accessories", "2024-05-01", 12.99),
    ("AURA-HP-005", "AuraSound Sport Earbuds", "Electronics", "2025-03-01", 69.99),
    ("AURA-HP-006", "AuraSound Noise Cancel Pro", "Electronics", "2025-08-01", 229.99),
    ("AURA-SPK-005", "AuraBoom Travel Speaker", "Electronics", "2025-04-01", 59.99),
    ("AURA-ACC-009", "AuraMount TV Wall Bracket", "Accessories", "2025-01-01", 44.99),
    ("AURA-CBL-007", "AuraConnect USB-C Hub 7-in-1", "Cables", "2025-05-01", 39.99),
    ("AURA-ACC-010", "AuraTag Bluetooth Tracker 4-Pack", "Accessories", "2025-07-01", 54.99),
    ("AURA-HP-007", "AuraSound Sleep Buds", "Electronics", "2025-09-01", 99.99),
    ("AURA-SPK-006", "AuraBoom Outdoor Rugged Speaker", "Electronics", "2025-10-01", 109.99),
]

# Monthly base revenue by region (GBP, thousands)
REGION_BASE_REVENUE = {
    "North": 420000,
    "South": 380000,
    "East": 290000,
    "West": 260000,
}

# Channel revenue split
CHANNEL_SPLIT = {"Online": 0.40, "Retail": 0.35, "Partner": 0.25}

SEGMENTS = ["Enterprise", "SMB", "Consumer"]

START_DATE = date(2025, 10, 1)
END_DATE = date(2026, 3, 31)


def generate_sales_data() -> list[dict]:
    """Generate ~2,160 sales rows with PRD narrative patterns embedded."""
    rows = []
    sale_id = 1
    
    current = START_DATE
    while current <= END_DATE:
        month = current.month
        year = current.year
        
        for region in REGIONS:
            base = REGION_BASE_REVENUE[region]
            
            # Apply narrative patterns
            multiplier = 1.0
            ad_spend_multiplier = 1.0
            
            # Thread 1: South region crisis (Feb 2026)
            if region == "South" and year == 2026 and month == 2:
                multiplier = 0.72  # -28% drop
                ad_spend_multiplier = 0.05  # Near-zero ad spend
            elif region == "South" and year == 2026 and month == 3:
                multiplier = 0.82  # Partial recovery to ~£310k
                ad_spend_multiplier = 0.3
            
            # Thread 2: North success story (Jan 2026)
            if region == "North" and year == 2026 and month == 1:
                multiplier = 1.21  # Spike to ~£510k
            elif region == "North" and year == 2026 and month in [2, 3]:
                multiplier = 1.15  # Sustained growth
            
            for channel in CHANNELS:
                channel_base = base * CHANNEL_SPLIT[channel] / 30  # Daily
                
                # Thread 3: Partner channel decline in South/East (Mar 2026)
                partner_decline = 1.0
                if channel == "Partner" and year == 2026 and month == 3:
                    if region in ["South", "East"]:
                        partner_decline = 0.70  # -30% Partner revenue
                
                for product in PRODUCTS:
                    sku = product[0]
                    category = product[2]
                    rrp = product[4]
                    launch = product[3]
                    
                    # Skip products not yet launched
                    if current < date.fromisoformat(launch):
                        continue
                    
                    # Not every product sells every day — sample ~60%
                    if random.random() > 0.6:
                        continue
                    
                    # AuraSound Pro boost in North Jan 2026
                    product_boost = 1.0
                    if sku == "AURA-HP-001" and region == "North" and year == 2026 and month == 1:
                        product_boost = 3.0
                    
                    # Calculate daily revenue for this row
                    variance = random.uniform(0.90, 1.10)  # ±10% noise
                    units = max(1, int(random.gauss(8, 3)))
                    daily_revenue = round(units * rrp * variance * multiplier * partner_decline * product_boost, 2)
                    
                    # Ad spend
                    ad_spend = round(daily_revenue * 0.12 * ad_spend_multiplier * random.uniform(0.8, 1.2), 2)
                    
                    # Discount
                    discount = round(random.choice([0, 0, 0, 5, 10, 15, 20]) / 100, 2)
                    
                    rows.append({
                        "SALE_ID": f"SALE-{year}-{sale_id:06d}",
                        "SALE_DATE": current.isoformat(),
                        "GEO_TERRITORY": region,
                        "CHANNEL": channel,
                        "PRODUCT_SKU": sku,
                        "PRODUCT_CATEGORY": category,
                        "ACTUAL_SALES": daily_revenue,
                        "UNITS_SOLD": units,
                        "AD_SPEND": ad_spend,
                        "DISCOUNT_RATE": discount,
                    })
                    sale_id += 1
        
        current += timedelta(days=1)
    
    return rows


def generate_return_events(sales_data: list[dict]) -> list[dict]:
    """Generate return events with PRD narrative patterns."""
    returns = []
    return_id = 1
    
    reasons_normal = ["Changed Mind", "Wrong Item", "Other"]
    
    for sale in sales_data:
        sale_date = date.fromisoformat(sale["SALE_DATE"])
        sku = sale["PRODUCT_SKU"]
        channel = sale["CHANNEL"]
        month = sale_date.month
        year = sale_date.year
        
        # Base return probability
        return_prob = 0.07  # 7% normal
        defective_prob = 0.10  # 10% of returns are defective normally
        
        # Thread 4: Online returns spike for AURA-HP-001 in Jan 2026
        if sku == "AURA-HP-001" and channel == "Online" and year == 2026 and month == 1:
            return_prob = 0.18  # 18% return rate
            defective_prob = 0.65  # 65% defective
        elif sku == "AURA-HP-001" and year == 2026 and month >= 2:
            return_prob = 0.07  # Normalized after firmware fix
        
        for _ in range(sale["UNITS_SOLD"]):
            if random.random() < return_prob:
                is_defective = random.random() < defective_prob
                reason = "Defective" if is_defective else random.choice(reasons_normal)
                
                return_delay = random.randint(3, 25)
                return_date = sale_date + timedelta(days=return_delay)
                
                refund = round(sale["ACTUAL_SALES"] / sale["UNITS_SOLD"] * random.uniform(0.85, 1.0), 2)
                
                returns.append({
                    "RETURN_ID": f"RET-{year}-{return_id:06d}",
                    "RETURN_DATE": return_date.isoformat(),
                    "SALE_DATE": sale["SALE_DATE"],
                    "PRODUCT_SKU": sku,
                    "GEO_TERRITORY": sale["GEO_TERRITORY"],
                    "CHANNEL": channel,
                    "RETURN_REASON": reason,
                    "REFUND_AMOUNT": refund,
                    "RETURN_RATE": round(return_prob, 3),
                })
                return_id += 1
    
    return returns


def generate_customer_metrics() -> list[dict]:
    """Generate monthly customer health metrics with PRD patterns."""
    rows = []
    metric_id = 1
    
    current = START_DATE.replace(day=1)
    end = END_DATE.replace(day=1)
    
    while current <= end:
        month = current.month
        year = current.year
        
        for region in REGIONS:
            for segment in SEGMENTS:
                # Base values
                active = random.randint(800, 1200)
                new_customers = random.randint(40, 80)
                churn_rate = round(random.uniform(0.03, 0.05), 3)
                aov = round(random.uniform(45, 120), 2)
                repeat_rate = round(random.uniform(0.25, 0.40), 3)
                
                # Thread 3: SMB churn spike in South (Feb/Mar 2026)
                if segment == "SMB" and region == "South":
                    if year == 2026 and month == 2:
                        churn_rate = round(random.uniform(0.10, 0.12), 3)  # ~11%
                    elif year == 2026 and month == 3:
                        churn_rate = round(random.uniform(0.13, 0.15), 3)  # ~14%
                        repeat_rate = round(random.uniform(0.15, 0.22), 3)
                
                # Thread 3: SMB churn in East (lagging, Mar 2026)
                if segment == "SMB" and region == "East":
                    if year == 2026 and month == 3:
                        churn_rate = round(random.uniform(0.07, 0.09), 3)  # ~8%
                
                # Thread 2: North Consumer spike (Jan 2026 - AuraSound Pro)
                if segment == "Consumer" and region == "North" and year == 2026 and month == 1:
                    new_customers = random.randint(120, 160)  # Spike
                    active = random.randint(1300, 1500)
                
                churned = max(1, int(active * churn_rate))
                
                rows.append({
                    "METRIC_ID": f"MET-{year}-{metric_id:04d}",
                    "METRIC_MONTH": current.isoformat(),
                    "GEO_TERRITORY": region,
                    "CUSTOMER_SEGMENT": segment,
                    "ACTIVE_CUSTOMER_COUNT": active,
                    "NEW_CUSTOMER_COUNT": new_customers,
                    "CHURNED_CUSTOMER_COUNT": churned,
                    "CHURN_RATE": churn_rate,
                    "AVG_ORDER_VALUE": aov,
                    "REPEAT_PURCHASE_RATE": repeat_rate,
                })
                metric_id += 1
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    return rows


# ============================================================
# Snowflake DDL & Loading
# ============================================================

DDL_STATEMENTS = [
    "CREATE DATABASE IF NOT EXISTS OMNIDATA_DB",
    "USE DATABASE OMNIDATA_DB",
    
    "CREATE SCHEMA IF NOT EXISTS SALES",
    "CREATE SCHEMA IF NOT EXISTS PRODUCTS",
    "CREATE SCHEMA IF NOT EXISTS RETURNS",
    "CREATE SCHEMA IF NOT EXISTS CUSTOMERS",
    
    """
    CREATE OR REPLACE TABLE OMNIDATA_DB.SALES.AURA_SALES (
        SALE_ID VARCHAR PRIMARY KEY,
        SALE_DATE DATE,
        GEO_TERRITORY VARCHAR,
        CHANNEL VARCHAR,
        PRODUCT_SKU VARCHAR,
        PRODUCT_CATEGORY VARCHAR,
        ACTUAL_SALES NUMBER(12,2),
        UNITS_SOLD NUMBER,
        AD_SPEND NUMBER(10,2),
        DISCOUNT_RATE NUMBER(4,2)
    )
    """,
    
    """
    CREATE OR REPLACE TABLE OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE (
        PRODUCT_SKU VARCHAR PRIMARY KEY,
        PRODUCT_NAME VARCHAR,
        PRODUCT_CATEGORY VARCHAR,
        LAUNCH_DATE DATE,
        RRP_GBP NUMBER(8,2),
        CHANNEL_AVAILABILITY VARCHAR DEFAULT 'All',
        IS_ACTIVE BOOLEAN DEFAULT TRUE
    )
    """,
    
    """
    CREATE OR REPLACE TABLE OMNIDATA_DB.RETURNS.RETURN_EVENTS (
        RETURN_ID VARCHAR PRIMARY KEY,
        RETURN_DATE DATE,
        SALE_DATE DATE,
        PRODUCT_SKU VARCHAR,
        GEO_TERRITORY VARCHAR,
        CHANNEL VARCHAR,
        RETURN_REASON VARCHAR,
        REFUND_AMOUNT NUMBER(10,2),
        RETURN_RATE NUMBER(4,3)
    )
    """,
    
    """
    CREATE OR REPLACE TABLE OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS (
        METRIC_ID VARCHAR PRIMARY KEY,
        METRIC_MONTH DATE,
        GEO_TERRITORY VARCHAR,
        CUSTOMER_SEGMENT VARCHAR,
        ACTIVE_CUSTOMER_COUNT NUMBER,
        NEW_CUSTOMER_COUNT NUMBER,
        CHURNED_CUSTOMER_COUNT NUMBER,
        CHURN_RATE NUMBER(4,3),
        AVG_ORDER_VALUE NUMBER(8,2),
        REPEAT_PURCHASE_RATE NUMBER(4,3)
    )
    """,
]


def save_csv(data: list[dict], filename: str) -> Path:
    """Save data to CSV in the seed/data directory."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    filepath = data_dir / filename
    
    if not data:
        print(f"  ⚠ No data for {filename}")
        return filepath
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"  ✓ Saved {len(data)} rows → {filepath.name}")
    return filepath


def load_to_snowflake(connector: SnowflakeConnector, table: str, data: list[dict]):
    """Load data into Snowflake using batch INSERT."""
    if not data:
        return
    
    columns = list(data[0].keys())
    col_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
    
    # Batch insert in chunks of 500
    batch_size = 500
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        values = [tuple(row[col] for col in columns) for row in batch]
        
        from src.warehouse.connector import snowflake
        with connector._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, values)
            cursor.close()
    
    print(f"  ✓ Loaded {len(data)} rows → {table}")


def seed(verify_only: bool = False):
    """Main seed function."""
    settings = get_settings()
    
    connector = SnowflakeConnector(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
    )
    
    # Test connection
    print("Testing Snowflake connection...")
    if not connector.test_connection():
        print("✗ Connection failed. Check your credentials.")
        return
    print("✓ Connected to Snowflake\n")
    
    if verify_only:
        verify(connector)
        return
    
    # Run DDL
    print("Creating database and tables...")
    for ddl in DDL_STATEMENTS:
        connector.execute_ddl(ddl)
    print("✓ All tables created\n")
    
    # Generate data
    print("Generating seed data...")
    random.seed(42)  # Reproducible
    
    sales = generate_sales_data()
    save_csv(sales, "aura_sales.csv")
    
    products = [
        {
            "PRODUCT_SKU": p[0],
            "PRODUCT_NAME": p[1],
            "PRODUCT_CATEGORY": p[2],
            "LAUNCH_DATE": p[3],
            "RRP_GBP": p[4],
            "CHANNEL_AVAILABILITY": "All",
            "IS_ACTIVE": True,
        }
        for p in PRODUCTS
    ]
    save_csv(products, "product_catalogue.csv")
    
    returns = generate_return_events(sales)
    save_csv(returns, "return_events.csv")
    
    metrics = generate_customer_metrics()
    save_csv(metrics, "customer_metrics.csv")
    
    print()
    
    # Load to Snowflake
    print("Loading data to Snowflake...")
    connector.execute_ddl("USE DATABASE OMNIDATA_DB")
    
    load_to_snowflake(connector, "OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE", products)
    load_to_snowflake(connector, "OMNIDATA_DB.SALES.AURA_SALES", sales)
    load_to_snowflake(connector, "OMNIDATA_DB.RETURNS.RETURN_EVENTS", returns)
    load_to_snowflake(connector, "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS", metrics)
    
    print()
    verify(connector)
    
    connector.close()
    print("\n✓ Snowflake seeding complete!")


def verify(connector: SnowflakeConnector):
    """Verify row counts in all tables."""
    print("Verifying row counts...")
    tables = [
        "OMNIDATA_DB.SALES.AURA_SALES",
        "OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE",
        "OMNIDATA_DB.RETURNS.RETURN_EVENTS",
        "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS",
    ]
    for table in tables:
        try:
            result = connector.execute_query(f"SELECT COUNT(*) AS cnt FROM {table}")
            count = result[0]["CNT"]
            print(f"  {table}: {count} rows")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Snowflake with Aura Retail data")
    parser.add_argument("--verify", action="store_true", help="Only verify row counts")
    args = parser.parse_args()
    
    seed(verify_only=args.verify)
