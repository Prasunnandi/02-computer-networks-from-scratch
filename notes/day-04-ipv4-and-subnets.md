# Day 04: IPv4 Addressing & CIDR Subnetting Mathematics: Bitmasks, LPM & TCAM Routing Engines

> **Zero External Dependency Guarantee**: This document is an encyclopedic, self-contained masterclass. It contains complete historical origins, 32-bit integer conversion formulas, CIDR RFC 4632 prefix matching algebra, Longest Prefix Match (LPM) TCAM hardware architectures, private RFC 1918 scopes, the 2008 YouTube BGP hijack post-mortem, and FAANG staff-level interview questions. You do NOT need any textbook or external website.

---

## 1. Executive Summary & Historical Origins

In 1981, Jon Postel published **RFC 791**, specifying the Internet Protocol Version 4 (IPv4). In IPv4, an address is a **32-bit unsigned integer** representing a unique host interface in the global internetwork topology.

To make these 32 binary bits readable to human beings, they are formatted as **Dotted-Decimal Notation**: four 8-bit octets separated by dots (e.g., `192.168.1.1`).

### The Historical Crisis: The Death of Classful Addressing
Originally, IPv4 was carved into rigid classes based on the highest-order bits:
* **Class A (`0...`)**: `/8` prefix (16,777,214 hosts per network). Only 126 Class A networks existed globally!
* **Class B (`10..`)**: `/16` prefix (65,534 hosts per network).
* **Class C (`110.`)**: `/24` prefix (254 hosts per network).

By 1992, the explosion of commercial internet connections triggered the **Routing Table Crisis**:
* If an organization needed 500 IP addresses, a Class C network (254 hosts) was too small, so they were allocated a Class B network (65,534 hosts)—**wasting 65,000 IP addresses!**
* Global core router memory tables were overflowing.

In 1993, the IETF abolished classful addressing and published **RFC 4632: Classless Inter-Domain Routing (CIDR)**, introducing arbitrary prefix bitmasking.

---

## 2. Mathematical Conversion: Dotted Decimal to 32-Bit Integer

Every IPv4 address is mathematically an integer between $0$ and $2^{32} - 1$ ($4,294,967,295$):
$$\mathbf{\text{Integer Value} = (A \cdot 2^{24}) + (B \cdot 2^{16}) + (C \cdot 2^8) + D}$$

```
WORKED CONVERSION EXAMPLE: 192.168.1.1
Octet A = 192 = 11000000_2
Octet B = 168 = 10101000_2
Octet C = 1   = 00000001_2
Octet D = 1   = 00000001_2

Mathematical Expansion:
  (192 * 16,777,216) + (168 * 65,536) + (1 * 256) + 1
= 3,221,225,472 + 11,010,048 + 256 + 1
= 3,232,235,777 (Hexadecimal: 0xC0A80101)
```

---

## 3. Subnetting Mathematics & Boolean Masking Algebra

A subnet mask is a 32-bit integer consisting of $P$ consecutive `1` bits followed by $32 - P$ consecutive `0` bits, denoted in CIDR slash notation as **/P** (e.g., `/24`).

### 3.1 The Three Fundamental Subnet Equations:
1. **Network Address (Base Route)**:
   $$\mathbf{\text{Network Address} = \text{IP Address} \ \& \ \text{Subnet Mask}}$$
2. **Broadcast Address (Direct Directed Broadcast)**:
   $$\mathbf{\text{Broadcast Address} = \text{IP Address} \ \mid \ (\sim\text{Subnet Mask})}$$
3. **Total Usable Host Addresses**:
   $$\mathbf{\text{Usable Hosts} = 2^{32 - P} - 2}$$
   *(We subtract 2 because the all-zeros host portion is reserved for the Network ID, and the all-ones host portion is reserved for the Broadcast Address).*

```
WORKED EXAMPLE: Subnet 192.168.1.75 / 26
Prefix P = 26 bits. Host bits H = 32 - 26 = 6 bits.
Subnet Mask: 11111111.11111111.11111111.11000000 = 255.255.255.192

1. Network Address:
   IP:   192.168.1.01001011 (75)
   Mask: 255.255.255.11000000 (192)
   AND:  192.168.1.01000000 = 192.168.1.64

2. Broadcast Address:
   ~Mask:0.0.0.00111111 (63)
   OR:   192.168.1.01111111 = 192.168.1.127

3. Usable Range: 192.168.1.65 through 192.168.1.126
   Total Usable Hosts = 2^6 - 2 = 64 - 2 = 62 hosts!
```

---

## 4. RFC 1918 Private Address Scopes

To delay IPv4 address exhaustion, RFC 1918 reserved three ranges for private enterprise networks that are never routable across the public global internet:

| Scope | CIDR Range | Total IP Addresses | Common Production Use Case |
| :--- | :--- | :---: | :--- |
| **24-Bit Block** | `10.0.0.0/8` | $16,777,216$ | Large enterprise datacenters, AWS VPCs, GCP networks. |
| **20-Bit Block** | `172.16.0.0/12`| $1,048,576$ | Docker container bridge networks, Kubernetes pods. |
| **16-Bit Block** | `192.168.0.0/16`| $65,536$ | Home consumer routers, office Wi-Fi networks. |

---

## 5. Longest Prefix Match (LPM) & TCAM Hardware Routing Engines

