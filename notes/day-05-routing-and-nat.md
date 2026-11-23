# 🚪 Day 5: Gateways, Routers & NAT (Network Address Translation)

> **Zero External Dependency Guarantee**: This document is an exhaustive, encyclopedic masterclass. It contains complete historical context, the exact 6-step packet transformation inside a Layer 3 router, the Linux Netfilter `conntrack` connection tracking engine, AWS NAT Gateway port exhaustion post-mortems, and FAANG technical interview questions. You do NOT need any textbook or external website.

---

## 1. Executive Summary & Historical Context

By 1994, the explosive growth of the World Wide Web meant that the world's remaining unallocated IPv4 addresses would be exhausted within a few short years. While engineers began designing the next-generation protocol (IPv6 with 128-bit addresses), building and deploying a completely new internet protocol across global infrastructure would take decades.

In May 1994, K. Egevang and P. Francis published **RFC 1631**, introducing **NAT (The IP Network Address Translator)**, followed by **RFC 3022 (Traditional NAT / NAPT)**.

NAT was originally intended as a temporary emergency band-aid. Instead, it became the most ubiquitous and enduring network architecture in human history. Today, billions of home Wi-Fi routers, corporate enterprises, and cloud datacenters (AWS VPCs, Google Cloud, Azure) rely on NAT to allow millions of private internal devices to share a handful of public IP addresses.

---

## 2. Microscopic Router Internals: The 6 Steps of Packet Forwarding

When a Layer 3 Router receives an IP packet, what changes inside the packet as it moves from one interface to the next?

```
      INCOMING ON INTERFACE eth0                             OUTGOING ON INTERFACE eth1
┌──────────────────────────────────────┐               ┌──────────────────────────────────────┐
│  ETHERNET HEADER:                    │               │  ETHERNET HEADER:                    │
│  ├── Dst MAC: Router eth0 MAC        │               │  ├── Dst MAC: NEXT HOP ROUTER MAC    │ ◄── REWRITTEN!
│  └── Src MAC: Sender Host MAC        │               │  └── Src MAC: Router eth1 MAC        │ ◄── REWRITTEN!
├──────────────────────────────────────┤               ├──────────────────────────────────────┤
│  IP HEADER:                          │               │  IP HEADER:                          │
│  ├── Source IP: 192.168.1.5          │    ROUTER     │  ├── Source IP: 192.168.1.5          │ (Preserved)
│  ├── Dest IP:   8.8.8.8              │ ────────────► │  ├── Dest IP:   8.8.8.8              │ (Preserved)
│  ├── TTL:       64                   │   FORWARD     │  ├── TTL:       63                   │ ◄── DECREMENTED!
│  └── Checksum:  0x4A1F               │               │  └── Checksum:  0x4B1F               │ ◄── RECALCULATED!
├──────────────────────────────────────┤               ├──────────────────────────────────────┤
│  PAYLOAD DATA:                       │               │  PAYLOAD DATA:                       │
│  "GET /index.html"                   │               │  "GET /index.html"                   │ (Untouched)
└──────────────────────────────────────┘               └──────────────────────────────────────┘
```

### The Exact 6 Steps Executed by the Router:
1. **Layer 2 Verification & Stripping**: The router's network card verifies the incoming frame's CRC-32 checksum. If valid, it strips off the Layer 2 Ethernet header and passes the raw Layer 3 IP packet to the kernel network stack.
2. **TTL Decrement**: The router decrements the **Time-To-Live (TTL)** field in the IP header by **`1`**.
   * If the TTL reaches **`0`**, the router drops the packet and transmits an **ICMP Time Exceeded (Type 11)** packet back to the sender! (This is the exact mechanism used by `traceroute` to map internet paths).
