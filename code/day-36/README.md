# Day 36: DNS Caching Engine & Negative TTL Simulation (RFC 2308)

## 1. What Are We Building & Why Does It Matter?
DNS caching is what prevents the global Internet from collapsing under query volume. Without caches, every single web request, email check, and API ping on Earth would slam the 13 Root Server clusters.
- **Positive Caching**: When a resolver receives a valid answer (e.g. `example.com A 93.184.216.34`), it stores it for the duration specified by the server's `TTL` (Time-To-Live). As seconds tick by, the remaining TTL degrades.
- **Negative Caching (RFC 2308)**: When a domain does *not* exist (`NXDOMAIN`), resolvers must also cache that failure! Otherwise, broken software or bots querying non-existent domains would flood authoritative servers in an accidental Denial of Service. The negative TTL is defined by the minimum timer in the zone's `SOA` record.

In this lab, we build a **DNS Caching Engine** in pure Python that models positive TTL countdowns, RFC 2308 negative caching, TTL capping, and automatic eviction.

---

## 2. Python Concepts for Beginners

### A. Synthetic Timestamps for Deterministic Testing
Instead of waiting real seconds with `time.sleep()`, we pass synthetic timestamps (`mock_time=1000.0`, `current_time=1050.0`) to test TTL expiration deterministically in milliseconds without sleeping!

### B. Python Class Properties (`@property`)
The `@property` decorator allows a method to be accessed like a normal variable attribute, computing its value on-the-fly:
```python
@property
def is_expired(self) -> bool:
    return self.remaining_ttl <= 0
```

### C. Case-Insensitive Cache Keys
In DNS, `EXAMPLE.COM` and `example.com` are identical. In Python, string keys in dictionaries are case-sensitive by default. We normalize keys with `.lower()` and `.upper()`:
```python
key = (qname.lower(), qtype.upper())
```

---

## 3. Step-by-Step Code Walkthrough

1. **`CacheEntry` Dataclass**: Stores domain name, record type, response status (`NOERROR` vs `NXDOMAIN`), payload data, initial TTL, and insertion timestamp.
2. **`store_positive()`**: Inserts successful record sets and computes remaining lifetime.
3. **`store_negative()`**: Implements RFC 2308 by caching NXDOMAIN results using the zone's SOA minimum TTL (capped to 3 hours).
4. **`lookup()`**: Retrieves an entry, computes elapsed time, and if expired, immediately deletes it from memory and returns `None`.
5. **`main()` Function**: Simulates synthetic queries at `t=0`, `t=50`, `t=100`, and `t=301`, verifying positive hits, negative hits, and expiration eviction.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-36/dns_cache_ttl_engine.py
```

Expected output:
```text
====================================================
DAY 36: DNS CACHING ENGINE & NEGATIVE TTL (RFC 2308)
====================================================
  [PASS] Positive Cache Hit: Status=NOERROR, Data=['93.184.216.34'], TTL remaining=250s
  [PASS] Negative Cache Hit: Status=NXDOMAIN, Data=[], TTL remaining=500s
  [PASS] Cache entry cleanly evicted after TTL expiration.
  Stats: Hits=2, Misses=1, Evictions=1

[VERIFIED] DNS Cache Engine passed all tests with 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting

- **`KeyError` on Deletion**: When deleting expired items with `del self.cache[key]`, ensure the key exists or use `self.cache.pop(key, None)`.
- **Negative Remaining TTL**: If elapsed time exceeds TTL, `ttl - elapsed` produces negative numbers. We guard against this with `max(0, effective_ttl - elapsed)`.
- **Memory Leaks**: In real servers with millions of domains, passive eviction (only deleting on lookup) can leak RAM. Production caches run background purge sweeps or use LRU (Least Recently Used) eviction.

---
### Additional Python Beginner Foundations
- **Negative Caching Architecture (RFC 2308)**:
  Why cache errors? If an application repeatedly requests a misspelled domain name, every query would hit the root and TLD servers. Caching `NXDOMAIN` with the zone's SOA minimum TTL protects root infrastructure.
- **Deterministic Time Modeling in Tests**:
  By passing a synthetic `mock_time` parameter to cache methods, unit tests can advance virtual time by 50, 200, or 10,000 seconds instantly without using `time.sleep()`, keeping test suites running at blazing speed!

### Extended Debugging Guide
1. **Clock Drift Issues**: If system time shifts backward (e.g. NTP sync), `current_time - insert_timestamp` can become negative. Guard against clock skew by capping elapsed time at zero.
2. **Negative TTL Capping**: RFC 2308 recommends capping negative TTLs to at most 3 hours (10,800 seconds) regardless of how high the authoritative SOA minimum timer is configured.

## 6. Beginner Exercises & Challenges

1. **Max-Cache Capacity Limit**: Add a `max_entries = 1000` limit. When full, evict the entry with the smallest remaining TTL.
2. **Cache Purge Method**: Implement `flush_zone("example.com")` that removes all cached records belonging to that domain and its subdomains.
3. **Pre-fetching**: If an entry has less than 10% TTL remaining and receives a lookup, flag it for background refresh.
