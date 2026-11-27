# Day 47: LLMNR & NetBIOS Name Resolution Lab Tutorial

Welcome to Day 47 of Computer Networks from Scratch. Today, you will build an RFC 1001/1002 NetBIOS half-byte name encoder/decoder and simulate RFC 4795 Link-Local Multicast Name Resolution (LLMNR) poisoning attacks.

---

## 1. What Are We Building & Why Does It Matter?

Before active directory DNS was ubiquitous across Windows environments, local network name resolution relied on **NetBIOS-over-TCP/IP (NBT)** and later **LLMNR** (UDP port 5355).

NetBIOS uses a unique 32-byte encoding where each byte of a 16-character name is split into two 4-bit nibbles, each converted to an ASCII character by adding `0x41` ('A'). The 16th byte indicates the service type (e.g. `0x00` Workstation, `0x20` File Server).

However, because LLMNR queries are unauthenticated local multicasts (`224.0.0.252`), an attacker on the local network running tools like *Responder* can immediately reply with their own IP address, poisoning the client cache and harvesting NTLM credentials.

---

## 2. Python Concepts for Beginners

### A. Nibble Extraction with Bit Shifts
Extracting the upper 4 bits and lower 4 bits of an 8-bit unsigned byte:
```python
high_nibble = (b >> 4) & 0x0F
low_nibble = b & 0x0F
```

### B. ASCII Character Arithmetic
Adding an offset integer to transform a 0–15 value into ASCII characters 'A' through 'P':
```python
ascii_char_code = high_nibble + 0x41  # 0 -> 'A' (65), 1 -> 'B' (66)
```

### C. String Right Padding (`ljust`)
Padding a string with space characters to reach exact 15-byte NetBIOS length:
```python
padded = name.upper()[:15].ljust(15, " ")
```

---

## 3. Step-by-Step Code Walkthrough

1. **`NetBIOSCodec` Class**:
   - `encode_name()`:
     - Truncates and pads the name to 15 uppercase ASCII characters.
     - Appends the 1-byte service type (e.g. `0x20`).
     - Splits each byte into high and low nibbles, adds `0x41`, and prepends length byte `32`.
   - `decode_name()`:
     - Reverses the transformation by subtracting `0x41` and bitwise shifting: `(high << 4) | low`.
     - Extracts the 15-byte name string and trailing service type byte.
2. **`LLMNRSimulator` Class**:
   - `resolve()`: Demonstrates how unauthenticated broadcast/multicast queries allow malicious third parties to inject rogue IP mappings before genuine servers reply.
3. **`main()` Test Suite**: Verifies round-trip NetBIOS encoding/decoding and validates simulated rogue poisoning attack detection.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-47/llmnr_netbios_poison_simulator.py
```

Expected output:
```text
=== Day 47: LLMNR & NetBIOS Name Resolution Simulator ===
[*] Test 1 Passed: NetBIOS Name 'FILESERVER' (Service 0x20) encoded to 34 bytes and decoded perfectly
[*] Test 2 Passed: Legitimate LLMNR resolution for 'win-dc-01' -> 10.0.0.1
[*] Test 3 Passed: Detected simulated rogue LLMNR poison response (10.0.0.99)
All LLMNR and NetBIOS assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`ValueError: Expected NetBIOS name length 32`**: Occurs if the input buffer does not follow RFC 1001 label framing. Ensure the initial length byte is 32.
- **`IndexError` in nibble decoding**: Ensure the encoded buffer contains an even number of bytes (32 characters representing 16 raw bytes).

---

## 6. Beginner Exercises & Challenges

1. **Service Type Lookup Table**: Create a dictionary mapping common NetBIOS service bytes (`0x00`, `0x03`, `0x20`, `0x1B`, `0x1D`) to their human-readable roles.
2. **Add Group Name Flag Support**: NetBIOS names can be unique or group addresses (e.g. domain master browsers). Add a boolean parameter to encode this bit in the registration flags.
3. **Implement Poison Mitigation**: Write a validation function that queries unicast DNS first and rejects any LLMNR response that contradicts authoritative DNS records.