3. **Checksum Recalculation**: Because the TTL field changed, the 16-bit **IP Header Checksum** is mathematically invalidated! The router recalculates the checksum using RFC 1071 ones' complement addition.
4. **Routing Table Lookup (LPM)**: The router consults its forwarding table using the **Longest Prefix Match (LPM)** rule to identify the next-hop IP address and outbound network interface (`eth1`).
5. **Next-Hop MAC Resolution (ARP)**: The router queries its local ARP cache table to discover the physical MAC address of the next-hop router.
6. **Layer 2 Re-Encapsulation**: The router wraps the packet in a brand new Ethernet frame:
   * **Source MAC**: The router's own outgoing interface MAC (`eth1`).
   * **Destination MAC**: The next-hop router's MAC address!
   * The frame is transmitted onto the wire!

---

## 3. The 3 Types of NAT Architecture

```
                               THE NAT FAMILY
          ┌─────────────────────────────────────────────────────────┐
          │                                                         │
          ▼                                                         ▼
     STATIC NAT (1:1)                                      NAPT / PAT (Overload)
  One Private <-> One Public                            Many Privates <-> One Public
  (Used for hosting public servers)                     (Used for homes, Wi-Fi & AWS NAT)
```

### 1. Static NAT (One-to-One)
* A dedicated public IP is permanently mapped to a single private IP.
* `192.168.1.100 <===> 203.0.113.50`
* **Use Case**: Hosting a public database or mail server inside a private subnet.

### 2. Dynamic NAT (Pool-based)
* A pool of public IPs (e.g. 10 addresses) is shared among internal computers on a first-come, first-served basis. When 10 computers are online, the 11th computer is blocked until someone logs off. Rarely used today.

### 3. Port Address Translation (PAT / NAPT / NAT Overload)
* **The Modern Standard**: Thousands of internal devices share a **single public IP address** by translating Layer 4 Transport **Port Numbers**!
* Defined in RFC 3022.

---

## 4. Kernel Architecture: Linux Netfilter & `conntrack`

On Linux (and inside every home Wi-Fi router running OpenWrt or Linux), NAT is implemented by the kernel's **Netfilter subsystem** and the **Connection Tracking (`conntrack`) engine**:

```
[ INCOMING PACKET ] ──► [ PREROUTING ] ──► [ ROUTING DECISION ] ──► [ POSTROUTING ] ──► [ WIRE ]
                             │                                            │
                     (DNAT Applied Here!)                         (SNAT Applied Here!)
```

### The In-Memory `conntrack` Tuple:
Inside `net/netfilter/nf_conntrack_core.c`, the Linux kernel maintains a bidirectional state table for every active flow:

```
TUPLE ORIGIN:  [ Src: 192.168.1.5:54321, Dst: 142.250.190.46:443, Proto: TCP ]
TUPLE REPLY :  [ Src: 142.250.190.46:443, Dst: 203.0.113.1:60001, Proto: TCP ]
STATE       :  ESTABLISHED (Timeout: 432,000 seconds / 5 days)
```

1. **SNAT (Source NAT / Masquerade)**: Applied in the `POSTROUTING` chain as packets leave the network. Rewrites the private source IP to the public IP.
2. **DNAT (Destination NAT / Port Forwarding)**: Applied in the `PREROUTING` chain as packets enter the network. Rewrites the destination IP from the public address to an internal server IP.

You can inspect your live Linux connection tracking table using:
```bash
conntrack -L
```

---

## 5. NAT Traversal: The Broken Protocols Problem (STUN, TURN, ICE)

While NAT was a genius solution for web browsing, it **breaks protocols that embed IP addresses inside their application payload**:

### Why WebRTC & VoIP (SIP) Fail on NAT:
When you make a video call, your phone sends a message saying: *"Hey friend, stream your audio directly to my microphone at `192.168.1.5:4000`!"*  
Your friend's phone across the world tries to send video to `192.168.1.5`—which is unreachable!

### The Modern Solutions:
1. **STUN (Session Traversal Utilities for NAT - RFC 5389)**:
   * Your phone queries a public STUN server on the internet: *"What is my external public IP and port as seen by the world?"*
   * The STUN server replies: *"You appear as `203.0.113.1:60001`."*
   * Your phone can now share its true reflexive public address with your friend!
