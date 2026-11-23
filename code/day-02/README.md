# Day 02 Lab: Parsing Raw Ethernet II Frames in Python

> **Welcome to Day 2!** Every time your laptop communicates with your Wi-Fi router or an Ethernet switch, it wraps data inside an **Ethernet Frame**. In this lab, you will learn how to decode raw binary network frames into human-readable MAC addresses and protocol names.

---

## 🎯 What Does This Lab Do?
`parse_ethernet_frame.py` takes raw hex bytes straight off a network wire and decodes the standard **14-byte Ethernet II header**:
* **Destination MAC Address** (Bytes 0 to 5, 6 bytes): Who should receive this frame.
* **Source MAC Address** (Bytes 6 to 11, 6 bytes): Who sent this frame.
* **EtherType** (Bytes 12 to 13, 2 bytes): What protocol is inside the payload (`0x0800` = IPv4, `0x0806` = ARP, `0x86DD` = IPv6).
* **Payload**: The actual data (IP packet) carried inside!

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python parse_ethernet_frame.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Raw Byte Strings (`b"..."` and `bytes.fromhex(...)`)
* In Python, normal strings `'hello'` are Unicode text.
* But network packets are **raw binary bytes**!
* In Python, prefixing with `b` creates a byte string: `b"\x00\x1a\x2b"`.
* `bytes.fromhex("AA BB CC")` converts a string of hexadecimal letters directly into binary bytes.

### 2. Combining Bytes with Bit Shifting: `(b1 << 8) | b2`
* The EtherType is a 16-bit integer split across two 8-bit bytes (e.g. `0x08` and `0x00`).
* `raw_bytes[12] << 8` shifts the first byte 8 bits to the left.
* `| raw_bytes[13]` uses bitwise OR to glue the second byte into the lower 8 bits.
* Result: `0x0800` (2048 in decimal, representing IPv4!).

### 3. Formatting MAC Addresses with `:02X`
* In Python:
  - `02`: Print at least 2 digits (pad with leading zero if needed).
  - `X`: Format as UPPERCASE hexadecimal.
* `":".join(f"{b:02X}" for b in byte_seq)` turns `[170, 187, 204]` into `"AA:BB:CC"`.

---

## 🔍 Code Walkthrough

```python
ETHERTYPES = {
    0x0800: "IPv4 (Internet Protocol v4)",
    0x0806: "ARP (Address Resolution Protocol)",
    0x86DD: "IPv6 (Internet Protocol v6)"
}

def parse_ethernet_header(raw_bytes):
    # 1. Check minimum length
    if len(raw_bytes) < 14:
        raise ValueError("Ethernet header must be at least 14 bytes long!")

    # 2. Extract 6-byte Destination and Source MACs
    dst_mac = ":".join(f"{b:02X}" for b in raw_bytes[0:6])
    src_mac = ":".join(f"{b:02X}" for b in raw_bytes[6:12])

    # 3. Combine bytes 12 and 13 to get EtherType
    ethertype = (raw_bytes[12] << 8) | raw_bytes[13]
    protocol_name = ETHERTYPES.get(ethertype, "Unknown Protocol")

    return {
        "Destination MAC": dst_mac,
        "Source MAC": src_mac,
        "EtherType": hex(ethertype),
        "Protocol": protocol_name
    }
```

---

## 📋 Expected Terminal Output
```text
==================================================
   DAY 2 LAB: DECODING RAW ETHERNET II FRAMES    
==================================================
Raw Frame Hex:
5254001234560800271a2b3c08004500003c

--- Decoded Ethernet Header ---
Destination MAC : 52:54:00:12:34:56
Source MAC      : 08:00:27:1A:2B:3C
EtherType       : 0x0800
Encapsulated    : IPv4 (Internet Protocol v4)
Payload Length  : 4 bytes
==================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: What is the special MAC address `FF:FF:FF:FF:FF:FF` used for? (Answer: The Ethernet Broadcast address! Sent to every device on the local network).
2. **Challenge 2**: In `parse_ethernet_frame.py`, pass a frame with EtherType `0x0806` and verify that the script identifies it as ARP!
