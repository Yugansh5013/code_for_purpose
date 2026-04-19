"""
OmniData — Groq API Key Rotation Pool

Cycles through multiple Groq API keys per-request to avoid
hitting free-tier rate limits (~30 requests/minute per key).
Thread-safe via itertools.cycle.

complete_with_retry() catches 429 rate-limit errors and
automatically rotates to the next key in the pool before retrying.
"""

import itertools
import logging
from typing import Any

from groq import Groq, RateLimitError

logger = logging.getLogger(__name__)


class GroqKeyPool:
    """
    Round-robin pool of Groq API keys with automatic 429 retry rotation.

    Usage:
        pool = GroqKeyPool(["gsk_key1", "gsk_key2", "gsk_key3"])

        # Simple (no retry):
        client = pool.get_client()
        response = client.chat.completions.create(...)

        # With automatic key rotation on 429:
        response = pool.complete_with_retry(model=..., messages=..., ...)
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

    def complete_with_retry(self, **kwargs: Any) -> Any:
        """
        Call chat.completions.create() with automatic key rotation on 429.

        Tries every key in the pool before giving up.
        All kwargs are forwarded directly to client.chat.completions.create().

        Raises:
            RateLimitError: if ALL keys are exhausted and rate limited.
            Any other exception from the last attempt.
        """
        last_error = None
        num_keys = len(self._keys)

        for attempt in range(num_keys):
            client = self.get_client()
            try:
                response = client.chat.completions.create(**kwargs)
                if attempt > 0:
                    logger.info(f"Groq call succeeded on key rotation attempt {attempt + 1}/{num_keys}")
                return response
            except RateLimitError as e:
                last_error = e
                logger.warning(
                    f"Groq 429 on attempt {attempt + 1}/{num_keys} — rotating to next key. "
                    f"Key ends: ...{self._keys[(attempt) % num_keys][-6:]}"
                )
            except Exception as e:
                # Non-rate-limit errors (bad request, auth failure, etc.) — don't rotate, raise immediately
                raise e

        logger.error(f"All {num_keys} Groq keys hit rate limit. Last error: {last_error}")
        raise last_error

    @property
    def key_count(self) -> int:
        return len(self._keys)
