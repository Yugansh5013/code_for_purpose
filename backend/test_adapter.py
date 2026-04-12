"""Quick test of the frontend adapter endpoints."""
import requests
import json

BASE = "http://localhost:8000"

# Test 1: /api/status
print("=== /api/status ===")
r = requests.get(f"{BASE}/api/status")
print(json.dumps(r.json(), indent=2))

# Test 2: /api/metrics
print("\n=== /api/metrics ===")
r = requests.get(f"{BASE}/api/metrics")
d = r.json()
print(f"{len(d['metrics'])} metrics")
print(json.dumps(d["metrics"][0], indent=2))

# Test 3: /api/chat
print("\n=== /api/chat (churn risk query) ===")
r = requests.post(f"{BASE}/api/chat", json={
    "session_id": "test-session",
    "message": "Which accounts are at high churn risk?"
}, timeout=120)
d = r.json()

print(f"type: {d['type']}")
print(f"message_id: {d['message_id']}")

if d["type"] == "answer":
    a = d["answer"]
    print(f"\nbranches: {a['branches']}")
    print(f"trace: {len(a['trace'])} entries")
    for t in a["trace"]:
        highlight = " <<<" if t.get("highlight") else ""
        detail = t['detail'].encode('ascii', 'replace').decode('ascii')
        print(f"  [{t['node']}] {detail}{highlight}")
    
    print(f"\nsources: {len(a['sources'])} chips")
    for s in a["sources"]:
        print(f"  {s['source_type']}: {s['label']} (conf: {s.get('confidence', '-')})")
    
    print(f"\nchart_data: {'yes' if a.get('chart_data') else 'no'}")
    print(f"stat_updates: {len(a.get('stat_updates') or [])}")
    
    t = a.get("transparency", {})
    print(f"\ntransparency.sql: {'yes' if t.get('sql') else 'no'}")
    print(f"transparency.context_chunks: {len(t.get('context_chunks') or [])}")
    print(f"transparency.confidence: {t.get('confidence', {}).get('tier', 'none')} ({t.get('confidence', {}).get('score', 0)})")
    print(f"transparency.semantic_substitutions: {len(t.get('semantic_substitutions') or [])}")
    
    print(f"\nresponse (first 300 chars):\n{a['text'][:300]}")

print("\n\nAll adapter tests complete!")
