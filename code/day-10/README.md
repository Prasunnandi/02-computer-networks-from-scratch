# Day 10 Lab: UDP Protocol Internals & Pseudo-Header Checksum in Python

> **Welcome to Day 10!** When playing online multiplayer games (like Fortnite or Valorant) or streaming live video, computers don't use TCP. They use **UDP (User Datagram Protocol)**!
> UDP has no handshakes, no acknowledgments, and no delays. In this lab, you will learn how the 8-byte UDP header works and how the 12-byte IP Pseudo-Header protects against misrouted packets.

---

## 🎯 What Does This Lab Do?
`udp_telemetry_server.py` demonstrates:
1. **The 8-Byte UDP Header**: Unpacking the 4 core fields: Source Port, Destination Port, Length, and Checksum.
2. **The 12-Byte Pseudo-Header**: Proving why UDP computes a checksum over Layer 3 IP addresses, ensuring that a packet delivered to the wrong server is immediately discarded!
3. **Datagram Boundaries**: Proving that unlike TCP (which is a continuous stream of bytes), UDP preserves discrete message boundaries (sending 2 packets creates 2 separate receipts).

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python udp_telemetry_server.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Packing the 8-Byte Header: `!HHHH`
* In `struct.pack("!HHHH", ...)`:
  - `H` is an unsigned 16-bit integer (2 bytes).
  - Four `H`s = $4 \times 2 = 8\text{ bytes}$ total!
  - `H1`: Source Port
  - `H2`: Destination Port
  - `H3`: UDP Datagram Length
  - `H4`: Calculated Checksum

### 2. Building the 12-Byte Pseudo-Header
* Layer 4 needs to verify Layer 3 IP addresses:
  ```python
  pseudo_header = struct.pack("!4s4sBBH", src_bytes, dst_bytes, 0, 17, udp_len)
  ```
  - `4s` (4 bytes): Source IP
  - `4s` (4 bytes): Destination IP
  - `B` (1 byte): Zero padding
  - `B` (1 byte): Protocol number (`17` is the official standard number for UDP!)
  - `H` (2 bytes): UDP Length

### 3. Detecting Misrouted Packets
* If a router accidentally delivers a UDP datagram to `10.0.0.99` instead of `10.0.0.50`, the destination server checks the checksum with its own IP.
* Because the IP doesn't match the sender's pseudo-header, the checksum validation **fails**, and the server safely discards the packet!

---

## 🔍 Code Walkthrough

```python
# 1. Crafting a UDP packet carrying high-speed stock quotes:
telemetry = b"QUOTE:AAPL:185.50:VOL=5000:TIMESTAMP=1700000000"
packet = UDPDatagram.craft("192.168.1.100", "10.0.0.50", 54321, 53, telemetry)

# 2. Decoding and validating checksum:
decoded = UDPDatagram.decode(packet, src_ip="192.168.1.100", dst_ip="10.0.0.50")
print("Checksum valid:", decoded["is_checksum_valid"]) # True!

# 3. Simulating arrival at wrong IP:
wrong_decoded = UDPDatagram.decode(packet, src_ip="192.168.1.100", dst_ip="10.0.0.99")
print("Checksum valid on wrong IP:", wrong_decoded["is_checksum_valid"]) # False!
```

---

## 📋 Expected Terminal Output
```text
============================================================
DAY 10 LAB: UDP PROTOCOL ENGINE & PSEUDO-HEADER CHECKSUM
============================================================

[1] Crafting UDP Datagram from 192.168.1.100:54321 -> 10.0.0.50:53 (DNS/Custom)...
    Raw Datagram Length: 55 bytes (8B header + 47B payload)
    UDP Header Hex: d4 31 00 35 00 37 6f 2e

[2] Decoding datagram on server with matching IP addresses...
    Source Port     : 54321
    Destination Port: 53
    UDP Length      : 55 bytes
    Checksum        : 0x6f2e
    Checksum Valid  : True
    Payload Data    : QUOTE:AAPL:185.50:VOL=5000:TIMESTAMP=1700000000
    [PASS] UDP datagram and 12-byte Pseudo-Header checksum verified valid.

[3] Simulating Router Misroute: Target host receives datagram at wrong IP (10.0.0.99)...
    Checksum Valid on Wrong IP: False
    [PASS] Pseudo-header checksum prevented misrouted packet ingestion.

[4] Verifying Datagram Message Boundary Preservation...
    [PASS] Datagram boundaries preserved across separate transmissions.
============================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: Why does live video streaming use UDP instead of TCP? What happens to the video if a packet is lost? (Answer: UDP drops the single pixel frame without pausing the video; TCP would freeze the video for 2 seconds while trying to resend the lost frame!).
2. **Challenge 2**: In `udp_telemetry_server.py`, change `dst_port = 123` (NTP network time protocol) and verify that the script crafts and decodes the new datagram!
