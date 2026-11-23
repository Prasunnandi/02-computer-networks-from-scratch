# 02-computer-networks-from-scratch

> **Curriculum Track**: Pair 1 (Days 1 - 100) [Secondary Track]  
> **Topic**: Physical/Data Link, IP, Sockets, TCP 3-Way Handshake, DNS, HTTP  
> **Target**: 100 Days | Zero Knowledge Gap | Self-Contained Textbook & Simulation Suite

---

## 📌 Executive Summary
Understand computer networks from physical bits to the application layer. Build raw socket clients, implement protocols, and inspect packet flows. 100% self-contained study material with bit-exact frame layouts, RFC protocol standards, mathematical proofs, production war stories, and working code simulation labs.

---

## 🎯 100-Day Milestones
- [x] **Milestone 1 (Days 1–5)**: Physical Transmission, Ethernet Frames, CRC-32 Math, ARP & Subnet Masking
- [x] **Milestone 2 (Days 6–10)**: IPv4 Header Anatomy, Checksum Math, Fragmentation/PMTUD, ICMP & UDP
- [ ] **Milestone 3 (Days 11–25)**: TCP 3-Way Handshake, Sequence/ACK Numbers, Sliding Window & Congestion Control
- [ ] **Milestone 4 (Days 26–50)**: DNS Protocol from Scratch, TLS 1.3 Cryptography & HTTP/1.1 vs HTTP/2
- [ ] **Milestone 5 (Days 51–100)**: Raw Socket Sniffing (`libpcap`), Custom Web Server, HTTP/3 (QUIC) & BGP Routing

---

## 📚 Curriculum Index (Days 1 – 10)

| Day | Topic | Textbook Notes | Hands-on Simulation Lab | Verification Status |
| :---: | :--- | :--- | :--- | :---: |
| **01** | Physical Layer (Bits, Baud Rate, Nyquist-Shannon Theorem, Signal-to-Noise) | [day-01-bits-bytes-and-signals.md](notes/day-01-bits-bytes-and-signals.md) | [binary_signal_sim.py](code/day-01/binary_signal_sim.py) | ✅ Verified |
| **02** | Ethernet Framing (Preamble, MAC Addresses, 64-Byte Min Frame, CRC-32) | [day-02-ethernet-and-mac-framing.md](notes/day-02-ethernet-and-mac-framing.md) | [parse_ethernet_frame.py](code/day-02/parse_ethernet_frame.py) | ✅ Verified |
| **03** | ARP Protocol (28-Byte Packet, Broadcast vs Unicast, Poisoning Defense) | [day-03-arp-protocol-and-cache.md](notes/day-03-arp-protocol-and-cache.md) | [arp_cache_simulator.py](code/day-03/arp_cache_simulator.py) | ✅ Verified |
| **04** | IPv4 Addressing & Subnetting (CIDR, Bitwise Netmasks, Network/Broadcast) | [day-04-ipv4-addressing-and-subnets.md](notes/day-04-ipv4-addressing-and-subnets.md) | [subnet_calculator.py](code/day-04/subnet_calculator.py) | ✅ Verified |
| **05** | Routing & NAT (Next-Hop Routing Tables, Conntrack, Port Overload NAPT) | [day-05-routing-tables-and-nat.md](notes/day-05-routing-tables-and-nat.md) | [nat_simulator.py](code/day-05/nat_simulator.py) | ✅ Verified |
| **06** | IPv4 Header Anatomy (IHL, TTL Loop Prevention, 16-Bit Ones' Complement) | [day-06-ipv4-header-anatomy.md](notes/day-06-ipv4-header-anatomy.md) | [parse_ipv4_header.py](code/day-06/parse_ipv4_header.py) | ✅ Verified |
| **07** | IP Fragmentation (MTU vs MSS, DF/MF Flags, 8-Byte Offset Units, PMTUD) | [day-07-ip-fragmentation-and-mtu.md](notes/day-07-ip-fragmentation-and-mtu.md) | [fragmentation_simulator.py](code/day-07/fragmentation_simulator.py) | ✅ Verified |
| **08** | ICMP Protocol (RFC 792 Echo Request/Reply, Traceroute TTL Expiry) | [day-08-icmp-ping-and-traceroute.md](notes/day-08-icmp-ping-and-traceroute.md) | [custom_traceroute.py](code/day-08/custom_traceroute.py) | ✅ Verified |
| **09** | Transport Layer Foundations (Port Multiplexing, Socket 5-Tuple, Ephemeral Exhaustion) | [day-09-transport-ports-and-demux.md](notes/day-09-transport-ports-and-demux.md) | [port_scanner_and_demux.py](code/day-09/port_scanner_and_demux.py) | ✅ Verified |
| **10** | UDP Protocol Internals (RFC 768 8-Byte Header, Pseudo-Header Checksum, Boundaries) | [day-10-udp-internals-and-sockets.md](notes/day-10-udp-internals-and-sockets.md) | [udp_telemetry_server.py](code/day-10/udp_telemetry_server.py) | ✅ Verified |

---

## 🚀 Daily Study Rule ("Side-by-Side Mode")
- Work on this repository strictly in tandem with its complementary pair repository: [`01-linux-cli-and-posix-mastery`](https://github.com/Prasunnandi/01-linux-cli-and-posix-mastery).
- Block A: Primary Systems (Linux) ~2 hours.
- Block B: Secondary Track (Computer Networks) ~1.5 hours.
- Complete the daily hands-on lab before moving to the next day.
