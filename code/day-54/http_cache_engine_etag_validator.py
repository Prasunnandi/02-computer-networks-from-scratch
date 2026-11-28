"""
Day 54: HTTP Cache Engine & ETag Revalidation Validator
100% pure Python standard library implementation of RFC 9111 HTTP caching algorithms:
Freshness Lifetime, Current Age, ETag FNV-1a hashing, and 304 Not Modified conditional logic.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, Optional, Tuple


@dataclass
class CachedResponse:
    uri: str
    status_code: int
    headers: Dict[str, str]
    body: str
    date_timestamp: float         # Origin Date header
    response_received_time: float # When client received response
    max_age_sec: int              # Parsed from Cache-Control: max-age
    etag: str                     # Entity Tag


class HTTPCacheEngine:
    """Evaluates HTTP freshness lifetimes and executes conditional revalidation."""

    def __init__(self):
        # Cache storage: uri -> CachedResponse
        self.cache: Dict[str, CachedResponse] = {}

    @staticmethod
    def generate_etag(data: str) -> str:
        """Generates 64-bit FNV-1a hash formatted as strong ETag."""
        hash_val = 14695981039346656037
        for b in data.encode("utf-8"):
            hash_val ^= b
            hash_val = (hash_val * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        return f'"{hash_val:016x}"'

    def store_response(self, uri: str, body: str, max_age: int, now: float) -> CachedResponse:
        etag = self.generate_etag(body)
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": f"public, max-age={max_age}",
            "ETag": etag
        }
        cached = CachedResponse(
            uri=uri,
            status_code=200,
            headers=headers,
            body=body,
            date_timestamp=now,
            response_received_time=now,
            max_age_sec=max_age,
            etag=etag
        )
        self.cache[uri] = cached
        return cached

    def get(self, uri: str, current_time: float, origin_server_content: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Retrieves asset. Returns (status_code, body, cache_status).
        Cache status is one of: CACHE_HIT, REVALIDATED_304, CACHE_MISS.
        """
        if uri not in self.cache:
            return 200, origin_server_content or "", "CACHE_MISS"

        entry = self.cache[uri]

        # Calculate RFC 9111 Age:
        apparent_age = max(0.0, entry.response_received_time - entry.date_timestamp)
        resident_time = current_time - entry.response_received_time
        current_age = apparent_age + resident_time

        # 1. Freshness Check: If Age < Max-Age -> Instant CACHE_HIT (0 network calls)
        if current_age < entry.max_age_sec:
            return 200, entry.body, f"CACHE_HIT (Fresh: Age={current_age:.1f}s, MaxAge={entry.max_age_sec}s)"

        # 2. Asset is STALE: Execute Conditional Revalidation (If-None-Match)
        if origin_server_content is not None:
            origin_etag = self.generate_etag(origin_server_content)
            if origin_etag == entry.etag:
                # 304 Not Modified: Refresh entry timestamp
                entry.date_timestamp = current_time
                entry.response_received_time = current_time
                return 304, entry.body, "REVALIDATED_304 (Unmodified on origin; TTL refreshed)"
            else:
                # Content updated on origin: Update cache with new entity
                self.store_response(uri, origin_server_content, entry.max_age_sec, current_time)
                return 200, origin_server_content, "STALE_UPDATED_200 (Origin modified; cache updated)"

        return 200, entry.body, "STALE_SERVED (Fallback)"


def main():
    print("=== Day 54: HTTP Cache Engine & ETag Revalidation Validator ===")

    engine = HTTPCacheEngine()
    now = 1000.0
    uri = "/api/v1/config.json"
    initial_content = '{"theme": "dark", "version": "1.0.0"}'

    # Store initial response with max-age=60s
    engine.store_response(uri, initial_content, max_age=60, now=now)
    etag1 = engine.cache[uri].etag
    print(f"[*] Stored response: ETag={etag1}, Max-Age=60s")

    # Test 1: Fresh Request at t+20s -> Instant CACHE_HIT
    status, body, msg = engine.get(uri, current_time=now + 20.0)
    assert status == 200
    assert body == initial_content
    assert "CACHE_HIT" in msg
    print(f"[*] Test 1 Passed: Fresh request resolved from memory: {msg}")

    # Test 2: Stale Request at t+75s (Age > 60s), Origin Unmodified -> 304 Not Modified
    status, body, msg = engine.get(uri, current_time=now + 75.0, origin_server_content=initial_content)
    assert status == 304
    assert body == initial_content
    assert "REVALIDATED_304" in msg
    print(f"[*] Test 2 Passed: Stale request revalidated with 304 Not Modified: {msg}")

    # Test 3: Asset modified on origin -> 200 OK with new content & ETag
    updated_content = '{"theme": "light", "version": "1.0.1"}'
    status, body, msg = engine.get(uri, current_time=now + 150.0, origin_server_content=updated_content)
    assert status == 200
    assert body == updated_content
    assert "STALE_UPDATED_200" in msg
    assert engine.cache[uri].etag != etag1
    print(f"[*] Test 3 Passed: Origin update correctly replaced stale cache entity: {msg}")

    print("All HTTP Cache Engine assertions passed successfully!")


if __name__ == "__main__":
    main()
