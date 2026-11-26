# Day 35: Recursive Resolver Simulator with Bailiwick Security Filter

## 1. What Are We Building & Why Does It Matter?
In DNS architecture, there are two distinct resolution modes:
1. **Recursive Resolution**: The client (like your laptop or smartphone) asks a recursive resolver (like `8.8.8.8` or `1.1.1.1`): *"Give me the answer or tell me it doesn't exist."* The client does not do the legwork.
2. **Iterative Resolution**: The recursive resolver does the legwork by querying Root -> TLD -> Authoritative servers step by step.

However, resolvers face a dangerous threat: **Cache Poisoning**. If a malicious authoritative server for `attacker.com` responds with an answer for `bank.com`, an unhardened resolver might accept it!
The **Bailiwick Rule (RFC 2181)** prevents this: a nameserver is only permitted to provide authoritative answers for domain names located strictly within its own sub-tree.

In this lab, we build a **Recursive Resolver Engine** in pure Python equipped with a Bailiwick validation filter and local memory cache.

---

## 2. Python Concepts for Beginners

### A. Tuple Keys in Dictionaries
In Python, dictionary keys must be immutable. A `tuple` like `("example.com", "A")` can be used as a dictionary key, creating multi-dimensional lookups for caches:
```python
cache = {}
cache[("example.com", "A")] = ["93.184.216.34"]
result = cache.get(("example.com", "A"))
```

### B. String Domain Suffix Checking (`str.endswith`)
To verify whether a domain name belongs to a zone:
```python
domain = "api.cloudflare.net"
zone = "cloudflare.net"
is_valid = domain == zone or domain.endswith("." + zone)  # True
```

### C. List Comprehensions for Filtering
We filter out invalid records in a single concise line:
```python
valid_records = [r for r in records if is_in_bailiwick(r.name, zone)]
```

---

## 3. Step-by-Step Code Walkthrough

1. **`MockNameserver`**: Simulates a remote nameserver holding local records or delegation pointers (`subzone -> (ns_name, ns_ip)`).
2. **`is_in_bailiwick(record_name, server_zone)`**: Enforces the security boundary. If `server_zone` is `cloudflare.net`, records for `google.com` return `False`.
3. **`resolve(qname, qtype)`**:
   - Checks memory cache first.
   - Iterates through nameservers starting from the Root IP.
   - Upon receiving an answer, filters every record through `is_in_bailiwick()`.
   - Stores valid records into cache and returns to client.
4. **`main()` Function**: Simulates an attack where `cloudflare.net` attempts to inject a poison record for `google.com`, verifying that the Bailiwick filter drops the poison.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-35/recursive_resolver_sim.py
```

Expected output:
```text
====================================================
DAY 35: RECURSIVE RESOLVER & BAILIWICK FILTER
====================================================
[RECURSION START] Client queried: api.cloudflare.net. A
  Hop 1: Server . (198.41.0.4) referred to a.gtld-servers.net. (192.5.6.30)
  Hop 2: Server .net. (192.5.6.30) referred to ns1.cloudflare.net. (172.64.32.1)
  [SECURITY ALERT] Discarded out-of-bailiwick record: google.com. from zone cloudflare.net.!
  [PASS] Resolved legitimately: api.cloudflare.net. -> 104.16.123.96
[CACHE HIT] Returning cached answer for api.cloudflare.net.
  [PASS] Verified second query served from local cache.

[VERIFIED] Recursive Resolver with Bailiwick Filter passed all tests!
```

---

## 5. Common Python Errors & Troubleshooting

- **`RuntimeError: Recursion limit exceeded`**: Occurs if a delegation cycle exists (e.g. Server A delegates to Server B, which delegates to Server A). The `hops < 10` counter prevents infinite hangs.
- **Accidental Root Matching**: If comparing against the root zone `.` with `.endswith()`, ensure special handling for empty string zone roots.
- **Cache Stale Data**: In production, records must expire after their TTL seconds elapse.

---

## 6. Beginner Exercises & Challenges

1. **Add TTL Expiration**: Store a timestamp with each cache entry and invalidate entries when `time.time() - cached_time > record.ttl`.
2. **CNAME Chaser**: Modify `resolve()` so that if it receives a `CNAME` answer, it restarts recursion to resolve the canonical target.
3. **Round-Robin DNS**: If a domain has multiple `A` records, rotate the list on each query to simulate round-robin load balancing.\n