2. **TURN (Traversal Using Relays around NAT - RFC 5766)**:
   * If both users are behind strict **Symmetric NATs**, direct peer-to-peer connection is mathematically impossible.
   * Traffic must be relayed through an intermediate public cloud server (TURN relay).
3. **ICE (Interactive Connectivity Establishment - RFC 8445)**:
   * The master framework used by WhatsApp, Zoom, and WebRTC: it tests direct connection, tries STUN hole punching, and falls back to TURN if all else fails.

---

## 6. Real-World Production War Story: The AWS NAT Gateway Port Exhaustion

### The Incident:
In 2022, a hyper-growth fintech microservices platform deployed on AWS Elastic Kubernetes Service (EKS) began failing randomly during peak stock market opening at 09:30 AM.  
Backend microservices attempting to make outbound HTTPS calls to third-party payment gateways suffered from **100% connection timeouts for 15 minutes**.

### What Happened Under the Hood:
1. All 40 Kubernetes worker nodes were located in private subnets, routing outbound traffic through a single **AWS NAT Gateway** with 1 public IP.
2. An upstream service had disabled HTTP Keep-Alive connection pooling, opening and closing a brand new TCP connection for every single query (10,000 requests/second).
3. When a TCP connection closes, the port enters the **`TIME_WAIT` state for 120 seconds** before the kernel reclaims it.
4. Because a single public IP has strictly **65,535 total ports**, within 10 seconds, all 65,535 ports on the AWS NAT Gateway were consumed by `TIME_WAIT` connections!
5. The NAT Gateway began silently dropping all new outgoing TCP SYN packets.

### The Production Fix:
* **Connection Pooling**: Re-use persistent TCP connections (HTTP Keep-Alive) across microservices.
* **Multi-IP NAT Gateways**: Attach multiple secondary public IPs to the NAT Gateway (each adding 55,000 available ports).

---

## 7. Staff-Level Technical Interview Deep-Dives

### Question 1: What exact mathematical fields are modified in an IP packet when passing through a standard Layer 3 router without NAT?
**Exhaustive Answer**:
* **Layer 3**:
  1. The **Time-To-Live (TTL)** field is decremented by 1.
  2. The **IP Header Checksum** is recalculated via RFC 1071 ones' complement algorithm.
  3. (The Source IP, Destination IP, and Payload remain strictly 100% untouched!).
* **Layer 2**:
  1. The entire Ethernet frame is discarded, and a **brand new Ethernet frame** is constructed with the router's egress interface MAC as Source, and the next-hop router's MAC as Destination.

### Question 2: Why do WebSockets survive NAT timeouts while idle TCP connections die?
**Exhaustive Answer**:
* Routers must discard stale entries in their NAT translation tables to free up port memory. If an idle TCP connection has no traffic for 300 seconds, the router silently deletes the NAT entry.
* If a packet later arrives from the internet, the router drops it because the table entry is gone.
* WebSockets maintain active state by transmitting periodic **WebSocket Ping/Pong heartbeat frames** (Opcode `0x9` and `0xA`) every 30 to 60 seconds, resetting the router's `conntrack` aging timer and keeping the NAT tunnel permanently alive!

---

## 8. Complete Verification Checklist (Zero Gaps)
Before marking Day 5 as completed in your tracker, verify that you can answer these without looking:
- [ ] Can you list all 6 steps executed by a Layer 3 router when forwarding an IP packet?
- [ ] How does Port Address Translation (PAT) allow 50 devices to share a single public IP simultaneously?
- [ ] What is the Linux Netfilter `conntrack` connection tracking table, and where does SNAT vs DNAT occur?
- [ ] Why does AWS NAT Gateway experience port exhaustion under heavy microservice traffic without TCP Keep-Alive?
