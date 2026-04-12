"""Test multiple queries against the OmniData pipeline."""
import httpx

queries = [
    "Why are returns spiking for AuraSound Pro?",
    "What is the churn rate for SMB customers in the South region?",
    "How is the Partner channel trending?",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    print('='*60)
    
    r = httpx.post(
        "http://localhost:8000/query",
        json={"query": q},
        timeout=90,
    )
    
    data = r.json()
    tier = data.get('confidence_tier', 'N/A')
    score = data.get('confidence_score', 0)
    chart = data.get('chart_type', 'N/A')
    time_ms = data.get('processing_time_ms', 0)
    sql = data.get('sql', '')[:150]
    rows = len(data.get('chart_data', []))
    
    print(f"Confidence: {tier} ({score}) | Chart: {chart} | Time: {time_ms}ms | Rows: {rows}")
    print(f"SQL: {sql}")
    print(f"---")
    print(data.get('response', '')[:400])
