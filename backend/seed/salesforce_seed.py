"""
OmniData — Salesforce CRM Seed Script

Seeds Salesforce CRM data into Pinecone dense index (salesforce_crm namespace)
AND optionally into the live Salesforce org.

Flow:
1. Load salesforce_crm.json (35 accounts, 20 opps, 40 cases)
2. Convert each record into a rich text document
3. Group related records (account + its opps + its cases) for context
4. Upsert into Pinecone omnidata-dense / salesforce_crm namespace
5. Optionally push to live Salesforce org if --live flag is passed

Usage:
    python -m seed.salesforce_seed                  # Pinecone only
    python -m seed.salesforce_seed --live            # Pinecone + Salesforce org
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vector.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Config ────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "data" / "salesforce_crm.json"
INDEX_NAME = os.getenv("PINECONE_DENSE_INDEX", "omnidata-dense")
NAMESPACE = "salesforce_crm"
BATCH_SIZE = 5
BATCH_DELAY = 2.0  # seconds between batches


def load_crm_data() -> dict:
    """Load CRM data from JSON file, grouped by object type."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = {}
    for group in data:
        obj_type = group["object_type"]
        result[obj_type] = group["records"]

    logger.info(
        f"Loaded CRM data: "
        + ", ".join(f"{len(v)} {k}s" for k, v in result.items())
    )
    return result


def build_account_documents(crm_data: dict) -> list[dict]:
    """
    Build rich text documents for each account, enriched with
    related opportunities and cases.
    
    Each document becomes a Pinecone record with:
    - _id: unique identifier
    - text: rich description for semantic search
    - metadata: structured fields for filtering
    """
    accounts = crm_data.get("Account", [])
    opportunities = crm_data.get("Opportunity", [])
    cases = crm_data.get("Case", [])

    # Index opportunities and cases by account name
    opps_by_account = {}
    for opp in opportunities:
        name = opp.get("AccountName", "")
        opps_by_account.setdefault(name, []).append(opp)

    cases_by_account = {}
    for case in cases:
        name = case.get("AccountName", "")
        cases_by_account.setdefault(name, []).append(case)

    documents = []
    for i, acc in enumerate(accounts):
        name = acc["Name"]
        region = acc.get("Region__c", "")
        segment = acc.get("CustomerSegment__c", "")
        churn_risk = acc.get("ChurnRisk__c", "")
        acv = acc.get("AnnualContractValue__c", 0)
        last_purchase = acc.get("LastPurchaseDate__c", "")
        partner_tier = acc.get("PartnerTier__c", "")
        industry = acc.get("Industry", "")

        # Build account summary
        text_parts = [
            f"Salesforce Account: {name}",
            f"Region: {region} | Segment: {segment} | Industry: {industry}",
            f"Churn Risk: {churn_risk} | Partner Tier: {partner_tier}",
            f"Annual Contract Value (ACV): £{acv:,.0f}",
            f"Last Purchase Date: {last_purchase}",
        ]

        # Add related opportunities
        account_opps = opps_by_account.get(name, [])
        if account_opps:
            total_pipeline = sum(o.get("Amount", 0) for o in account_opps)
            text_parts.append(
                f"\nOpen Opportunities ({len(account_opps)} deals, £{total_pipeline:,.0f} pipeline):"
            )
            for opp in account_opps:
                text_parts.append(
                    f"  - {opp['Name']}: £{opp['Amount']:,.0f} | "
                    f"Stage: {opp['StageName']} | Close: {opp['CloseDate']}"
                )

        # Add related cases
        account_cases = cases_by_account.get(name, [])
        if account_cases:
            open_cases = [c for c in account_cases if c["Status"] != "Closed"]
            text_parts.append(
                f"\nSupport Cases ({len(account_cases)} total, {len(open_cases)} open):"
            )
            for case in account_cases[:5]:  # Limit to top 5 for each account
                text_parts.append(
                    f"  - [{case['Priority']}] {case['Subject']} "
                    f"({case['Status']}, {case.get('CreatedDate', '')})"
                )
                if case.get("Description"):
                    text_parts.append(f"    {case['Description'][:150]}")

        text = "\n".join(text_parts)

        documents.append({
            "_id": f"sf_account_{i:03d}_{name.lower().replace(' ', '_')[:30]}",
            "text": text,
            "object_type": "Account",
            "account_name": name,
            "region": region,
            "segment": segment,
            "churn_risk": churn_risk,
            "acv": acv,
            "partner_tier": partner_tier,
            "source": "salesforce",
        })

    return documents


