"""
OmniData — Salesforce CRM Store

Wrapper over PineconeClient.dense_query() for retrieving
Salesforce CRM records (accounts, opportunities, cases).

Queries the `salesforce_crm` namespace in the dense index.
Falls back to live Salesforce SOQL if vector search returns no results
and a SalesforceConnector is available.
"""

import logging
from typing import Optional, Any

from src.vector.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)

DEFAULT_INDEX = "omnidata-dense"
NAMESPACE = "salesforce_crm"


def search_salesforce_crm(
    client: PineconeClient,
    query: str,
    index_name: str = DEFAULT_INDEX,
    top_k: int = 5,
    salesforce_connector: Any = None,
    filter: dict = None,
) -> list[dict]:
    """
    Search Salesforce CRM data using dense vector search against Pinecone.
    
    Primary: Pinecone dense search (fast, reliable for demo)
    Fallback: Live Salesforce SOQL via SalesforceConnector (if available)
    
    Returns top_k CRM records with metadata:
        - id, score, text, object_type, account_name, region, segment, etc.
    """
    # ── Primary: Pinecone vector search ───────────────────
    matches = client.dense_query(
        index_name=index_name,
        namespace=NAMESPACE,
        query_text=query,
        top_k=top_k,
        filter=filter,
    )

    results = []
    for m in matches:
        meta = m.get("metadata", {})
        results.append({
            "id": m["id"],
            "score": m["score"],
            "text": meta.get("text", ""),
            "object_type": meta.get("object_type", "Account"),
            "account_name": meta.get("account_name", ""),
            "region": meta.get("region", ""),
            "segment": meta.get("segment", ""),
            "churn_risk": meta.get("churn_risk", ""),
            "acv": meta.get("acv", 0),
            "partner_tier": meta.get("partner_tier", ""),
            "source": "salesforce",
        })

    # Deduplicate: if multiple entries for same account, keep highest scoring
    seen = {}
    deduped = []
    for r in results:
        key = r["account_name"] or r["id"]
        if key not in seen:
            seen[key] = r
            deduped.append(r)
        else:
            existing = seen[key]
            if r["score"] > existing["score"]:
                existing["score"] = r["score"]
            # Merge text for richer context
            existing["text"] += "\n\n" + r["text"]

    logger.info(
        f"Salesforce CRM search: '{query[:60]}...' → {len(results)} matches, "
        f"{len(deduped)} unique records"
    )

    # ── Fallback: Live Salesforce SOQL ────────────────────
    if not deduped and salesforce_connector:
        logger.info("No vector results — attempting live Salesforce SOQL fallback")
        try:
            live_results = _live_salesforce_search(salesforce_connector, query)
            if live_results:
                return live_results
        except Exception as e:
            logger.warning(f"Live Salesforce fallback failed: {e}")

    return deduped


def _live_salesforce_search(connector: Any, query: str) -> list[dict]:
    """
    Fallback: execute a basic SOQL query against live Salesforce.
    Only triggered if vector search returns empty.
    """
    if not connector.is_connected:
        connector.connect()

    # Simple keyword-based SOQL generation
    query_lower = query.lower()

    soql = None
    if "churn" in query_lower or "risk" in query_lower:
        soql = (
            "SELECT Name, Region__c, CustomerSegment__c, ChurnRisk__c, "
            "AnnualContractValue__c, LastPurchaseDate__c "
            "FROM Account WHERE ChurnRisk__c = 'High' "
            "ORDER BY AnnualContractValue__c DESC LIMIT 20"
        )
    elif "pipeline" in query_lower or "opportunity" in query_lower or "deal" in query_lower:
        soql = (
            "SELECT Name, Account.Name, Amount, StageName, CloseDate "
            "FROM Opportunity "
            "WHERE StageName NOT IN ('Closed Won', 'Closed Lost') "
            "ORDER BY Amount DESC LIMIT 20"
        )
    elif "case" in query_lower or "complaint" in query_lower or "support" in query_lower:
        soql = (
            "SELECT Subject, Account.Name, Priority, Status, CreatedDate "
            "FROM Case ORDER BY CreatedDate DESC LIMIT 20"
        )
    else:
        soql = (
            "SELECT Name, Region__c, CustomerSegment__c, ChurnRisk__c, "
            "AnnualContractValue__c FROM Account ORDER BY Name LIMIT 20"
        )

    records = connector.query(soql)

    return [{
        "id": f"sf_live_{i}",
        "score": 0.9,
        "text": str(record),
        "object_type": "LiveQuery",
        "account_name": record.get("Name", ""),
        "region": record.get("Region__c", ""),
        "segment": record.get("CustomerSegment__c", ""),
        "churn_risk": record.get("ChurnRisk__c", ""),
        "acv": record.get("AnnualContractValue__c", 0),
        "partner_tier": "",
        "source": "salesforce",
    } for i, record in enumerate(records)]
