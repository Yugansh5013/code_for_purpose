"""
OmniData — Confluence API Client

Production-grade client for the Atlassian Confluence REST API.
Retrieves pages from Confluence spaces, with automatic fallback
to local demo data when credentials are not configured.

Integration Modes:
    1. LIVE MODE  — connects to real Confluence instance via REST API
    2. DEMO MODE  — loads from local seed data (for development/hackathon)

The mode is auto-detected from environment configuration.

Usage:
    client = ConfluenceClient(
        base_url="https://your-domain.atlassian.net/wiki",
        email="user@example.com",
        api_token="your-token",
        default_space="AURA",
    )
    pages = await client.get_space_pages(space_key="AURA")
"""

import json
import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Confluence REST API v2 endpoints
CONFLUENCE_SEARCH_ENDPOINT = "/rest/api/content/search"
CONFLUENCE_CONTENT_ENDPOINT = "/rest/api/content"
CONFLUENCE_SPACE_ENDPOINT = "/rest/api/space"

# Local demo data path (relative to backend root)
DEMO_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "seed" / "data" / "confluence_pages.json"


class ConfluenceClient:
    """
    Atlassian Confluence REST API client with demo fallback.
    
    Automatically detects whether live Confluence credentials are
    configured. If not, transparently serves pages from the local
    seed data to enable full pipeline testing without external deps.
    """
    
    def __init__(
        self,
        base_url: str = "",
        email: str = "",
        api_token: str = "",
        default_space: str = "AURA",
    ):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.email = email
        self.api_token = api_token
        self.default_space = default_space
        
        # Auto-detect mode
        self.live_mode = bool(self.base_url and self.email and self.api_token)
        self._demo_cache: Optional[list[dict]] = None
        
        mode = "LIVE" if self.live_mode else "DEMO"
        logger.info(f"Confluence client initialized [{mode}]")
        if self.live_mode:
            logger.info(f"  Base URL: {self.base_url}")
            logger.info(f"  User: {self.email}")
            logger.info(f"  Space: {self.default_space}")
        else:
            logger.info(f"  Using local demo data from: {DEMO_DATA_PATH.name}")
    
    @property
    def is_connected(self) -> bool:
        """Whether the client is in live mode with valid credentials."""
        return self.live_mode
    
    @property
    def mode_label(self) -> str:
        return "live" if self.live_mode else "demo"
    
    # ── Live Confluence API Methods ───────────────────────
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict:
        """
        Make an authenticated request to the Confluence REST API.
        
        Uses HTTP Basic Auth with email + API token (Atlassian Cloud).
        """
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                auth=(self.email, self.api_token),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> bool:
        """
        Test connectivity to the Confluence instance.
        
        Returns True if the API responds successfully.
        """
        if not self.live_mode:
            # Demo mode — check local data exists
            return DEMO_DATA_PATH.exists()
        
        try:
            result = await self._api_request(
                "GET",
                CONFLUENCE_SPACE_ENDPOINT,
                params={"limit": 1},
            )
            spaces = result.get("results", [])
            logger.info(f"Confluence connection OK — {len(spaces)} space(s) accessible")
            return True
        except Exception as e:
            logger.error(f"Confluence connection failed: {e}")
            return False
    
    async def get_space_pages(
        self,
        space_key: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Retrieve all pages from a Confluence space.
        
        In LIVE mode: calls the Confluence REST API with CQL search.
        In DEMO mode: loads from local seed data.
        
        Args:
            space_key: Confluence space key (defaults to configured space)
            limit: Maximum number of pages to retrieve
            
        Returns:
            List of page dicts with id, title, space, content fields
        """
        space_key = space_key or self.default_space
        
        if not self.live_mode:
            return self._load_demo_pages(space_key)
        
        try:
            # CQL query to fetch all pages in the space
            cql = f"space={space_key} AND type=page"
            
            result = await self._api_request(
                "GET",
                CONFLUENCE_SEARCH_ENDPOINT,
                params={
                    "cql": cql,
                    "limit": limit,
                    "expand": "body.storage,metadata.labels,space",
                },
            )
            
            pages = []
            for item in result.get("results", []):
                pages.append({
                    "id": f"confluence_{item['id']}",
                    "title": item.get("title", ""),
                    "space": space_key,
                    "content": self._extract_text_from_storage(
                        item.get("body", {}).get("storage", {}).get("value", "")
                    ),
                    "labels": [
                        l["name"]
                        for l in item.get("metadata", {}).get("labels", {}).get("results", [])
                    ],
                    "url": f"{self.base_url}{item.get('_links', {}).get('webui', '')}",
                    "last_modified": item.get("version", {}).get("when", ""),
                })
            
            logger.info(f"Retrieved {len(pages)} pages from Confluence [{space_key}]")
            return pages
            
        except Exception as e:
            logger.error(f"Failed to fetch pages from Confluence: {e}")
            logger.info("Falling back to demo data")
            return self._load_demo_pages(space_key)
    
    async def get_page_by_id(self, page_id: str) -> Optional[dict]:
        """
        Retrieve a single page by its Confluence page ID.
        
        Args:
            page_id: The Confluence page ID
            
        Returns:
            Page dict or None if not found
        """
        if not self.live_mode:
            pages = self._load_demo_pages()
            return next((p for p in pages if p["id"] == page_id), None)
        
        try:
            result = await self._api_request(
                "GET",
                f"{CONFLUENCE_CONTENT_ENDPOINT}/{page_id}",
                params={"expand": "body.storage,space,version"},
            )
            
            return {
                "id": f"confluence_{result['id']}",
                "title": result.get("title", ""),
                "space": result.get("space", {}).get("key", ""),
                "content": self._extract_text_from_storage(
                    result.get("body", {}).get("storage", {}).get("value", "")
                ),
                "url": f"{self.base_url}{result.get('_links', {}).get('webui', '')}",
                "last_modified": result.get("version", {}).get("when", ""),
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch page {page_id}: {e}")
            return None
    
    async def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search Confluence pages using CQL full-text search.
        
        Args:
            query: Search text
            space_key: Optional space to restrict search to
            limit: Maximum results
            
        Returns:
            List of matching page dicts
        """
        if not self.live_mode:
            # Simple keyword search over demo data
            pages = self._load_demo_pages(space_key)
            query_lower = query.lower()
            return [
                p for p in pages
                if query_lower in p["title"].lower() or query_lower in p["content"].lower()
            ][:limit]
        
        try:
            cql_parts = [f'text~"{query}"']
            if space_key:
                cql_parts.append(f"space={space_key}")
            cql = " AND ".join(cql_parts)
            
            result = await self._api_request(
                "GET",
                CONFLUENCE_SEARCH_ENDPOINT,
                params={
                    "cql": cql,
                    "limit": limit,
                    "expand": "body.storage,space",
                },
            )
            
            pages = []
            for item in result.get("results", []):
                pages.append({
                    "id": f"confluence_{item['id']}",
                    "title": item.get("title", ""),
                    "space": item.get("space", {}).get("key", ""),
                    "content": self._extract_text_from_storage(
                        item.get("body", {}).get("storage", {}).get("value", "")
                    ),
                })
            
            return pages
            
        except Exception as e:
            logger.error(f"Confluence search failed: {e}")
            return []
    
    # ── Private Helpers ───────────────────────────────────
    
    def _load_demo_pages(self, space_key: Optional[str] = None) -> list[dict]:
        """Load pages from local demo seed data."""
        if self._demo_cache is None:
            if not DEMO_DATA_PATH.exists():
                logger.warning(f"Demo data not found at {DEMO_DATA_PATH}")
                return []
            
            with open(DEMO_DATA_PATH, "r", encoding="utf-8") as f:
                self._demo_cache = json.load(f)
            
            logger.info(f"Loaded {len(self._demo_cache)} demo pages from local data")
        
        pages = self._demo_cache
        
        # Filter by space if requested
        if space_key:
            pages = [p for p in pages if p.get("space", "").lower() == space_key.lower() or not space_key]
        
        return pages
    
    @staticmethod
    def _extract_text_from_storage(html_content: str) -> str:
        """
        Extract plain text from Confluence storage format (XHTML).
        
        Strips HTML tags and returns clean text for embedding.
        In production, this would use a proper HTML parser like
        BeautifulSoup. For demo purposes, a regex-based approach
        is sufficient.
        """
        import re
        
        if not html_content:
            return ""
        
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html_content)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # Decode common HTML entities
        text = (
            text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
        )
        
        return text