def build_case_documents(crm_data: dict) -> list[dict]:
    """
    Build separate documents for case clusters (product issues, pricing complaints).
    These give thematic searchability beyond individual accounts.
    """
    cases = crm_data.get("Case", [])
    documents = []

    # Cluster 1: AuraSound Pro defect cases
    defect_cases = [c for c in cases if "AuraSound Pro" in c.get("Subject", "") and c.get("Priority") == "High"]
    if defect_cases:
        text = (
            f"Salesforce Case Cluster: AuraSound Pro Product Defect\n"
            f"Total Cases: {len(defect_cases)} high-priority cases\n"
            f"Period: January 2026\n"
            f"Issue: Firmware defect in batches AU-0126-A through AU-0126-F causing "
            f"intermittent audio dropout. Cases filed by {len(set(c['AccountName'] for c in defect_cases))} "
            f"different accounts across all regions.\n\n"
            f"Affected Accounts:\n"
        )
        for c in defect_cases:
            text += f"  - {c['AccountName']}: {c['Subject']} ({c.get('CreatedDate', '')})\n"

        documents.append({
            "_id": "sf_cluster_aurasound_defect",
            "text": text,
            "object_type": "CaseCluster",
            "cluster_type": "product_defect",
            "product_sku": "AURA-HP-001",
            "source": "salesforce",
        })

    # Cluster 2: Partner pricing complaints  
    pricing_cases = [c for c in cases if "pric" in c.get("Subject", "").lower() or "pric" in c.get("Description", "").lower()]
    if pricing_cases:
        text = (
            f"Salesforce Case Cluster: Partner Channel Price Increase Complaints\n"
            f"Total Cases: {len(pricing_cases)} cases\n"
            f"Period: February–March 2026\n"
            f"Issue: Following the 12% Partner channel price increase in February 2026, "
            f"multiple SMB accounts filed complaints and churn warnings. "
            f"Concentrated in South and East regions.\n\n"
            f"Affected Accounts:\n"
        )
        for c in pricing_cases:
            text += f"  - {c['AccountName']}: {c['Subject']} ({c.get('CreatedDate', '')})\n"
            if c.get("Description"):
                text += f"    {c['Description'][:120]}\n"

        documents.append({
            "_id": "sf_cluster_pricing_complaints",
            "text": text,
            "object_type": "CaseCluster",
            "cluster_type": "pricing_complaint",
            "source": "salesforce",
        })

    # Cluster 3: Churn risk escalations
    churn_cases = [c for c in cases if "churn" in c.get("Subject", "").lower()]
    if churn_cases:
        text = (
            f"Salesforce Case Cluster: Churn Risk Escalations\n"
            f"Total Cases: {len(churn_cases)}\n"
            f"Period: March 2026\n"
            f"Regions: South and East\n"
            f"Context: Account managers escalating churn risks for SMB partners "
            f"following the February price increase.\n\n"
        )
        for c in churn_cases:
            text += f"  - {c['AccountName']}: {c['Description'][:150]}\n"

        documents.append({
            "_id": "sf_cluster_churn_escalations",
            "text": text,
            "object_type": "CaseCluster",
            "cluster_type": "churn_risk",
            "source": "salesforce",
        })

    return documents


def build_pipeline_summary(crm_data: dict) -> list[dict]:
    """Build regional pipeline summary documents."""
    opportunities = crm_data.get("Opportunity", [])
    documents = []

    # Group by region
    by_region = {}
    for opp in opportunities:
        region = opp.get("Region__c", "Unknown")
        by_region.setdefault(region, []).append(opp)

    for region, opps in by_region.items():
        total = sum(o["Amount"] for o in opps)
        stages = {}
        for o in opps:
            s = o["StageName"]
            stages[s] = stages.get(s, 0) + o["Amount"]

        text = (
            f"Salesforce Pipeline Summary — {region} Region\n"
            f"Total Open Pipeline: £{total:,.0f}\n"
            f"Deal Count: {len(opps)}\n\n"
            f"By Stage:\n"
        )
        for stage, amount in sorted(stages.items(), key=lambda x: -x[1]):
            text += f"  - {stage}: £{amount:,.0f}\n"

        text += f"\nDeals:\n"
        for o in opps:
            text += f"  - {o['Name']}: £{o['Amount']:,.0f} ({o['StageName']}, closes {o['CloseDate']})\n"

        documents.append({
            "_id": f"sf_pipeline_{region.lower()}",
            "text": text,
            "object_type": "PipelineSummary",
            "region": region,
            "total_pipeline": total,
            "deal_count": len(opps),
            "source": "salesforce",
        })

    return documents


