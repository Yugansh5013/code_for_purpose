"""
OmniData -- Neon (PostgreSQL) Seed Script

Creates all tables and seeds Aura Retail synthetic data into Neon.

NOTE: Migration note:
    Originally used Snowflake (see seed/snowflake_seed.py, preserved for reference).
    Migrated to Neon (serverless PostgreSQL) on 2026-05-19 because the Snowflake
    30-day free trial expired. All data and business narratives are identical.
    Table names converted to lowercase snake_case per PostgreSQL convention.

Idempotent: safe to run multiple times (uses CREATE TABLE IF NOT EXISTS + ON CONFLICT DO NOTHING).

Usage:
    cd backend
    python -m seed.neon_seed
    python -m seed.neon_seed --verify   # Check row counts only
"""

import os
import sys
import random
import argparse
from datetime import date, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Add it to your .env file and retry.")
    sys.exit(1)


# ============================================================
# Data Generation (identical to snowflake_seed.py)
# ============================================================

REGIONS = ["North", "South", "East", "West"]
CHANNELS = ["Online", "Retail", "Partner"]
SEGMENTS = ["Enterprise", "SMB", "Consumer"]

PRODUCTS = [
    ("AURA-HP-001",  "AuraSound Pro Headphones",         "Electronics",  "2026-01-08", 149.99),
    ("AURA-HP-002",  "AuraSound Lite Headphones",         "Electronics",  "2024-03-01",  79.99),
    ("AURA-SPK-001", "AuraBoom Portable Speaker",         "Electronics",  "2024-06-15",  89.99),
    ("AURA-CBL-001", "AuraConnect USB-C Cable 2m",        "Cables",       "2023-01-01",  12.99),
    ("AURA-ACC-001", "AuraCase Pro Carry Case",           "Accessories",  "2024-09-01",  34.99),
    ("AURA-HP-003",  "AuraSound Studio Monitor",          "Electronics",  "2024-01-15", 199.99),
    ("AURA-HP-004",  "AuraSound Kids Headphones",         "Electronics",  "2024-07-01",  39.99),
    ("AURA-SPK-002", "AuraBoom Mini Speaker",             "Electronics",  "2024-09-01",  49.99),
    ("AURA-SPK-003", "AuraBoom Max Soundbar",             "Electronics",  "2025-02-01", 179.99),
    ("AURA-SPK-004", "AuraBoom Party Speaker",            "Electronics",  "2025-06-01", 129.99),
    ("AURA-CBL-002", "AuraConnect Lightning Cable 1m",    "Cables",       "2023-03-01",   9.99),
    ("AURA-CBL-003", "AuraConnect HDMI Cable 3m",         "Cables",       "2023-06-01",  14.99),
    ("AURA-CBL-004", "AuraConnect USB-A to C Adapter",    "Cables",       "2023-09-01",   7.99),
    ("AURA-CBL-005", "AuraConnect Ethernet Cable 5m",     "Cables",       "2024-01-01",  11.99),
    ("AURA-CBL-006", "AuraConnect Display Port Cable 2m", "Cables",       "2024-04-01",  13.99),
    ("AURA-ACC-002", "AuraCase Lite Carry Pouch",         "Accessories",  "2024-03-01",  19.99),
    ("AURA-ACC-003", "AuraStand Pro Headphone Stand",     "Accessories",  "2024-06-01",  29.99),
    ("AURA-ACC-004", "AuraPad Wireless Charging Pad",     "Accessories",  "2024-11-01",  24.99),
    ("AURA-ACC-005", "AuraClean Screen Cleaning Kit",     "Accessories",  "2023-05-01",   8.99),
    ("AURA-ACC-006", "AuraWrap Cable Organiser",          "Accessories",  "2023-08-01",   6.99),
    ("AURA-ACC-007", "AuraGrip Phone Mount",              "Accessories",  "2024-02-01",  15.99),
    ("AURA-ACC-008", "AuraShield Screen Protector Pack",  "Accessories",  "2024-05-01",  12.99),
    ("AURA-HP-005",  "AuraSound Sport Earbuds",           "Electronics",  "2025-03-01",  69.99),
    ("AURA-HP-006",  "AuraSound Noise Cancel Pro",        "Electronics",  "2025-08-01", 229.99),
    ("AURA-SPK-005", "AuraBoom Travel Speaker",           "Electronics",  "2025-04-01",  59.99),
    ("AURA-ACC-009", "AuraMount TV Wall Bracket",         "Accessories",  "2025-01-01",  44.99),
    ("AURA-CBL-007", "AuraConnect USB-C Hub 7-in-1",      "Cables",       "2025-05-01",  39.99),
    ("AURA-ACC-010", "AuraTag Bluetooth Tracker 4-Pack",  "Accessories",  "2025-07-01",  54.99),
    ("AURA-HP-007",  "AuraSound Sleep Buds",              "Electronics",  "2025-09-01",  99.99),
    ("AURA-SPK-006", "AuraBoom Outdoor Rugged Speaker",   "Electronics",  "2025-10-01", 109.99),
]

