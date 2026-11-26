# Day 33: Core DNS Records Wire Format Parser

## 1. What Are We Building & Why Does It Matter?
In DNS, resource records (RRs) share a universal envelope format:
- **Name**: Domain name (variable length).
- **Type (16 bits)**: e.g. A (1), AAAA (28), MX (15), TXT (16), SOA (6).
- **Class (16 bits)**: Almost universally `1` for Internet (`IN`).
- **TTL (32 bits)**: Time-To-Live in seconds.
- **RDLENGTH (16 bits)**: Byte length of the record-specific payload (`RDATA`).
- **RDATA (variable)**: The binary payload whose internal structure depends entirely on `Type`.

In this lab, we build an RFC-compliant **DNS Record Wire Parser** in pure Python that decodes binary RDATA into structured Python objects for IPv4 (A), IPv6 (AAAA), Mail Exchangers (MX), Text (TXT), and Zone Authority (SOA).

---

## 2. Python Concepts for Beginners

### A. Python's `socket.inet_ntoa` and `inet_ntop`
Translating between 4 raw bytes and human-readable IPv4 strings (`"93.184.216.34"`) is handled by `socket.inet_ntoa()` (network to ASCII) and `socket.inet_aton()` (ASCII to network). For 16-byte IPv6 addresses, we use `socket.inet_ntop(socket.AF_INET6, raw_bytes)`.

### B. Fixed-Size Struct Unpacking (`struct.unpack`)
When parsing multi-byte integers from binary data:
- `!H` reads a 16-bit unsigned integer (2 bytes).
- `!I` reads a 32-bit unsigned integer (4 bytes).
- `!IIIII` reads five consecutive 32-bit integers (20 bytes total), perfect for SOA records!

### C. String Encoding and Decoding
Binary network data consists of raw bytes (`bytes`). We turn raw ASCII/UTF-8 bytes into Python strings with `.decode('utf-8')`:
```python
raw_bytes = b"hello"
text = raw_bytes.decode('utf-8')  # String: "hello"
```

---

## 3. Step-by-Step Code Walkthrough

1. **`parse_a_record()`**: Validates that input is exactly 4 bytes and converts to dotted-quad notation via `socket.inet_ntoa()`.
2. **`parse_aaaa_record()`**: Validates 16-byte length and parses IPv6 address via `socket.inet_ntop()`.
3. **`parse_mx_record()`**: Unpacks the 2-byte preference priority (`!H`) followed by the mail server domain name.
4. **`parse_txt_record()`**: Loops through length-prefixed strings (RFC 1035 allows multiple chunks up to 255 bytes each) and concatenates them.
5. **`parse_soa_record()`**: Reads the 20-byte timer trailer: Zone Serial Number, Refresh, Retry, Expire, and Minimum (Negative Caching) TTL.
6. **`main()` Function**: Executes unit tests against synthetic binary wire payloads.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-33/dns_record_wire_parser.py
```

Expected output:
```text
====================================================
DAY 33: CORE DNS RECORDS WIRE FORMAT PARSER
====================================================
  [PASS] A Record Wire -> IP: 93.184.216.34
  [PASS] AAAA Record Wire -> IPv6: 2606:2800:220:1:248:1893:25c8:1946
  [PASS] MX Record Wire -> Priority 10, Host: mail.example.com
  [PASS] TXT Record Wire -> Text: v=spf1 include:_spf.example.com ~all
  [PASS] SOA Record Wire -> Serial: 2026112601, Negative TTL: 300s

[VERIFIED] Core DNS Record Wire Parser passed all tests with 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting

- **`ValueError: A record RDATA must be exactly 4 bytes`**: If passing more or fewer than 4 bytes to `parse_a_record()`, check that `rdlength` from the record header was parsed properly.
- **`struct.error: unpack requires a buffer of 20 bytes`**: Occurs if `raw_soa_timers` has fewer than 20 bytes.
- **Handling Non-ASCII in TXT**: Sometimes SPF or verification TXT records contain foreign characters. Using `.decode('utf-8', errors='replace')` prevents crashes on invalid byte sequences.

---

## 6. Beginner Exercises & Challenges

1. **CNAME Parser**: Implement `parse_cname_record(rdata_bytes)` to extract the canonical alias domain name.
2. **Reverse PTR Lookup**: Build an encoder that takes an IPv4 address like `192.0.2.1` and converts it to its in-addr.arpa reverse name `1.2.0.192.in-addr.arpa`.
3. **Record Envelope Formatter**: Write a function that takes a complete DNS record dictionary and formats it as a standard BIND zone file line.\n