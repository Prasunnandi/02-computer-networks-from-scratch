# Day 54: HTTP Cache Engine & ETag Validator Lab Tutorial

Welcome to Day 54 of Computer Networks from Scratch. Today, you will build an RFC 9111 compliant HTTP caching engine, implementing Freshness Lifetime calculations, FNV-1a cryptographic ETag hashing, and `304 Not Modified` conditional revalidation.

---

## 1. What Are We Building & Why Does It Matter?

Without caching, global internet backbones and web servers would collapse under load. HTTP caching operates on two primary mechanisms:
1. **Freshness Lifetime**: Assets with a valid `max-age` are served immediately from local browser/CDN storage with **zero network latency**.
2. **Conditional Revalidation**: When an asset becomes stale ($Age \ge MaxAge$), the client sends an `If-None-Match: "<etag>"` request. If the server's asset has not changed, it replies with `304 Not Modified` and zero payload bytes, refreshing the cache lifetime without wasting bandwidth.

In this lab, you simulate this complete lifecycle in pure Python.

---

## 2. Python Concepts for Beginners

### A. 64-Bit Bitwise Hash Functions
Implement fast non-cryptographic checksums using bitwise operations (`^`, `*`, `& 0xFFFFFFFFFFFFFFFF`):
```python
hash_val = 14695981039346656037
for b in data.encode("utf-8"):
    hash_val ^= b
    hash_val = (hash_val * 1099511628211) & 0xFFFFFFFFFFFFFFFF
etag = f'"{hash_val:016x}"'
```

### B. Age vs Max-Age Arithmetic
Calculate elapsed age based on apparent age and resident time:
```python
apparent_age = max(0.0, response_time - date_header_time)
resident_time = current_time - response_time
current_age = apparent_age + resident_time

if current_age < max_age:
    # Asset is Fresh!
```

### C. Formatting Hex Hashes
Format integers into fixed-width 16-character hex strings:
```python
formatted_hash = f"{hash_val:016x}"
```

---

## 3. Step-by-Step Code Walkthrough

1. **`CachedResponse` Dataclass**: Models the cached entity: `uri`, `status_code`, `headers`, `body`, `date_timestamp`, `max_age_sec`, `etag`.
2. **`HTTPCacheEngine` Class**:
   - `generate_etag()`: Computes an FNV-1a 64-bit hash string surrounded by double quotes.
   - `store_response()`: Inserts a new response entity with `Cache-Control: max-age`.
   - `get()`:
     - Calculates `current_age`.
     - If fresh, returns `CACHE_HIT` (200 OK) without contacting origin.
     - If stale, checks `origin_server_content`. If ETags match, returns `REVALIDATED_304` and refreshes timestamps.
     - If origin updated, replaces cache and returns 200 OK.
3. **`main()` Test Suite**: Validates fresh cache hits, stale 304 revalidations, and origin update cache refreshes.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-54/http_cache_engine_etag_validator.py
```

Expected output:
```text
=== Day 54: HTTP Cache Engine & ETag Revalidation Validator ===
[*] Stored response: ETag="b9c5123d93708a0d", Max-Age=60s
[*] Test 1 Passed: Fresh request resolved from memory: CACHE_HIT (Fresh: Age=20.0s, MaxAge=60s)
[*] Test 2 Passed: Stale request revalidated with 304 Not Modified: REVALIDATED_304 (Unmodified on origin; TTL refreshed)
[*] Test 3 Passed: Origin update correctly replaced stale cache entity: STALE_UPDATED_200 (Origin modified; cache updated)
All HTTP Cache Engine assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **Quoting in ETags**: RFC 9110 specifies that ETags are opaque quoted strings (e.g. `"33a64df5"`). Always include surrounding quotes when comparing headers.
- **Negative Age Values**: Network clock drift can cause $T_{\text{ResponseReceived}} < T_{\text{Date}}$. Always wrap apparent age calculations in `max(0.0, ...)`.

---

## 6. Beginner Exercises & Challenges

1. **Implement `stale-while-revalidate`**: Allow the cache to serve stale content immediately while triggering an asynchronous origin fetch in the background.
2. **Support Weak ETags**: Implement weak ETag comparison (`W/"hash"`) that ignores semantic whitespace differences.
3. **Add `no-store` Support**: Modify `store_response()` to refuse caching any response containing `Cache-Control: no-store`.
