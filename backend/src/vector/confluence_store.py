"""
OmniData — Confluence Store

Wrapper over PineconeClient.dense_query() for retrieving
Confluence knowledge base documents.

Queries the `confluence_store` namespace in the dense index.
"""

import logging
from typing import Optional

from src.vector.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)

# Default index name — overridden at init
DEFAULT_INDEX = "omnidata-dense"
NAMESPACE = "confluence_store"


def search_confluence(
    client: PineconeClient,
    query: str,
    index_name: str = DEFAULT_INDEX,
    top_k: int = 5,
) -> list[dict]:
    """
    Search the Confluence knowledge base using dense vector search.
    
    Returns top_k document chunks with metadata:
      - id, score, title, space, text, doc_id, chunk_index
    """
    matches = client.dense_query(
        index_name=index_name,
        namespace=NAMESPACE,
        query_text=query,
        top_k=top_k,
    )
    
    # Enrich each match with structured fields
    results = []
    for m in matches:
        meta = m.get("metadata", {})
        results.append({
            "id": m["id"],
            "score": m["score"],
            "title": meta.get("title", "Unknown"),
            "space": meta.get("space", ""),
            "text": meta.get("text", ""),
            "doc_id": meta.get("doc_id", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "source": "confluence",
        })
    
    # Deduplicate: if multiple chunks from same document, keep highest scoring
    seen_docs = {}
    deduped = []
    for r in results:
        doc_id = r["doc_id"]
        if doc_id not in seen_docs:
            seen_docs[doc_id] = r
            deduped.append(r)
        else:
            # Keep higher score, but append the chunk text to existing
            existing = seen_docs[doc_id]
            if r["score"] > existing["score"]:
                existing["score"] = r["score"]
            # Merge text from additional chunks for richer context
            existing["text"] += "\n\n" + r["text"]
    
    logger.info(
        f"Confluence search: '{query[:60]}...' → {len(results)} chunks, "
        f"{len(deduped)} unique documents"
    )
    
    return deduped
