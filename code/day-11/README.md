# Hands-On Lab: Day 11 - Binary RFC 793 TCP Header Parser & Generator (`tcp_header_parser.py`)

## 1. What Are We Building & Why Does It Matter?
In computer networking, network interface cards transmit raw binary bytes, not JSON or text strings. Every packet transmitted across the Internet must follow strict binary format specifications defined in Request For Comments (RFC) standards.

The TCP header (RFC 793) is a 20-byte binary structure (longer if options are present). It contains bitfields for:
- Source and Destination Ports (16 bits each).
- Sequence and Acknowledgment Numbers (32 bits each).
- Header Length (Data Offset) and 8 Control Flags (SYN, ACK, FIN, RST, PSH, URG, ECE, CWR).
- Advertised Window Size (16 bits).

In this lab, we build `tcp_header_parser.py`, which uses Python's standard `struct` module to pack integer fields into genuine 20-byte binary packet headers and parse raw binary streams back into human-readable data.

---

## 2. Python Concepts for Beginners
1. **The `struct` Module**:
   - Python's built-in tool for converting between Python values (integers, strings) and C binary structs (`bytes`).
   - Format string `!HHIIHHHH`:
     - `!`: Network Byte Order (Big-Endian, where the most significant byte comes first).
     - `H`: 16-bit unsigned integer (2 bytes, 0 to 65,535).
     - `I`: 32-bit unsigned integer (4 bytes, 0 to 4,294,967,295).
2. **Bitwise Shift (`<<` and `>>`) & Masking (`&` and `|`)**:
   - The Data Offset (4 bits) and Flags (8 bits) are packed together into a 16-bit integer:
     - `(offset << 12) | flag_bits` shifts the 4-bit offset to the top 4 bits of the 16-bit integer.
     - `(packed >> 12) & 0x0F` extracts the 4-bit offset back out.

---

## 3. Step-by-Step Code Walkthrough

```python
import struct

def build_tcp_header(src_port: int, dst_port: int, seq_num: int, ack_num: int,
                     flags: dict, window: int = 65535) -> bytes:
    data_offset = 5 # 5 * 4 = 20 bytes
    flag_val = 0
    if flags.get("FIN"): flag_val |= 0x01
    if flags.get("SYN"): flag_val |= 0x02
    if flags.get("RST"): flag_val |= 0x04
    if flags.get("PSH"): flag_val |= 0x08
    if flags.get("ACK"): flag_val |= 0x10
    if flags.get("URG"): flag_val |= 0x20

    offset_and_flags = (data_offset << 12) | flag_val
    return struct.pack("!HHIIHHHH", src_port, dst_port, seq_num, ack_num,
                       offset_and_flags, window, 0, 0)
```
- `struct.pack("!HHIIHHHH", ...)` creates a 20-byte sequence:
  - 2 bytes (src) + 2 bytes (dst) + 4 bytes (seq) + 4 bytes (ack) + 2 bytes (flags) + 2 bytes (win) + 2 bytes (chk) + 2 bytes (urg) = 20 bytes!
- In `parse_tcp_header(raw_bytes)`:
  - `struct.unpack("!HHIIHHHH", raw_bytes[:20])` unpacks the fields back into Python integers.

---

## 4. How to Run the Script

```bash
cd code/day-11
python tcp_header_parser.py
```

### Expected Output
```
Building TCP SYN Header (Port 54321 -> 80, Seq 100000)...
Raw 20-Byte Header (Hex):
  d4310050000186a0000000005002ffff00000000

Parsing Binary Header:
  Source Port      : 54321
  Destination Port : 80 (HTTP)
  Sequence Number  : 100000
  Ack Number       : 0
  Header Length    : 20 bytes (Data Offset: 5 words)
  Active Flags     : ['SYN']
  Advertised Window: 65535 bytes
```

---

## 5. Common Python Errors & Troubleshooting
1. **`struct.error: unpack requires a buffer of 20 bytes`**:
   - Occurs if `raw_bytes` has fewer than 20 bytes. Always verify `len(raw_bytes) >= 20`.
2. **`OverflowError: 'H' format requires 0 <= number <= 65535`**:
   - You passed a port number or window size greater than 65535.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

