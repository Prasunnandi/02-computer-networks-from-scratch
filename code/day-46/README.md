# Day 46: IPv4 Link-Local (APIPA) & Multicast DNS (mDNS) Lab Tutorial

Welcome to Day 46 of Computer Networks from Scratch. Today, you will build an RFC 3927 compliant Automatic Private IP Addressing (APIPA) engine with ARP probing and an RFC 6762 Multicast DNS (mDNS) codec.

---

## 1. What Are We Building & Why Does It Matter?

When a host cannot contact a DHCP server (e.g. ad-hoc networking, broken router, home LAN switch without a gateway), standard unicast IP routing fails. To provide zero-configuration peer-to-peer networking, operating systems use **APIPA** (RFC 3927):
1. The host autonomously selects a pseudorandom IPv4 address from the reserved `169.254.1.0/16` range.
2. It sends 3 **ARP Probes** (`SIP=0.0.0.0`, `DIP=candidate_ip`) to verify no other host on the wire is using that IP.
3. If no conflict occurs, it broadcasts 2 gratuitous **ARP Announcements** to claim the IP and update peer ARP caches.
4. For hostname discovery without a central DNS server, devices use **mDNS** (RFC 6762) over multicast address `224.0.0.251:5353` to resolve `.local` domain names.

---

## 2. Python Concepts for Beginners

### A. Random Integer Ranges (`random.randint`)
Generate pseudorandom candidate octets between boundaries:
```python
import random

octet3 = random.randint(1, 254)
octet4 = random.randint(1, 254)
candidate_ip = f"169.254.{octet3}.{octet4}"
```

### B. Binary DNS Label Serialization
DNS domain names (like `printer.local`) are encoded as length-prefixed byte sequences ending with a null byte:
```python
parts = "printer.local".split(".")
payload = bytearray()
for part in parts:
    payload.append(len(part))
    payload.extend(part.encode("ascii"))
payload.append(0)  # Terminating null byte
```

### C. Big-Endian Struct Headers (`struct.pack`)
The DNS header consists of six 16-bit integers (12 bytes total):
```python
import struct

header = struct.pack("!HHHHHH", 0, 0x0000, 1, 0, 0, 0)
```

---

## 3. Step-by-Step Code Walkthrough

1. **`ARPPacket` Dataclass**: Captures ARP fields (`op`, `sha`, `spa`, `tha`, `tpa`).
2. **`APIPAAllocator` Class**:
   - `generate_candidate_ip()`: Selects a valid address in `169.254.1.1` to `169.254.254.254`, excluding reserved network edges.
   - `build_arp_probe()`: Creates an ARP Probe with `spa="0.0.0.0"` to avoid polluting peer ARP tables before claiming ownership.
   - `build_arp_announcement()`: Creates a Gratuitous ARP frame announcing `candidate_ip` to `FF:FF:FF:FF:FF:FF`.
   - `allocate()`: Transmits 3 probes. If any collide with `network_existing_ips`, picks a new candidate. On 3 clean probes, emits 2 announcements and locks the configuration.
3. **`MDNSCodec` Class**:
   - `encode_query()`: Builds a binary DNS query for `.local` domains with `QDCOUNT=1`.
   - `decode_query()`: Slices the 12-byte DNS header and reconstructs the dot-separated domain name string.
4. **`main()` Test Suite**: Executes conflict-free APIPA address allocation and validates mDNS round-trip serialization.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-46/apipa_arp_probe_and_mdns_sim.py
```

Expected output:
```text
=== Day 46: IPv4 Link-Local (APIPA) & Multicast DNS (mDNS) Simulator ===
[*] Test 1 Passed: Claimed APIPA IP 169.254.142.88 with 5 ARP frames
[*] Test 2 Passed: Encoded & Decoded mDNS query for 'printer.local' (Type 1)
All APIPA and mDNS assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`IndexError` in label decoding**: Occurs if the length byte indicates more characters than remaining in the packet buffer. Ensure the packet buffer is complete.
- **`AssertionError: len(packets) == 5`**: If a generated IP randomly collides with an existing IP in the test list, extra probes will be sent. The test list uses a small set of IPs to minimize collision probability.

---

## 6. Beginner Exercises & Challenges

1. **Simulate Collision Backoff**: Implement RFC 3927 Section 2.2.1 exponential backoff: after 10 collisions, rate-limit new candidate generation to 1 probe sequence per minute.
2. **Implement mDNS A Record Response**: Write `encode_response()` in `MDNSCodec` that generates a DNS Answer section with TTL and the 4-byte IPv4 address.
3. **Handle Incoming ARP Collisions After Claim**: Add an `inspect_gratuitous_arp()` method to `APIPAAllocator` that triggers address defense if another host announces the same claimed IP.
