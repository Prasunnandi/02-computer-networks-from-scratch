# Hands-On Lab: Day 29 - Cryptographic SYN Cookie Defense (`syn_cookie_crypto_sim.py`)

## 1. What Are We Building & Why Does It Matter?
In a standard TCP 3-way handshake, when a server receives a `SYN` packet, it allocates a kernel data structure (`struct request_sock`, $\approx 280$ bytes) and places it into the **SYN Backlog Queue**, waiting for the client's final `ACK`.

In a **TCP SYN Flood Attack**, an attacker sends millions of spoofed `SYN` packets from fake IP addresses and never sends the final `ACK`. Within seconds, the server's backlog queue fills completely, causing the operating system to drop legitimate user connections!

In 1996, Daniel J. Bernstein (djb) and Eric Schenk invented **SYN Cookies** (standardized in RFC 4987).
When the backlog fills, instead of dropping connections or saving memory:
1. The server allocates **ZERO bytes of state memory**.
2. It encodes the entire connection state (timestamp, MSS, and a cryptographic HMAC signature) directly inside the 32-bit **Initial Sequence Number (ISN)** of the `SYN-ACK` packet!
3. When the legitimate client responds with `ACK = ISN + 1`, the server extracts and cryptographically verifies the cookie without having saved any previous record!

In this lab, we build a complete RFC 4987 cryptographic cookie generator and validator.

---

## 2. Python Concepts for Beginners
1. **Bitwise Shifting and Masking**:
   - `t << 27` shifts the 5-bit time counter 27 positions to the left, placing it in the top 5 bits (bits 31..27).
   - `& 0x1F` masks with binary `0001 1111` (decimal 31) to retain only 5 bits.
   - `|` (Bitwise OR) combines bitfields together into a single 32-bit integer.
2. **Cryptographic Hashing with `hmac` & `hashlib`**:
   - `hmac.new(secret_key, msg, hashlib.sha256).digest()` creates a cryptographically secure message authentication code.
   - Attackers cannot forge cookies without knowing the server's private secret key.
3. **Binary Packing with `struct`**:
   - `struct.unpack('>I', b'\x00' + mac[:3])[0]` converts 3 raw bytes into a big-endian 32-bit unsigned integer.

---

## 3. Step-by-Step Code Walkthrough

### The 32-Bit Bitfield Layout
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Time (5) |MSS(3)|           Cryptographic MAC (24)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

```python
def generate_cookie(self, saddr, daddr, sport, dport, client_mss, timestamp=None):
    t = self._get_time_counter(timestamp)
    mss_idx = self._mss_to_index(client_mss)
    msg = f'{saddr}:{daddr}:{sport}:{dport}:{t}'.encode('utf-8')
    mac = hmac.new(self.secret_key, msg, hashlib.sha256).digest()
    mac_24 = struct.unpack('>I', b'\x00' + mac[:3])[0] & 0x00FFFFFF
    return (t << 27) | (mss_idx << 24) | mac_24
```
- The 5-bit slow counter `t` increments once every 64 seconds.
- The 3-bit MSS index maps the client's Maximum Segment Size to an 8-entry table (e.g. 1460 bytes).
- The lower 24 bits are a keyed HMAC signature of the IP 5-tuple and timestamp.
- When an ACK arrives, the server re-computes the HMAC. If the signature matches, the connection is genuine and the socket is created!

---

## 4. How to Run the Script

```bash
cd code/day-29
python syn_cookie_crypto_sim.py
```

### Expected Output
```
====================================================
DAY 29: CRYPTOGRAPHIC TCP SYN COOKIE DEFENSE (RFC 4987)
====================================================
Incoming SYN from 198.51.100.42:54321 (Requested MSS: 1460)
SYN Backlog full! Server generates stateless SYN Cookie...
Generated 32-bit ISN Cookie : 0x762B4A1C (1982548508)
Server saves ZERO bytes of memory in state table! (SYN flood defeated)

Client completes 3-way handshake with ACK: 0x762B4A1D
Cookie Authenticity Check   : VALID
Recovered Negotiated MSS    : 1460 bytes
Tampered ACK Check (1-bit flip): BLOCKED (Fake/Tampered)

[VERIFIED] Stateless cryptographic SYN cookie generated and verified cleanly!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`TypeError: Unicode-objects must be encoded before hashing`**:
   - `hmac` requires raw `bytes`, not Python strings. Always call `.encode('utf-8')` on string messages.
2. **Endianness Mismatch**:
   - In network protocols, numbers are always **Big-Endian** (most significant byte first). In `struct`, use the prefix `>` for big-endian.

---

## 6. Beginner Exercises & Challenges
1. **Cookie Expiration Test**: Pass `current_time = time.time() + 300` (5 minutes later) to `validate_cookie`. Verify that the cookie is rejected as expired.
2. **Inspect Kernel Setting**: On Linux, run `sysctl net.ipv4.tcp_syncookies`. A value of `1` means SYN cookies are enabled when the backlog overflows.
