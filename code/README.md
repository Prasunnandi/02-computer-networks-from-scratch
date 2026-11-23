# Hands-On Python Labs Guide: Computer Networks from Scratch

> **Welcome to the Networking Code Suite!** This directory contains self-contained Python implementations and simulations for the first 10 days of your Computer Networks curriculum.
> Every lab has been designed from the ground up to be **freshman and beginner friendly**, with zero external package dependencies (pure Python Standard Library).

---

## 🚀 Quick Start: How to Run Any Lab

You only need standard Python 3 (Python 3.8 or higher) installed on your system.

To run any day's lab, open your terminal and navigate to the code folder:

```bash
# Day 1: Binary, Hex & Signal Foundations
python day-01/binary_hex_converter.py
python day-01/binary_signal_sim.py

# Day 2: Parsing Raw Ethernet II Frames
python day-02/parse_ethernet_frame.py

# Day 3: Address Resolution Protocol (ARP) & Cache
python day-03/arp_cache_simulator.py

# Day 4: IPv4 Subnetting & CIDR Bitmask Calculator
python day-04/subnet_calculator.py

# Day 5: Network Address Translation (NAT) Router
python day-05/nat_simulator.py

# Day 6: IPv4 Header Decoder & 16-Bit Checksum Math
python day-06/parse_ipv4_header.py

# Day 7: IP Fragmentation & Reassembly Engine
python day-07/fragmentation_simulator.py

# Day 8: ICMP Echo & Custom Traceroute Simulator
python day-08/custom_traceroute.py

# Day 9: 5-Tuple Demultiplexing & Port Exhaustion
python day-09/port_scanner_and_demux.py

# Day 10: UDP Datagrams & Pseudo-Header Checksum
python day-10/udp_telemetry_server.py
```

---

## 📁 Directory Structure & Lab Index

Each day's folder includes its own dedicated **`README.md`** explaining the networking concepts, Python building blocks, line-by-line code logic, and beginner practice exercises:

| Directory | Lab Script | Networking & Python Concepts | Beginner Guide |
| :--- | :--- | :--- | :---: |
| **`day-01/`** | `binary_hex_converter.py` | Binary, Hexadecimal, Base conversion math, Shannon capacity | [day-01/README.md](day-01/README.md) |
| **`day-02/`** | `parse_ethernet_frame.py` | Raw byte strings `b'...'`, MAC formatting `:02X`, EtherTypes | [day-02/README.md](day-02/README.md) |
| **`day-03/`** | `arp_cache_simulator.py` | ARP tables, dictionaries as caches, broadcast vs unicast | [day-03/README.md](day-03/README.md) |
| **`day-04/`** | `subnet_calculator.py` | Packing 32-bit integers, Bitwise AND (`&`), CIDR prefixes | [day-04/README.md](day-04/README.md) |
| **`day-05/`** | `nat_simulator.py` | NAT state tables, port overloading (NAPT), private vs public | [day-05/README.md](day-05/README.md) |
| **`day-06/`** | `parse_ipv4_header.py` | `struct.unpack`, RFC 1071 ones' complement checksum, TTL | [day-06/README.md](day-06/README.md) |
| **`day-07/`** | `fragmentation_simulator.py`| MTU boundaries, 8-byte offset alignment, out-of-order reassembly | [day-07/README.md](day-07/README.md) |
| **`day-08/`** | `custom_traceroute.py` | ICMP Type 8/0/11, hop-by-hop discovery, firewall timeout | [day-08/README.md](day-08/README.md) |
| **`day-09/`** | `port_scanner_and_demux.py`| Socket 5-Tuple, demux hashing, `TIME_WAIT`, `EADDRNOTAVAIL` | [day-09/README.md](day-09/README.md) |
| **`day-10/`** | `udp_telemetry_server.py` | 8-byte UDP header, 12-byte IP Pseudo-Header, message boundaries | [day-10/README.md](day-10/README.md) |

---

## 💡 Python Networking Cheatsheet

1. **Network Byte Order (Big-Endian)**: When unpacking binary network headers, always use the `!` prefix in `struct.unpack("!...", bytes)`. This ensures consistent reading regardless of whether your computer CPU is Intel x86 or ARM!
2. **Zero Dependencies**: Everything runs using Python's built-in standard library (`struct`, `socket`, `math`, `time`). No external packages or administrator rights needed!
3. **Automated Verification**: Every script runs a self-testing validation suite at the bottom (`assert`). When you see `ALL VERIFICATIONS PASSED SUCCESSFULLY!`, you know your packet parsing conforms 100% to official RFC specifications.
