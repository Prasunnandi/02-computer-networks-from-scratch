# Day 34: Modern DNS Records Parser (SRV, CAA, HTTPS/SVCB)

## 1. What Are We Building & Why Does It Matter?
Modern cloud infrastructure and web browsers rely on specialized DNS record types beyond simple IP address mappings:
1. **SRV Records (RFC 2782)**: Define service discovery endpoints. Instead of hardcoding ports (e.g. SIP, LDAP, Minecraft), clients discover both the hostname and TCP/UDP port, complete with priority and weighted load balancing.
2. **CAA Records (RFC 8659)**: Protect domains from fraudulent SSL certificates by declaring which Certificate Authorities (e.g. Let's Encrypt, DigiCert) are allowed to issue certificates.
3. **HTTPS / SVCB Records (RFC 9460)**: Revolutionized the web in 2023. Enables browsers to negotiate HTTP/3 (QUIC) and Encrypted Client Hello (ECH) directly in the initial DNS lookup, eliminating extra HTTP redirects.

In this lab, we build a **Modern DNS Records Parser** in pure Python that decodes binary wire formats for SRV, CAA, and HTTPS/SVCB.

---

## 2. Python Concepts for Beginners

### A. Nested Struct Formats
When parsing binary formats with variable fields:
- We parse fixed-length headers with `struct.unpack("!HHH", data[:6])` (Priority, Weight, Port = 6 bytes).
- We slice the remaining bytes `data[6:]` to parse variable-length string labels.

### B. Length-Prefixed Strings in Binary Protocols
Unlike C strings which end in a null byte (`\0`), DNS protocols often store string length as the first byte:
```python
length = data[0]                     # Number of characters
text = data[1:1 + length].decode()   # Sliced text
```

### C. Dictionaries for Key-Value Parameters
In HTTPS/SVCB records, parameters arrive as a sequence of `(Key, Length, Value)` tuples. Storing these in a Python dictionary `Dict[int, bytes]` allows easy lookup by parameter ID (e.g. Key 1 = ALPN, Key 3 = Port).

---

## 3. Step-by-Step Code Walkthrough

1. **`parse_srv()`**: Unpacks Priority (16 bits), Weight (16 bits), Port (16 bits), and parses the target domain name.
2. **`parse_caa()`**: Reads the 1-byte Flags bitfield (Critical flag), 1-byte Tag length, ASCII tag string (`issue`, `issuewild`, `iodef`), and UTF-8 CA value.
3. **`parse_https_svcb()`**: Reads Priority (0 for alias mode, >0 for service mode), decodes the target name, and loops through arbitrary SvcParam keys (ALPN, Port, ECH).
4. **`main()` Function**: Runs unit tests verifying parsing of simulated SRV, CAA, and HTTPS records against RFC specifications.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-34/modern_records_parser.py
```

Expected output:
```text
====================================================
DAY 34: MODERN DNS RECORDS PARSER (SRV, CAA, HTTPS)
====================================================
  [PASS] SRV Record: Target=sipserver.example.com:5060 (Priority=10, Weight=60)
  [PASS] CAA Record: Tag='issue', Value='letsencrypt.org' (Flags=0)
  [PASS] HTTPS Record: Priority=1, ALPN=b'\x02h3\x02h2', Port=443

[VERIFIED] Modern DNS Records Parser passed all tests with 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting

- **`ValueError: SRV RDATA too short`**: Occurs if the binary payload has fewer than 7 bytes.
- **`UnicodeDecodeError` in CAA**: CAA tags must be 7-bit ASCII letters. If corrupted binary is received, `.decode('ascii')` will raise an exception.
- **SVCB Parameter Length Mismatch**: If `offset + 4 + param_len > len(rdata)`, the packet is truncated. Our code guards against buffer overruns.

---
### Additional Python Beginner Foundations
- **Service Discovery Logic with SRV**:
  SRV records allow decoupling service names from physical IP addresses and port numbers. A client querying `_sip._tcp.example.com` receives both the target machine name and the exact TCP port, enabling dynamic service mesh architectures.
- **Handling Variable-Length SvcParams in Python**:
  In RFC 9460 (HTTPS/SVCB), parameters are encoded as variable key-value sequences. Using a loop that reads a 2-byte key, 2-byte length, and slices the exact payload allows parsing unknown future parameters without breaking backward compatibility.

### Extended Debugging Guide
1. **Weight Zero in SRV Records**: When multiple SRV targets have equal priority, RFC 2782 specifies that targets with `weight 0` should be given a very small chance of selection rather than zero, preventing starvation.
2. **Critical CAA Flags**: If a CAA record has bit 0 set (`flags = 0x80`), any CA that does not recognize the tag must refuse to issue the certificate.

## 6. Beginner Exercises & Challenges

1. **SRV Weighted Selection**: Write a function that takes a list of `SRVRecord` objects with equal priority and selects one proportionally based on `weight`.
2. **ALPN Wire Decoder**: Parse the binary ALPN parameter (`\x02h3\x02h2`) into a list of strings `['h3', 'h2']`.
3. **CAA Critical Flag Checker**: Inspect `flags & 0x80`. If set, print a warning that the issuer MUST reject issuance if it cannot understand the tag.\n