REGION_BASE_REVENUE = {"North": 420000, "South": 380000, "East": 290000, "West": 260000}
CHANNEL_SPLIT = {"Online": 0.40, "Retail": 0.35, "Partner": 0.25}
START_DATE = date(2025, 10, 1)
END_DATE = date(2026, 3, 31)


def generate_sales_data():
    rows, sale_id = [], 1
    current = START_DATE
    while current <= END_DATE:
        month, year = current.month, current.year
        for region in REGIONS:
            base = REGION_BASE_REVENUE[region]
            multiplier = ad_mult = 1.0
            if region == "South" and year == 2026 and month == 2:
                multiplier, ad_mult = 0.72, 0.05
            elif region == "South" and year == 2026 and month == 3:
                multiplier, ad_mult = 0.82, 0.30
            if region == "North" and year == 2026 and month == 1:
                multiplier = 1.21
            elif region == "North" and year == 2026 and month in [2, 3]:
                multiplier = 1.15

            for channel in CHANNELS:
                partner_decline = 0.70 if (
                    channel == "Partner" and year == 2026 and month == 3
                    and region in ["South", "East"]
                ) else 1.0

                for product in PRODUCTS:
                    sku, pname, cat, launch, rrp = product
                    if current < date.fromisoformat(launch):
                        continue
                    if random.random() > 0.6:
                        continue
                    boost = 3.0 if (sku == "AURA-HP-001" and region == "North"
                                    and year == 2026 and month == 1) else 1.0
                    variance = random.uniform(0.90, 1.10)
                    units = max(1, int(random.gauss(8, 3)))
                    revenue = round(units * rrp * variance * multiplier * partner_decline * boost, 2)
                    ad_spend = round(revenue * 0.12 * ad_mult * random.uniform(0.8, 1.2), 2)
                    discount = round(random.choice([0, 0, 0, 5, 10, 15, 20]) / 100, 2)

                    rows.append({
                        "sale_id": f"SALE-{year}-{sale_id:06d}",
                        "sale_date": current.isoformat(),
                        "geo_territory": region,
                        "channel": channel,
                        "product_sku": sku,
                        "product_name": pname,
                        "product_category": cat,
                        "actual_sales": revenue,
                        "units_sold": units,
                        "ad_spend": ad_spend,
                        "discount_rate": discount,
                    })
                    sale_id += 1
        current += timedelta(days=1)
    return rows


def generate_return_events(sales):
    returns, ret_id = [], 1
    reasons_normal = ["Changed Mind", "Wrong Item", "Other"]
    for sale in sales:
        sale_date = date.fromisoformat(sale["sale_date"])
        sku, channel, month, year = (
            sale["product_sku"], sale["channel"],
            sale_date.month, sale_date.year,
        )
        ret_prob = 0.07
        def_prob = 0.10
        if sku == "AURA-HP-001" and channel == "Online" and year == 2026 and month == 1:
            ret_prob, def_prob = 0.18, 0.65
        elif sku == "AURA-HP-001" and year == 2026 and month >= 2:
            ret_prob = 0.07

        for _ in range(sale["units_sold"]):
            if random.random() < ret_prob:
                is_defective = random.random() < def_prob
                reason = "Defective" if is_defective else random.choice(reasons_normal)
                ret_date = sale_date + timedelta(days=random.randint(3, 25))
                refund = round(sale["actual_sales"] / sale["units_sold"] * random.uniform(0.85, 1.0), 2)
                returns.append({
                    "return_id": f"RET-{year}-{ret_id:06d}",
                    "return_date": ret_date.isoformat(),
                    "sale_date": sale["sale_date"],
                    "product_sku": sku,
                    "product_name": sale["product_name"],
                    "geo_territory": sale["geo_territory"],
                    "channel": channel,
                    "return_reason": reason,
                    "refund_amount": refund,
                    "return_rate": round(ret_prob, 3),
                })
                ret_id += 1
    return returns


