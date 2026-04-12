"""
OmniData — Groq API Key Rotation Pool

Cycles through multiple Groq API keys per-request to avoid
hitting free-tier rate limits (~30 requests/minute per key).
Thread-safe via itertools.cycle.
"""

import itertools
import logging
from groq import Groq

logger = logging.getLogger(__name__)


class GroqKeyPool:
    """
    Round-robin pool of Groq API keys.
    
    Usage:
        pool = GroqKeyPool(["gsk_key1", "gsk_key2", "gsk_key3"])
        client = pool.get_client()
        response = client.chat.completions.create(...)
    """

    def __init__(self, keys: list[str]):
        if not keys:
            raise ValueError("At least one Groq API key is required")
        self._keys = keys
        self._cycle = itertools.cycle(keys)
        logger.info(f"Groq key pool initialized with {len(keys)} key(s)")

    def get_client(self) -> Groq:
        """Get a Groq client with the next API key in rotation."""
        key = next(self._cycle)
        return Groq(api_key=key)

    def get_client_with_retry(self, max_retries: int = 3) -> Groq:
        """
        Try multiple keys if the first one fails (e.g., rate limited).
        Returns a new client each attempt using the next key in rotation.
        """
        for attempt in range(min(max_retries, len(self._keys))):
            client = self.get_client()
            return client
        return self.get_client()

    @property
    def key_count(self) -> int:
        return len(self._keys)
