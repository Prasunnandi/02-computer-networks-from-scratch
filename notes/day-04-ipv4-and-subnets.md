# 🔢 Day 4: IPv4 Addressing, CIDR & Subnetting Mathematics

> **Zero External Dependency Guarantee**: This document is an exhaustive, encyclopedic masterclass. It contains complete historical context, binary bitwise derivations, TCAM hardware lookup mechanics, the famous 2008 YouTube global BGP hijacking post-mortem, and FAANG technical interview questions. You do NOT need any textbook or external website.

---

## 1. Executive Summary & Historical Context

In 1981, Jon Postel published **RFC 791**, formalizing the **IPv4 protocol**. At the time, Postel and DARPA assumed that a 32-bit address space—providing **4,294,967,296 ($2^{32}$) addresses**—would be more than enough to connect every university computer in existence for centuries.

However, the early internet used an inflexible system called **Classful Networking**:
* **Class A (`/8`)**: Allocated $16,777,216$ addresses to a single entity (IBM, Apple, MIT, Ford each got an entire Class A block!).
* **Class B (`/16`)**: Allocated $65,536$ addresses.
* **Class C (`/24`)**: Allocated only $256$ addresses.

If a company needed 500 IP addresses, Class C was too small ($256$), so they were granted an entire Class B block ($65,536\text{ IPs}$)—**wasting over 65,000 public IP addresses in a single grant**!

By 1993, global routing tables were exploding, and the internet was on the verge of running out of addresses. In response, Vince Fuller and team authored **RFC 1519**, introducing **CIDR (Classless Inter-Domain Routing)** and **VLSM (Variable Length Subnet Masking)**, abolishing fixed classes and saving the internet.

---

## 2. Mathematical Foundations: The Binary Anatomy of IPv4

Every IPv4 address is an unsigned **32-bit integer** ($4\text{ Bytes}$).  
To make it readable for humans, we divide the 32 bits into **four 8-bit octets** separated by decimal points:

$$\text{192.168.1.45} \Longleftrightarrow \mathbf{11000000 . 10101000 . 00000001 . 00101101}$$

### Converting an IP Address to an Integer in Code:
Because an IP address is a 32-bit integer, you can convert it to a raw number using bit-shifts:

$$\text{IP Integer} = (\text{Octet}_1 \ll 24) \ | \ (\text{Octet}_2 \ll 16) \ | \ (\text{Octet}_3 \ll 8) \ | \ \text{Octet}_4$$

For `192.168.1.45`:
$$\text{Integer} = (192 \times 2^{24}) + (168 \times 2^{16}) + (1 \times 2^8) + 45 = \mathbf{3,232,235,821}$$

---

## 3. The Bitwise Logic of Subnetting

How does a router determine whether a packet is for a computer inside the local office or across the globe?  
It executes a hardware-level **Bitwise AND ($\&$)** operation between the IP address and the Subnet Mask!

```
                               THE BITWISE AND GATE
                     ┌────────────────────────────────────────┐
                     │          0 & 0 = 0    1 & 0 = 0        │
                     │          0 & 1 = 0    1 & 1 = 1        │
                     └────────────────────────────────────────┘
```

### Step-by-Step Mathematical Derivation for `192.168.1.45/26`:
A `/26` subnet mask has twenty-six `1` bits followed by six `0` bits ($32 - 26 = 6$).

```
IP Address:     11000000.10101000.00000001 . 00101101   (192.168.1.45)
Subnet Mask:    11111111.11111111.11111111 . 11000000   (255.255.255.192 = /26)
                ──────────────────────────────────────────────────────────
Bitwise AND (&):11000000.10101000.00000001 . 00000000   ==> 192.168.1.0 (NETWORK ID!)
```

### Calculating the Broadcast Address (Bitwise OR with Wildcard Mask):
The **Wildcard Mask** is the exact bitwise inversion of the subnet mask ($\sim\text{Mask}$):
```
Wildcard Mask:  00000000.00000000.00000000 . 00111111   (0.0.0.63)
Network ID:     11000000.10101000.00000001 . 00000000   (192.168.1.0)
                ──────────────────────────────────────────────────────────
Bitwise OR (|): 11000000.10101000.00000001 . 00111111   ==> 192.168.1.63 (BROADCAST ID!)
```

### The Exact Range for `/26`:
* **Network ID (Reserved)**: `192.168.1.0`
* **First Usable Host**: `192.168.1.1`
* **Last Usable Host**: `192.168.1.62`
* **Broadcast ID (Reserved)**: `192.168.1.63`
* **Total Usable Devices**: $2^6 - 2 = \mathbf{62\text{ devices}}$.

---

## 4. Hardware Routing: TCAM & The Longest Prefix Match (LPM)

How do core internet backbone routers (Cisco, Juniper) evaluate millions of routing table rules for **100 million packets every second**?

They do not use standard CPU loops or binary trees. They use specialized hardware chips called **TCAM (Ternary Content Addressable Memory)**!

