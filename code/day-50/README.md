# Day 50: Milestone 2 - Autonomous Recursive DNS Resolver Lab Tutorial

Welcome to Day 50 of Computer Networks from Scratch. Today is a major milestone: you will build a complete, autonomous recursive DNS resolver from scratch in pure Python standard library.

---

## 1. What Are We Building & Why Does It Matter?

The Domain Name System (DNS, RFC 1035) is the phonebook of the global internet. When a user requests `example.com`, their local computer contacts a recursive resolver. If the record is not in cache, the resolver performs iterative tree traversal:
1. Queries an ICANN **Root Nameserver** (e.g. `198.41.0.4` `a.root-servers.net`).
2. Follows the referral delegation to the **Top-Level Domain (TLD) Nameserver** (e.g. `a.gtld-servers.net` for `.com`).
3. Follows the referral to the domain's **Authoritative Nameserver** (e.g. `ns1.example.com`).
4. Extracts the final IPv4 `A` record and stores it in cache governed by the Time-To-Live (TTL).

In this milestone project, you build:
- Binary wire encoder for RFC 1035 questions.
- Binary wire decoder handling compression pointers (`0xC0`), answers, authorities, and additionals.
- Circular compression loop defense.
- Iterative multi-hop resolver and TTL memory cache.

---

## 2. Python Concepts for Beginners

### A. Nonlocal Variables in Nested Functions (`nonlocal`)
When parsing repeated lists of Resource Records (Answers, Authorities, Additionals), a nested function can update the outer byte offset:
```python
offset = 12
def parse_records():
    nonlocal offset
    offset += 10
```

### B. RFC 1035 Pointer Decompression Bitmasking
In DNS, if the first byte of a label starts with binary `11` (`0xC0`), it indicates a 14-bit backward pointer:
```python
if (first_byte & 0xC0) == 0xC0:
    pointer_offset = struct.unpack("!H", raw[idx:idx+2])[0] & 0x3FFF
```

### C. Loop Detection with Hash Sets
Malicious or malformed DNS packets can create infinite loops where pointer A points to pointer B which points back to pointer A. We track `visited_pointers` to abort safely:
```python
if pointer in visited_pointers:
    raise ValueError("Circular compression pointer loop detected!")
visited_pointers.add(pointer)
```

---

## 3. Step-by-Step Code Walkthrough

1. **`DNSRecord` & `DNSResponse` Dataclasses**: Represent individual resource records and full DNS response packets.
2. **`DNSWireCodec` Class**:
   - `encode_query()`: Formats standard 12-byte header with `RD=1` and length-prefixed domain labels.
   - `decode_name()`: Recursively follows `0xC0` compression pointers while tracking byte offsets and cycle prevention.
   - `decode_response()`: Parses Answers, Authorities, and Additionals (glue records).
3. **`RecursiveDNSResolver` Class**:
   - `resolve()`: First checks local cache. If missing or expired, begins at Root Hints, follows TLD referrals, parses glue records, and queries authoritative servers until finding the `A` record.
4. **`main()` Test Suite**:
   - Test 1: Verifies query packet wire encoding.
   - Test 2: Verifies compression pointer decompression and record parsing.
   - Test 3: Verifies detection of malicious circular compression loops.
   - Test 4: Verifies multi-hop iterative resolution across simulated Root, TLD, and Authoritative nameservers.
   - Test 5: Verifies in-memory TTL caching.

---

## 4. How to Run & Expected Output

Run the milestone script with Python 3:
```bash
python code/day-50/raw_socket_dns_resolver_milestone.py
```

Expected output:
```text
=== Day 50: Milestone 2 - Autonomous Recursive DNS Resolver from Scratch ===
[*] Test 1 Passed: Encoded 29-byte DNS query for 'example.com'
[*] Test 2 Passed: Decoded compression pointer and parsed Answer IP: 93.184.216.34
[*] Test 3 Passed: Successfully terminated circular compression loop attack
[*] Test 4 Passed: Iteratively resolved 'example.com' from Root -> TLD -> Auth: 93.184.216.34
[*] Test 5 Passed: Resolved 'example.com' directly from memory cache
Milestone 2 Raw DNS Resolver assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`ValueError: Circular compression pointer loop detected`**: If this occurs on valid packets, ensure you do not add standard length offsets to the pointer set. Only add compression pointer target offsets.
- **`struct.error: unpack requires a buffer of 10 bytes`**: Occurs if the packet was truncated mid-record. Ensure network sockets read the complete datagram.

---

## 6. Beginner Exercises & Challenges

1. **Implement AAAA Record Resolution**: Extend the decoder to support IPv6 `AAAA` records (type 28) returning colon-separated hex strings.
2. **Add Negative Caching (SOA Records)**: When a domain does not exist (`NXDOMAIN`, RCODE=3), resolvers cache the Authority section's SOA record TTL to avoid repeated queries.
3. **Live Socket Mode**: Add a command-line flag `--live` that transmits queries over real UDP sockets (`socket.AF_INET, socket.SOCK_DGRAM`) to public resolvers like `1.1.1.1` or `8.8.8.8`.
