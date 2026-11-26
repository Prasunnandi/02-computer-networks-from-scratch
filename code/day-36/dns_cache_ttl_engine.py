#!/usr/bin/env python3
"""
Day 36 Lab: DNS Caching Engine & Negative TTL Simulation (RFC 2308)
Simulates positive TTL degradation, negative caching of NXDOMAIN/NODATA
responses using SOA minimum TTL timers, and TTL capping limits.
Uses Python standard library only.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class CacheEntry:
    key: Tuple[str, str]  # (qname, qtype)
    status: str           # 'NOERROR' or 'NXDOMAIN'
    data: List[str]       # list of values or [] for NXDOMAIN
    original_ttl: int
    insert_timestamp: float
    max_ttl_cap: int = 86400  # Cap maximum positive TTL to 1 day
    negative_ttl_cap: int = 10800  # Cap negative TTL to 3 hours (RFC 2308)

    @property
    def remaining_ttl(self) -> int:
        elapsed = int(time.time() - self.insert_timestamp)
        effective_ttl = min(self.original_ttl, self.negative_ttl_cap if self.status == 'NXDOMAIN' else self.max_ttl_cap)
        return max(0, effective_ttl - elapsed)

    @property
    def is_expired(self) -> bool:
        return self.remaining_ttl <= 0


class DNSCacheEngine:
    def __init__(self, default_negative_ttl: int = 300):
        self.cache: Dict[Tuple[str, str], CacheEntry] = {}
        self.default_negative_ttl = default_negative_ttl
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def store_positive(self, qname: str, qtype: str, records: List[str], ttl: int, mock_time: Optional[float] = None):
        """Stores successful query response with positive TTL."""
        ts = mock_time if mock_time is not None else time.time()
        key = (qname.lower(), qtype.upper())
        self.cache[key] = CacheEntry(
            key=key,
            status="NOERROR",
            data=records,
            original_ttl=ttl,
            insert_timestamp=ts
        )

    def store_negative(self, qname: str, qtype: str, soa_min_ttl: int, mock_time: Optional[float] = None):
        """Stores negative response (NXDOMAIN) per RFC 2308."""
        ts = mock_time if mock_time is not None else time.time()
        key = (qname.lower(), qtype.upper())
        effective_neg_ttl = min(soa_min_ttl, 10800)  # RFC 2308 recommended cap
        self.cache[key] = CacheEntry(
            key=key,
            status="NXDOMAIN",
            data=[],
            original_ttl=effective_neg_ttl,
            insert_timestamp=ts
        )

    def lookup(self, qname: str, qtype: str, current_time: Optional[float] = None) -> Optional[Tuple[str, List[str], int]]:
        """Looks up cached entry. Returns (status, data, remaining_ttl) or None if expired/miss."""
        now = current_time if current_time is not None else time.time()
        key = (qname.lower(), qtype.upper())
        entry = self.cache.get(key)

        if not entry:
            self.stats["misses"] += 1
            return None

        elapsed = int(now - entry.insert_timestamp)
        effective_limit = entry.negative_ttl_cap if entry.status == 'NXDOMAIN' else entry.max_ttl_cap
        remaining = min(entry.original_ttl, effective_limit) - elapsed

        if remaining <= 0:
            del self.cache[key]
            self.stats["evictions"] += 1
            self.stats["misses"] += 1
            return None

        self.stats["hits"] += 1
        return entry.status, entry.data, remaining


def main():
    print("====================================================")
    print("DAY 36: DNS CACHING ENGINE & NEGATIVE TTL (RFC 2308)")
    print("====================================================")

    engine = DNSCacheEngine()
    t0 = 1000.0  # Synthetic epoch

    # 1. Positive caching
    engine.store_positive("example.com", "A", ["93.184.216.34"], ttl=300, mock_time=t0)
    res = engine.lookup("example.com", "A", current_time=t0 + 50)
    assert res is not None
    status, data, rem = res
    assert status == "NOERROR"
    assert data == ["93.184.216.34"]
    assert rem == 250, f"Expected remaining TTL 250, got {rem}"
    print(f"  [PASS] Positive Cache Hit: Status={status}, Data={data}, TTL remaining={rem}s")

    # 2. Negative caching (NXDOMAIN)
    engine.store_negative("ghost.example.com", "A", soa_min_ttl=600, mock_time=t0)
    neg_res = engine.lookup("ghost.example.com", "A", current_time=t0 + 100)
    assert neg_res is not None
    neg_status, neg_data, neg_rem = neg_res
    assert neg_status == "NXDOMAIN"
    assert neg_rem == 500
    print(f"  [PASS] Negative Cache Hit: Status={neg_status}, Data={neg_data}, TTL remaining={neg_rem}s")

    # 3. Expiration after TTL
    expired_res = engine.lookup("example.com", "A", current_time=t0 + 301)
    assert expired_res is None
    print("  [PASS] Cache entry cleanly evicted after TTL expiration.")

    # 4. Check statistics
    print(f"  Stats: Hits={engine.stats['hits']}, Misses={engine.stats['misses']}, Evictions={engine.stats['evictions']}")
    assert engine.stats["hits"] == 2
    assert engine.stats["evictions"] == 1

    print("\n[VERIFIED] DNS Cache Engine passed all tests with 100% fidelity!")


if __name__ == "__main__":
    main()
