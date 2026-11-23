# Day 06 Lab: IPv4 Packet Header Decoder & Ones' Complement Checksum in Python

> **Welcome to Day 6!** At Layer 3 of the Internet, billions of packets are routed across the globe every second. Every single packet starts with a standard **20-Byte IPv4 Header**.
> In this lab, you will learn how to unpack raw binary network bytes into structured fields and calculate the mathematical 16-bit Ones' Complement Checksum used by all Internet routers!

---

## 🎯 What Does This Lab Do?
`parse_ipv4_header.py` demonstrates:
1. **Binary Unpacking**: Reads raw 20-byte packet headers and extracts:
   - Version (`4`) and Header Length (`IHL = 5` words = 20 bytes)
   - Total Packet Length (bytes)
   - Identification and Fragmentation Flags (`DF`, `MF`)
   - Time to Live (`TTL`, hop limit countdown)
   - Protocol (`6` for TCP, `17` for UDP)
   - Source and Destination IP Addresses
2. **RFC 1071 Checksum Math**: Calculates and validates the 16-bit Ones' Complement Checksum over all 16-bit words.
3. **Router Hop Simulation**: Proves why a router must recalculate the checksum at every single hop when it decrements TTL by 1!

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python parse_ipv4_header.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. The `struct` Module (Packing and Unpacking Binary Data)
* In Python, `struct` is how you read raw binary C structures from network packets.
* Format string: `"!BBHHHBBH4s4s"`
  - `!` : **Network Byte Order (Big-Endian)**. High-order byte comes first.
  - `B` : **Unsigned Char (1 byte)**: Numbers from 0 to 255.
  - `H` : **Unsigned Short (2 bytes / 16 bits)**: Numbers from 0 to 65,535.
  - `4s` : **4 Raw Bytes**: Exactly the size of a 32-bit IPv4 address!
* Example: `struct.unpack("!BBHHHBBH4s4s", raw_bytes[:20])` instantly unpacks all 10 header fields!

### 2. Translating IP Addresses: `socket.inet_ntoa`
* `socket.inet_ntoa(4_bytes)`: Converts 4 raw binary bytes into a human-readable IP string like `"192.168.1.10"`.
* `socket.inet_aton("192.168.1.10")`: Converts the dotted string back into 4 raw binary bytes.

### 3. What is Ones' Complement Checksum?
* In standard addition, when two 16-bit numbers overflow past 65,535, the extra bit (carry bit) is normally lost.
* In **Ones' Complement** addition, the carry bits from the top ($total \gg 16$) are added **back into the bottom**:
  ```python
  while (total >> 16) > 0:
      total = (total & 0xFFFF) + (total >> 16)
  ```
* Finally, all bits are inverted (`~total`). This is the checksum!

---

## 🔍 Code Walkthrough

```python
import struct
import socket

# 1. Unpacking the 20-byte IPv4 header:
(first_byte, dscp_ecn, total_len, ident, flags_offset,
 ttl, protocol, checksum, src_raw, dst_raw) = struct.unpack("!BBHHHBBH4s4s", raw_packet[:20])

# 2. Extracting bitfields:
version = (first_byte >> 4) & 0x0F  # Top 4 bits: 4
ihl = (first_byte & 0x0F) * 4       # Bottom 4 bits: 20 bytes
flag_df = bool((flags_offset >> 14) & 0x01) # Don't Fragment bit

# 3. Converting IPs:
src_ip = socket.inet_ntoa(src_raw)
dst_ip = socket.inet_ntoa(dst_raw)
```

---

## 📋 Expected Terminal Output
```text
============================================================
DAY 06 LAB: IPV4 HEADER DECODER & ONES' COMPLEMENT CHECKSUM
============================================================

[1] Crafted Raw IPv4 Header (20 bytes):
    45 00 00 78 d4 31 40 00 40 06 57 73 c0 a8 01 0a 8e fa be 2e

[2] Decoded IPv4 Fields:
    - version               : 4
    - ihl_words             : 5
    - ihl_bytes             : 20
    - total_length          : 120
    - identification        : 54321
    - flags                 : {'reserved': False, 'dont_fragment': True, 'more_fragments': False}
    - ttl                   : 64
    - protocol              : 6
    - checksum              : 0x5773
    - is_checksum_valid     : True
    - source_ip             : 192.168.1.10
    - destination_ip        : 142.250.190.46

    [PASS] IPv4 Header decoded and Ones' Complement Checksum verified valid.

[3] Simulating Router Hop: Decrementing TTL from 64 to 63 without recalculating checksum...
    Hop TTL: 63, Checksum Valid: False
    [PASS] Corrupted/unrecalculated header correctly rejected by RFC 1071 validator.
============================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: Look at step [3]. Why does changing TTL from 64 to 63 cause the checksum validation to fail?
2. **Challenge 2**: In `parse_ipv4_header.py`, change `ttl = 128` and observe the new checksum value calculated!
