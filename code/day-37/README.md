# Day 37: DNS Transport Simulator (UDP Truncation, TCP Fallback & EDNS0)

## 1. What Are We Building & Why Does It Matter?
DNS historically ran exclusively over UDP port 53. Because Ethernet MTU is typically 1500 bytes and IP fragmentation causes packet loss, RFC 1035 restricted standard DNS UDP payloads to **512 bytes**.
- When an answer (such as dozens of IPs or large DNSSEC signatures) exceeds 512 bytes, the nameserver sets the **Truncation Flag (`TC=1`)** in the DNS header.
- Upon seeing `TC=1`, the client drops the partial UDP response and immediately initiates a 3-way handshake to re-query over **TCP port 53**.
- In 1999, **EDNS0 (RFC 6891)** introduced the `OPT` pseudo-Resource Record (Type 41), allowing clients to advertise modern buffer sizes (e.g. 1232 to 4096 bytes) directly inside UDP queries, avoiding slow TCP fallbacks.

In this lab, we build a **DNS Transport Simulator** in pure Python that models classic UDP truncation, automatic client TCP fallback, and EDNS0 OPT buffer negotiation.

---

## 2. Python Concepts for Beginners

### A. Simulating Protocol State Transitions
We model network interactions using simple state machines: when condition `payload > limit` is met, we return `tc_flag=True`, which triggers the client's branch to call `query_tcp_fallback()`.

### B. Binary Struct Layout for Pseudo-Records
The EDNS0 `OPT` record is not a database record; it is a synthetic protocol extension packed in the Additional section:
- Root Name: `0x00` (1 byte).
- Type: `41` (`!H` = 2 bytes).
- UDP Buffer Size: `4096` (`!H` = 2 bytes).
- Extended Flags & RDLENGTH (`!II` = 8 bytes).
```python
opt_bytes = struct.pack("!BHHII", 0, 41, 4096, 0, 0)
```

### C. Assertions for Verification
We use `assert` statements throughout the code to mathematically guarantee that our protocol simulations conform strictly to RFC requirements.

---

## 3. Step-by-Step Code Walkthrough

1. **`DNSTransportSimulator`**: Generates a synthetic zone with 34 `A` records that exceed the 512-byte limit.
2. **`query_udp_classic()`**: Simulates legacy RFC 1035 resolver behaviour: computes byte length, detects overflow, sets `tc_flag=True`, and returns 0 records.
3. **`query_tcp_fallback()`**: Simulates establishing a TCP stream and retrieving the full record set without truncation.
4. **`query_udp_edns0()`**: Simulates modern EDNS0 negotiation with a 4096-byte buffer, delivering the entire payload in a single UDP packet.
5. **`build_edns0_opt_record()`**: Packs the raw binary wire format of an RFC 6891 OPT record.
6. **`main()` Function**: Executes the full sequence, verifying each step.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-37/dns_transport_fallback_sim.py
```

Expected output:
```text
====================================================
DAY 37: DNS TRANSPORT (UDP TRUNCATION & TCP FALLBACK)
====================================================
1. Classic UDP Query:
   Payload Size: 512B / Limit: 512B | TC Flag: True
   [+] Client detected TC=1! Triggering automatic TCP fallback...
2. TCP Fallback Query:
   Transport: TCP | Records Delivered: 34 / 34
   [PASS] TCP successfully transferred entire oversized answer without truncation.
3. Modern EDNS0 Query:
   Transport: UDP (EDNS0) | Buffer: 4096B | Records: 34
   [PASS] EDNS0 transferred full answer over single UDP packet!
   [PASS] OPT Pseudo-RR wire format verified (Type 41, Buffer 4096B).

[VERIFIED] DNS Transport & Fallback Simulator passed all tests with 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting

- **`AssertionError: Classic UDP must set TC=1`**: Occurs if simulated record count is too small to overflow 512 bytes.
- **Firewall Blocking TCP 53**: In production environments, misconfigured firewalls often block TCP port 53 while allowing UDP port 53. If a packet overflows 512 bytes, queries fail with timeouts.
- **Path MTU Black Holes**: While EDNS0 supports 4096 bytes, setting buffer sizes above 1400 bytes often causes IP fragmentation issues. Most modern resolvers use 1232 bytes (DNS Flag Day 2020 standard).

---

## 6. Beginner Exercises & Challenges

1. **DNS Flag Day 1232B Cap**: Change the EDNS0 buffer size to 1232 bytes and test what happens when an answer exceeds 1232 bytes.
2. **TCP 2-Byte Length Framer**: In real TCP DNS streams, every query and response is prefixed by a 16-bit integer length. Write a function `frame_tcp_message(data)` that prepends `struct.pack("!H", len(data))`.
3. **DO Bit (DNSSEC OK)**: Add support for setting the DNSSEC OK bit (`DO=1`) in the extended flags field of the OPT record.
