# Day 42: DHCP Binary Packet Codec & Options TLV Parser Lab Tutorial

Welcome to Day 42 of Computer Networks from Scratch. Today, you will build a binary parser and encoder for RFC 2131 BOOTP/DHCP packets and RFC 2132 Type-Length-Value (TLV) options.

---

## 1. What Are We Building & Why Does It Matter?

DHCP packets are transported inside UDP datagrams (Client port 68, Server port 67). Unlike text-based application protocols (like HTTP), DHCP uses a fixed 236-byte binary header inherited from BOOTP (RFC 951), followed by a 4-byte Magic Cookie (`0x63825363`), followed by a variable-length list of TLV options.

Without understanding binary packet framing:
- Network engineers cannot parse pcap packet captures or debug PXE boot failures.
- Embedded devices and IoT firmware cannot unpack lease times, subnet masks, or router gateways.
- Systems programmers cannot build high-performance network services or DHCP relay daemons.

In this lab, you write pure Python standard library codecs using `struct` to serialize and parse real binary DHCP packets.

---

## 2. Python Concepts for Beginners

### A. Binary Struct Packing (`struct.pack` & `struct.unpack`)
Network protocols specify Big-Endian (`!`) network byte order:
```python
import struct

header = struct.pack("!BB", 53, 1)  # Option 53, Length 1
```

### B. Hexadecimal Strings to Raw Bytes (`bytes.fromhex`)
MAC addresses written as hex strings can be converted to 6 raw bytes:
```python
mac_bytes = bytes.fromhex("525400123456")
assert len(mac_bytes) == 6
```

### C. Byte Padding (`ljust`)
Fixed-width string buffers in C structs (like `chaddr` [16 bytes], `sname` [64 bytes], and `file` [128 bytes]) must be padded with null bytes (`\x00`):
```python
padded_mac = mac_bytes.ljust(16, b"\x00")
```

---

## 3. Step-by-Step Code Walkthrough

1. **Magic Cookie Verification**: RFC 2132 defines `0x63825363` as the 4-byte sequence directly preceding options. If absent, the packet is a legacy BOOTP frame.
2. **`DHCPOptionsTLVCodec`**:
   - `encode_options()`: Loops through Python dictionary keys, maps tag IDs to data types (IP addresses, strings, 16-bit MTUs, 32-bit lease durations), and packs them as `[Tag (1B)][Len (1B)][Value (Len B)]`. Appends Tag 255 (`END`).
   - `decode_options()`: Iterates through the payload. Reads Tag and Length, slices the byte buffer, unpacks data according to RFC 2132 definitions, and ignores `PAD` (Tag 0) bytes.
3. **`DHCPPacketCodec`**:
   - `encode()`: Uses format string `!BBBBIHH4s4s4s4s16s64s128s` to construct the 236-byte BOOTP header, appends the magic cookie, and appends the TLV options byte stream.
   - `decode()`: Validates packet length (at least 240 bytes), unpacks the 236-byte header, verifies the magic cookie, and passes remaining bytes to `decode_options()`.
4. **`main()` Test Suite**: Verifies round-trip serialization and byte-exact deserialization for both `DHCPDISCOVER` and `DHCPOFFER`.

---

## 4. How to Run & Expected Output

Execute the script with Python 3:
```bash
python code/day-42/dhcp_packet_codec_options_tlv.py
```

Expected output:
```text
=== Day 42: DHCP Binary Packet Codec & Options TLV Parser ===
[*] Serialized DHCPDISCOVER packet length: 260 bytes
[*] Successfully decoded and asserted binary field equality!
[*] Decoded DHCPOFFER: 192.168.1.50, DNS: ['1.1.1.1', '8.8.8.8'], Lease: 86400s
All DHCP Binary Codec & TLV Parser assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`struct.error: unpack requires a buffer of 236 bytes`**: The input buffer was smaller than the 236-byte BOOTP header. Ensure your network socket received the entire datagram.
- **`ValueError: Invalid DHCP magic cookie`**: Occurs if byte offset 236 does not equal `0x63825363`. Verify that the BOOTP header fields were not truncated or padded with extra offsets.
- **`UnicodeDecodeError` in hostname/domain parsing**: Use `errors="replace"` when decoding ASCII string options to gracefully handle non-compliant vendor options.

---

## 6. Beginner Exercises & Challenges

1. **Add Option 121 (Classless Static Routes)**: Implement RFC 3442 Option 121 decoder which encodes variable-length subnet masks and destination IP prefixes alongside router gateways.
2. **Enforce 300-Byte Minimum Packet Length**: RFC 2131 states that clients should pad DHCP packets with null bytes (`Tag 0`) if total packet size is under 300 bytes. Update `encode()` to pad options to 300 bytes.
3. **Implement Sub-Option TLV Parsing**: Implement Option 82 (Relay Agent Information), which itself contains nested sub-options (Sub-option 1: Agent Circuit ID, Sub-option 2: Agent Remote ID).