```
                                TCAM HARDWARE LOOKUP
┌───────────────────────────────────────────────────────────────────────────────┐
│ In standard RAM: You provide an Address ──────► Chip returns Data             │
│ In TCAM memory:  You provide the IP     ──────► Chip returns Egress Port!     │
└───────────────────────────────────────────────────────────────────────────────┘

TCAM supports 3 states: 0, 1, and X ("Don't Care" / Wildcard):
Routing Table Entries in TCAM:
├── Entry 1: 192.168.0.0/16 ──► [11000000.10101000.XXXXXXXX.XXXXXXXX] -> Port 1
├── Entry 2: 192.168.1.0/24 ──► [11000000.10101000.00000001.XXXXXXXX] -> Port 2
└── Entry 3: 0.0.0.0/0      ──► [XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX] -> Default Gateway
```

### The Longest Prefix Match (LPM) Rule:
If a packet arrives for `192.168.1.45`, it matches both Entry 1 (`/16`) and Entry 2 (`/24`).  
The universal law of internet routing is: **The router MUST always forward the packet to the LONGEST (most specific) prefix match!**  
In this case, `/24` is longer and more specific than `/16`, so the packet is forwarded out of **Port 2**.  
In TCAM hardware, this evaluation occurs in **a single clock cycle (under 2 nanoseconds)**!

---

## 5. Special IPv4 Addresses Every Engineer Must Know

| IP Range | Subnet Prefix | Formal Definition | Purpose & Behavior |
| :---: | :---: | :--- | :--- |
| **`127.0.0.0/8`** | `/8` | **Loopback** | Communicates with the local operating system kernel without transmitting any electrical signal to the physical network card! |
| **`169.254.0.0/16`** | `/16` | **Link-Local (APIPA)** | Automatically assigned by the OS when your computer fails to reach a DHCP server on the local Wi-Fi. Non-routable! |
| **`0.0.0.0/32`** | `/32` | **Unspecified / Current** | Used by a client as its source IP before it has been assigned an address during DHCP negotiation. |
| **`0.0.0.0/0`** | `/0` | **Default Route** | In a routing table, represents the "catch-all" path to the entire public internet. |
| **`255.255.255.255`** | `/32` | **Limited Broadcast** | Broadcasts to every device on the physical local wire. Routers will **never** forward this packet across boundaries! |

---

## 6. Real-World Production War Story: The 2008 YouTube BGP Hijack

### The Incident:
On February 24, 2008, the government of Pakistan ordered state telecom provider PTCL to block access to YouTube nationwide.  
A network engineer at PTCL configured a null-route for YouTube's IP block: `208.65.153.0/24`.

### What Happened Under the Hood:
1. YouTube owned and announced the global CIDR block: **`208.65.152.0/22`**.
2. PTCL accidentally leaked its localized `/24` route into global BGP routing tables via its upstream provider, PCCW.
3. Because **`/24` is more specific than `/22`**, the Longest Prefix Match (LPM) rule forced every internet router worldwide to prefer the `/24` route announced by Pakistan!
4. Within **3 minutes**, **all worldwide traffic to YouTube** was diverted to Pakistan Telecom's small routers, crashing them instantly and causing a **2-hour global outage for YouTube worldwide**!

### The Engineering Takeaway:
* Understanding prefix length (`/24` vs `/22`) is a matter of critical global infrastructure security.
* Modern networks use **ROA (Route Origin Authorization)** and **RPKI cryptographic signatures** to prevent invalid route announcements.

---

## 7. Staff-Level Technical Interview Deep-Dives

### Question 1: Why does `127.0.0.1` never leave the operating system?
**Exhaustive Answer**:
* When a socket writes to any IP in the `127.0.0.0/8` block, the Linux kernel's Layer 3 IP routing subsystem detects the loopback destination (`ip_route_output_key()`).
* The kernel bypasses the physical network device driver queue entirely. It immediately places the packet into the in-memory **Loopback Device Driver (`lo`)** receive queue.
* The packet never touches physical Ethernet framing, MAC resolution, or the physical NIC hardware. It executes entirely in RAM as a kernel-to-kernel memory transfer.

### Question 2: Can a subnet mask have non-contiguous bits (e.g. `255.0.255.0`)?
**Exhaustive Answer**:
* RFC 950 historically allowed non-contiguous subnet masks, but **RFC 1519 (CIDR) strictly abolished them**.
* All modern routing hardware requires subnet masks to be contiguous strings of `1`s followed by `0`s. This allows CIDR prefix notation (`/N`) to represent any mask with a single integer, which is mathematically required for TCAM binary trie lookups.

---

## 8. Complete Verification Checklist (Zero Gaps)
Before marking Day 4 as completed in your tracker, verify that you can answer these without looking:
- [ ] Can you convert `172.16.8.99/26` to its exact Network ID, Broadcast ID, and usable host count by hand?
- [ ] What is the Longest Prefix Match (LPM) rule, and how does TCAM hardware execute it in $O(1)$ time?
- [ ] What is the difference between Link-Local (`169.254.x.x`) and Private IP (`192.168.x.x`) ranges?
- [ ] How did Pakistan Telecom accidentally hijack YouTube globally using a more specific `/24` prefix?
