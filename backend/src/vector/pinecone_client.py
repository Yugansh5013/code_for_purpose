"""
OmniData — Shared Pinecone Client

Provides a single Pinecone client instance with methods for
hybrid search (dense + sparse) and dense-only search.

Embeddings are generated server-side via Pinecone Inference API —
no local models required.
"""

import logging
from typing import Optional

from pinecone import Pinecone

logger = logging.getLogger(__name__)


class PineconeClient:
    """
    Shared Pinecone client for all vector operations.
    
    Handles:
    - Hybrid search (dense + sparse via Inference API)
    - Dense-only search (integrated inference — raw text in)
    - Upsert with server-side embedding
    
    Usage:
        client = PineconeClient(api_key="pcsk_...")
        results = client.hybrid_query("omnidata-hybrid", "schema_store", "revenue by region")
    """

    DENSE_MODEL = "multilingual-e5-large"
    SPARSE_MODEL = "pinecone-sparse-english-v0"

    def __init__(self, api_key: str):
        self.pc = Pinecone(api_key=api_key)
        logger.info("Pinecone client initialized")

    def hybrid_query(
        self,
        index_name: str,
        namespace: str,
        query_text: str,
        top_k: int = 3,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        """
        Search using integrated inference — the index handles embedding
        server-side. Just pass raw text in, get scored matches out.
        
        Uses the search() API which auto-embeds with the index's configured model.
        
        Returns list of matches with id, score, and metadata.
        """
        try:
            index = self.pc.Index(index_name)
            
            search_params = {
                "namespace": namespace,
                "query": {"inputs": {"text": query_text}, "top_k": top_k},
            }
            if filter:
                search_params["query"]["filter"] = filter
            
            results = index.search(**search_params)
            
            matches = []
            if hasattr(results, 'result') and hasattr(results.result, 'hits'):
                for hit in results.result.hits:
                    fields = hit.get("fields", {})
                    matches.append({
                        "id": hit.get("_id", ""),
                        "score": hit.get("_score", 0.0),
                        "metadata": fields,
                    })
            
            logger.info(
                f"Search [{namespace}]: '{query_text[:50]}...' "
                f"→ {len(matches)} matches (top score: {matches[0]['score']:.3f})"
                if matches else f"Search [{namespace}]: no matches"
            )
            return matches

        except Exception as e:
            logger.error(f"Search error [{namespace}]: {e}")
            raise

    def dense_query(
        self,
        index_name: str,
        namespace: str,
        query_text: str,
        top_k: int = 3,
        filter: dict = None,
    ) -> list[dict]:
        """
        Dense-only search using integrated inference.
        The index handles embedding server-side — just pass raw text.
        
        Used for Confluence/document search (Phase 2).
        Supports optional metadata filtering for RBAC.
        """
        try:
            index = self.pc.Index(index_name)
            
            search_params = {
                "namespace": namespace,
                "query": {"inputs": {"text": query_text}, "top_k": top_k},
            }
            if filter:
                search_params["query"]["filter"] = filter
            
            results = index.search(**search_params)
            
            matches = []
            if hasattr(results, 'result') and hasattr(results.result, 'hits'):
                for hit in results.result.hits:
                    matches.append({
                        "id": hit.get("_id", ""),
                        "score": hit.get("_score", 0.0),
                        "metadata": hit.get("fields", {}),
                    })
            
            logger.info(
                f"Dense query [{namespace}]: '{query_text[:50]}...' → {len(matches)} matches"
            )
            return matches

        except Exception as e:
            logger.error(f"Dense query error [{namespace}]: {e}")
            raise

    def upsert_records(
        self,
        index_name: str,
        namespace: str,
        records: list[dict],
    ) -> None:
        """
        Upsert records with integrated inference (text auto-embedded).
        
        Each record must have an '_id' field and a 'text' field.
        """
        try:
            index = self.pc.Index(index_name)
            index.upsert_records(namespace=namespace, records=records)
            logger.info(f"Upserted {len(records)} records to [{index_name}/{namespace}]")
        except Exception as e:
            logger.error(f"Upsert error [{index_name}/{namespace}]: {e}")
            raise

    def test_connection(self, index_name: str) -> bool:
        """Test connectivity to a Pinecone index."""
        try:
            index = self.pc.Index(index_name)
            stats = index.describe_index_stats()
            logger.info(f"Pinecone [{index_name}] connected: {stats.total_vector_count} vectors")
            return True
        except Exception as e:
            logger.error(f"Pinecone connection test failed: {e}")
            return False