When a router receives an IP packet, its routing table may contain multiple matching routes for the destination address.
* **The Golden Invariant of IP Routing**:
  $$\mathbf{The\ router\ MUST\ forward\ based\ on\ the\ LONGEST\ PREFIX\ MATCH\ (Most\ Specific\ Route)!}$$

```
ROUTING TABLE EXAMPLE:
Destination IP of incoming packet: 10.1.2.55

Routing Table Entries:
  1. 0.0.0.0/0          -> Next Hop: Gateway A (Default Route, Prefix 0)
  2. 10.0.0.0/8          -> Next Hop: Gateway B (Prefix 8)
  3. 10.1.0.0/16         -> Next Hop: Gateway C (Prefix 16)
  4. 10.1.2.0/24         -> Next Hop: Gateway D (Prefix 24)

Match Evaluation:
All 4 routes match 10.1.2.55!
The router selects Route #4 (10.1.2.0/24) because 24 bits is the longest match!
```

### 5.1 TCAM (Ternary Content Addressable Memory):
Software tree lookups (Patricia Tries) require multiple memory accesses ($O(K)$). Modern core routers use **TCAM hardware**:
* Standard RAM stores `0` or `1`.
* TCAM stores three states: `0`, `1`, or **`X` (Don't Care / Wildcard)**!
* The entire routing table of 1,000,000 routes is evaluated in **parallel in a single clock cycle ($O(1)$)**, achieving line-rate forwarding at 400 Gbps!

---

---

## 6. Complete Python & C Implementation: High-Performance Subnet Calculator

### 6.1 Python Subnet Calculator (Bitwise Operations):
```python
import struct
import socket

def ip_to_int(ip_str: str) -> int:
    # Convert dotted decimal IPv4 string to 32-bit integer
    packed = socket.inet_aton(ip_str)
    return struct.unpack("!I", packed)[0]

def int_to_ip(ip_int: int) -> str:
    # Convert 32-bit integer to dotted decimal IPv4 string
    packed = struct.pack("!I", ip_int)
    return socket.inet_ntoa(packed)

def calculate_subnet(cidr_str: str):
    ip_str, prefix_str = cidr_str.split("/")
    prefix = int(prefix_str)
    
    ip = ip_to_int(ip_str)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    net_id = ip & mask
    broadcast = ip | (~mask & 0xFFFFFFFF)
    
    total_hosts = 2 ** (32 - prefix)
    usable_hosts = max(0, total_hosts - 2) if prefix < 31 else total_hosts
    
    first_host = net_id + 1 if prefix < 31 else net_id
    last_host = broadcast - 1 if prefix < 31 else broadcast
    
    print(f"CIDR Notation:     {cidr_str}")
    print(f"IP Address:        {ip_str} (0x{ip:08X})")
    print(f"Subnet Mask:       {int_to_ip(mask)} (/{prefix})")
    print(f"Network ID:        {int_to_ip(net_id)}")
    print(f"Broadcast Address: {int_to_ip(broadcast)}")
    print(f"Usable Host Range: {int_to_ip(first_host)} -> {int_to_ip(last_host)}")
    print(f"Total Usable Hosts: {usable_hosts:,}")

if __name__ == "__main__":
    calculate_subnet("192.168.1.75/26")
```

## 7. Real-World Production War Stories

### 6.1 War Story 1: The 2008 YouTube BGP Hijack
* **The Incident**: On February 24, 2008, the Pakistan Telecommunication Authority ordered local ISPs to block YouTube.
* **The Catastrophe**:
  - Pakistan Telecom announced a BGP route for YouTube's IP block: `208.65.153.0/24`.
  - YouTube's legitimate authoritative advertisement to the global internet was `208.65.152.0/22`.
  - Because `/24` is **more specific (longer prefix)** than `/22`, the Longest Prefix Match rule dictated that routers across the entire planet forwarded global YouTube traffic to Pakistan Telecom!
  - Pakistan Telecom's routers were instantly overwhelmed by global traffic, blackholing YouTube worldwide for 2 hours!
* **The Industry Fix**: Deployment of **RPKI (Resource Public Key Infrastructure)** and BGP Route Origin Validation (ROV).

---

## 8. Staff-Level Technical Interview Deep-Dives

### Question 1: Why does RFC 3021 allow `/31` subnets on point-to-point links without wasting IP addresses?
**Exhaustive Answer**:
* Under standard subnetting, a `/31` subnet provides $2^{32 - 31} = 2$ total IP addresses. Subtracting 2 for Network and Broadcast would leave **0 usable hosts**!
* In point-to-point router links (e.g., connecting Router A directly to Router B via a dedicated optical fiber):
  - There are no other hosts on the wire. Directed broadcast is completely unnecessary.
  - RFC 3021 explicitly standardizes that for `/31` subnets, the two addresses (e.g., `10.0.0.0` and `10.0.0.1`) are assigned directly to the two router interfaces!
  - This saves millions of valuable public IPv4 addresses across global telecommunications backbones.

---

## 9. Complete Verification Checklist (Zero Gaps)
- [ ] Convert `172.16.42.1` to a 32-bit unsigned integer and hexadecimal format.
- [ ] Calculate the Network ID, Broadcast Address, and usable host count for `10.20.30.40/28`.
- [ ] Explain how the Longest Prefix Match (LPM) rule determines routing decisions.
- [ ] Why did Pakistan Telecom's `/24` hijack YouTube's `/22` route under BGP?