def seed_pinecone(client: PineconeClient, documents: list[dict]):
    """Upsert documents into Pinecone in batches."""
    total = len(documents)
    logger.info(f"Seeding {total} documents into Pinecone [{INDEX_NAME}/{NAMESPACE}]")

    for i in range(0, total, BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]

        # Build records for upsert (needs _id and text fields)
        records = []
        for doc in batch:
            record = {"_id": doc["_id"], "text": doc["text"]}
            # Add metadata fields (everything except _id and text)
            for k, v in doc.items():
                if k not in ("_id", "text"):
                    record[k] = v
            records.append(record)

        client.upsert_records(
            index_name=INDEX_NAME,
            namespace=NAMESPACE,
            records=records,
        )

        logger.info(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} docs upserted")

        if i + BATCH_SIZE < total:
            time.sleep(BATCH_DELAY)

    logger.info(f"✓ Pinecone seed complete: {total} documents in [{NAMESPACE}]")


def seed_live_salesforce(crm_data: dict):
    """Push CRM records to the live Salesforce org."""
    from src.connectors.salesforce_connector import SalesforceConnector

    sf = SalesforceConnector()
    if not sf.connect():
        logger.error("Failed to connect to Salesforce. Skipping live seed.")
        return

    logger.info("Connected to Salesforce org — seeding records...")

    # 1. Create Accounts
    accounts = crm_data.get("Account", [])
    # Filter to fields Salesforce actually accepts
    sf_accounts = []
    for acc in accounts:
        sf_acc = {
            "Name": acc["Name"],
            "Industry": acc.get("Industry", ""),
        }
        # Custom fields — only include if they exist on the org
        for field in ["Region__c", "CustomerSegment__c", "ChurnRisk__c",
                       "AnnualContractValue__c", "LastPurchaseDate__c", "PartnerTier__c"]:
            if field in acc:
                sf_acc[field] = acc[field]
        sf_accounts.append(sf_acc)

    count = sf.upsert_accounts(sf_accounts)
    logger.info(f"  Accounts: {count}/{len(sf_accounts)} created")

    # 2. Build account name → ID map
    existing = sf.query("SELECT Id, Name FROM Account ORDER BY Name")
    account_map = {r["Name"]: r["Id"] for r in existing}

    # 3. Create Opportunities
    opportunities = crm_data.get("Opportunity", [])
    count = sf.upsert_opportunities(opportunities, account_map)
    logger.info(f"  Opportunities: {count}/{len(opportunities)} created")

    # 4. Create Cases
    cases = crm_data.get("Case", [])
    count = sf.upsert_cases(cases, account_map)
    logger.info(f"  Cases: {count}/{len(cases)} created")

    logger.info("✓ Live Salesforce seed complete")


def main():
    parser = argparse.ArgumentParser(description="Seed Salesforce CRM data")
    parser.add_argument("--live", action="store_true", help="Also push to live Salesforce org")
    args = parser.parse_args()

    from dotenv import load_dotenv
    # .env is at project root: backend/../.env
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    # Load data
    crm_data = load_crm_data()

    # Build documents
    account_docs = build_account_documents(crm_data)
    case_cluster_docs = build_case_documents(crm_data)
    pipeline_docs = build_pipeline_summary(crm_data)

    all_docs = account_docs + case_cluster_docs + pipeline_docs
    logger.info(
        f"Built {len(all_docs)} documents: "
        f"{len(account_docs)} accounts, "
        f"{len(case_cluster_docs)} case clusters, "
        f"{len(pipeline_docs)} pipeline summaries"
    )

    # Seed Pinecone
    api_key = os.getenv("PINECONE_API_KEY", "")
    client = PineconeClient(api_key=api_key)
    seed_pinecone(client, all_docs)

    # Optionally seed live Salesforce
    if args.live:
        seed_live_salesforce(crm_data)
    else:
        logger.info("Skipping live Salesforce seed (use --live flag to enable)")


if __name__ == "__main__":
    main()