def generate_customer_metrics():
    rows, met_id = [], 1
    current = START_DATE.replace(day=1)
    end = END_DATE.replace(day=1)
    while current <= end:
        month, year = current.month, current.year
        for region in REGIONS:
            for segment in SEGMENTS:
                active = random.randint(800, 1200)
                new_cust = random.randint(40, 80)
                churn = round(random.uniform(0.03, 0.05), 3)
                aov = round(random.uniform(45, 120), 2)
                repeat = round(random.uniform(0.25, 0.40), 3)
                if segment == "SMB" and region == "South":
                    if year == 2026 and month == 2:
                        churn = round(random.uniform(0.10, 0.12), 3)
                    elif year == 2026 and month == 3:
                        churn = round(random.uniform(0.13, 0.15), 3)
                        repeat = round(random.uniform(0.15, 0.22), 3)
                if segment == "SMB" and region == "East" and year == 2026 and month == 3:
                    churn = round(random.uniform(0.07, 0.09), 3)
                if segment == "Consumer" and region == "North" and year == 2026 and month == 1:
                    new_cust = random.randint(120, 160)
                    active = random.randint(1300, 1500)
                rows.append({
                    "metric_id": f"MET-{year}-{met_id:04d}",
                    "metric_month": current.isoformat(),
                    "geo_territory": region,
                    "customer_segment": segment,
                    "active_customer_count": active,
                    "new_customer_count": new_cust,
                    "churned_customer_count": max(1, int(active * churn)),
                    "churn_rate": churn,
                    "avg_order_value": aov,
                    "repeat_purchase_rate": repeat,
                })
                met_id += 1
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return rows


# ============================================================
# DDL
# ============================================================

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS aura_sales (
        sale_id          TEXT PRIMARY KEY,
        sale_date        DATE,
        geo_territory    TEXT,
        channel          TEXT,
        product_sku      TEXT,
        product_name     TEXT,
        product_category TEXT,
        actual_sales     NUMERIC(12,2),
        units_sold       INTEGER,
        ad_spend         NUMERIC(10,2),
        discount_rate    NUMERIC(4,2)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_catalogue (
        product_sku      TEXT PRIMARY KEY,
        product_name     TEXT,
        product_category TEXT,
        launch_date      DATE,
        rrp_gbp          NUMERIC(8,2),
        channel_avail    TEXT DEFAULT 'All',
        is_active        BOOLEAN DEFAULT TRUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS return_events (
        return_id      TEXT PRIMARY KEY,
        return_date    DATE,
        sale_date      DATE,
        product_sku    TEXT,
        product_name   TEXT,
        geo_territory  TEXT,
        channel        TEXT,
        return_reason  TEXT,
        refund_amount  NUMERIC(10,2),
        return_rate    NUMERIC(4,3)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customer_metrics (
        metric_id              TEXT PRIMARY KEY,
        metric_month           DATE,
        geo_territory          TEXT,
        customer_segment       TEXT,
        active_customer_count  INTEGER,
        new_customer_count     INTEGER,
        churned_customer_count INTEGER,
        churn_rate             NUMERIC(4,3),
        avg_order_value        NUMERIC(8,2),
        repeat_purchase_rate   NUMERIC(4,3)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jargon_overrides (
        term        TEXT PRIMARY KEY,
        replacement TEXT NOT NULL,
        category    TEXT DEFAULT 'custom'
    )
    """,
]


# ============================================================
# Seed helpers
# ============================================================

def _insert_batch(cur, table, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    col_str = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    values = [tuple(r[c] for c in cols) for r in rows]
    batch_size = 500
    for i in range(0, len(values), batch_size):
        cur.executemany(sql, values[i:i + batch_size])
    print(f"  OK {table}: {len(rows)} rows loaded")


def seed(verify_only=False):
    print("Connecting to Neon... ", end="", flush=True)
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("connected OK\n")

    if verify_only:
        verify(cur)
        cur.close()
        conn.close()
        return

    # Create tables
    print("Creating tables...")
    for stmt in DDL_STATEMENTS:
        cur.execute(stmt)
    print("OK All tables ready\n")

    # Generate data
    print("Generating seed data...")
    random.seed(42)
    sales = generate_sales_data()
    products = [
        {
            "product_sku": p[0],
            "product_name": p[1],
            "product_category": p[2],
            "launch_date": p[3],
            "rrp_gbp": p[4],
            "channel_avail": "All",
            "is_active": True,
        }
        for p in PRODUCTS
    ]
    returns = generate_return_events(sales)
    metrics = generate_customer_metrics()
    print(f"  Generated: {len(sales)} sales, {len(products)} products, "
          f"{len(returns)} returns, {len(metrics)} metrics\n")

    # Load
    print("Loading to Neon...")
    _insert_batch(cur, "product_catalogue", products)
    _insert_batch(cur, "aura_sales", sales)
    _insert_batch(cur, "return_events", returns)
    _insert_batch(cur, "customer_metrics", metrics)

    print()
    verify(cur)
    cur.close()
    conn.close()
    print("\nOK Neon seeding complete!")


def verify(cur):
    print("Verifying row counts...")
    for table in ["aura_sales", "product_catalogue", "return_events", "customer_metrics"]:
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        row = cur.fetchone()
        print(f"  {table}: {row['cnt']} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Neon (PostgreSQL) with Aura Retail data")
    parser.add_argument("--verify", action="store_true", help="Only verify row counts")
    args = parser.parse_args()
    seed(verify_only=args.verify)
