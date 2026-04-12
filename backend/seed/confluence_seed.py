"""
OmniData — Confluence Knowledge Base Seeder

Fetches pages from the Confluence client (live or demo mode),
chunks them, and upserts into the Pinecone dense index.

The ConfluenceClient auto-detects whether real credentials are
configured and falls back to local demo data if not.

Usage:
    python -m seed.confluence_seed           # Auto-detect mode
    python -m seed.confluence_seed --force   # Re-seed even if vectors exist
"""

import asyncio
import os
import sys
import time
import logging
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pinecone import Pinecone

from src.connectors.confluence_client import ConfluenceClient

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
DENSE_INDEX = os.environ.get("PINECONE_DENSE_INDEX", "omnidata-dense")
NAMESPACE = "confluence_store"
CHUNK_SIZE = 800   # chars per chunk (fits ~200 tokens)
CHUNK_OVERLAP = 100  # overlap to preserve context


def chunk_document(doc: dict) -> list[dict]:
    """
    Split a document into overlapping chunks.
    Each chunk gets the document title + space prepended for context.
    """
    content = doc["content"]
    title = doc["title"]
    space = doc["space"]
    doc_id = doc["id"]
    
    chunks = []
    start = 0
    chunk_idx = 0
    
    while start < len(content):
        end = start + CHUNK_SIZE
        chunk_text = content[start:end]
        
        # Try to break at sentence boundary
        if end < len(content):
            last_period = chunk_text.rfind(".")
            last_newline = chunk_text.rfind("\n")
            break_at = max(last_period, last_newline)
            if break_at > CHUNK_SIZE * 0.5:  # Only break if we're past half
                chunk_text = chunk_text[:break_at + 1]
                end = start + break_at + 1
        
        # Prepend title for retrieval context
        full_text = f"[{space}] {title}\n\n{chunk_text.strip()}"
        
        chunks.append({
            "_id": f"{doc_id}_chunk_{chunk_idx}",
            "text": full_text,
            "doc_id": doc_id,
            "title": title,
            "space": space,
            "chunk_index": chunk_idx,
            "source": "confluence",
        })
        
        chunk_idx += 1
        start = end - CHUNK_OVERLAP  # Overlap
        
        if start >= len(content):
            break
    
    return chunks


async def fetch_pages() -> list[dict]:
    """
    Fetch pages from Confluence using the client.
    
    Automatically uses LIVE mode if credentials are set in .env,
    or DEMO mode with local seed data otherwise.
    """
    client = ConfluenceClient(
        base_url=os.environ.get("CONFLUENCE_BASE_URL", ""),
        email=os.environ.get("CONFLUENCE_USER_EMAIL", ""),
        api_token=os.environ.get("CONFLUENCE_API_TOKEN", ""),
        default_space=os.environ.get("CONFLUENCE_DEFAULT_SPACE", "AURA"),
    )
    
    # Test connectivity
    connected = await client.test_connection()
    if not connected:
        logger.error("Cannot connect to Confluence (no credentials or data)")
        return []
    
    logger.info(f"Confluence mode: {client.mode_label.upper()}")
    
    # Fetch all pages from the configured space
    pages = await client.get_space_pages()
    logger.info(f"Fetched {len(pages)} pages from Confluence [{client.mode_label}]")
    
    return pages


def main():
    parser = argparse.ArgumentParser(description="Seed Confluence pages into Pinecone")
    parser.add_argument("--force", action="store_true", help="Re-seed even if vectors exist")
    args = parser.parse_args()
    
    # ── Fetch pages via Confluence client ─────────────
    documents = asyncio.run(fetch_pages())
    
    if not documents:
        logger.error("No documents to seed — exiting")
        return
    
    logger.info(f"Retrieved {len(documents)} documents for seeding")
    
    # ── Chunk all documents ───────────────────────────
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc)
        logger.info(f"  {doc['title'][:50]}... → {len(chunks)} chunks")
        all_chunks.extend(chunks)
    
    logger.info(f"Total chunks: {len(all_chunks)}")
    
    # ── Connect to Pinecone ───────────────────────────
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(DENSE_INDEX)
    
    # Check current stats
    stats = index.describe_index_stats()
    existing = stats.namespaces.get(NAMESPACE, {})
    existing_count = getattr(existing, 'record_count', 0) if existing else 0
    logger.info(f"Index [{DENSE_INDEX}] — existing vectors in '{NAMESPACE}': {existing_count}")
    
    if existing_count > 0 and not args.force:
        logger.info("Vectors already exist. Use --force to re-seed. Skipping.")
        return
    
    # ── Upsert in batches ─────────────────────────────
    BATCH_SIZE = 10
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        index.upsert_records(namespace=NAMESPACE, records=batch)
        logger.info(f"  Upserted batch {i // BATCH_SIZE + 1}: {len(batch)} chunks")
        time.sleep(1)  # Rate limit courtesy
    
    # ── Verify ────────────────────────────────────────
    logger.info("Waiting for index to sync...")
    time.sleep(5)
    
    stats = index.describe_index_stats()
    ns_stats = stats.namespaces.get(NAMESPACE, {})
    final_count = getattr(ns_stats, 'record_count', 0) if ns_stats else 0
    logger.info(f"✅ Seeding complete: {final_count} vectors in [{DENSE_INDEX}/{NAMESPACE}]")
    
    # ── Print summary ─────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Confluence Seed Summary")
    print(f"  Documents: {len(documents)}")
    print(f"  Chunks:    {len(all_chunks)}")
    print(f"  Index:     {DENSE_INDEX}")
    print(f"  Namespace: {NAMESPACE}")
    print(f"  Vectors:   {final_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
