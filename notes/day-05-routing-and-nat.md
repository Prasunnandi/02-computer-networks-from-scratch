# Day 05: IPv4 Routing & Network Address Translation (NAT): Netfilter `conntrack`, NAPT & STUN/TURN Traversal

> **Zero External Dependency Guarantee**: This document is an encyclopedic, self-contained masterclass. It contains complete historical origins, the step-by-step 6-phase router packet forwarding algorithm, Linux Netfilter `conntrack` state tables, NAPT port mapping mechanics, STUN/TURN/ICE traversal topologies, production ephemeral port exhaustion post-mortems, and FAANG staff-level interview questions. You do NOT need any textbook or external website.

---

## 1. Executive Summary & Historical Origins

In 1994, K. Egevang and P. Francis published **RFC 1631**, introducing **Network Address Translation (NAT)** as a temporary short-term palliative to prolong the life of IPv4 until IPv6 could be deployed. Thirty years later, NAT remains the load-bearing pillar of the modern internet.

NAT allows thousands of devices inside an enterprise or home private network (using RFC 1918 addresses like `192.168.1.0/24`) to share a single, globally unique public IPv4 address when accessing the internet.

```
THE NETWORK ADDRESS TRANSLATION (NAPT) TOPOLOGY:
Private Subnet (192.168.1.0/24)                                  Public Internet
+-------------------------------+                                +------------------+
| Client 1: 192.168.1.10:50234  | --+                            | Web Server       |
+-------------------------------+   |   +--------------------+   | 93.184.216.34:80 |
| Client 2: 192.168.1.20:41890  | --+-> | Linux NAT Gateway  | ->+------------------+
+-------------------------------+       | Public IP:         |
                                        | 203.0.113.5        |
                                        +--------------------+
                                         (Rewrites headers &
                                          tracks state table)
```

---

## 2. The Step-by-Step 6-Phase Router Packet Forwarding Algorithm

When an IP packet arrives on a physical router interface, the router executes a deterministic 6-phase forwarding sequence before transmitting it out the egress interface:

```
THE 6-PHASE ROUTER FORWARDING PIPELINE:
[ Incoming Ethernet Frame ]
            |
            v
1. LAYER 2 INTEGRITY CHECK:
   Verify Ethernet CRC-32 (FCS). Check if Dest MAC matches router's interface.
            |
            v
2. IP HEADER INTEGRITY CHECK:
   Verify IPv4 Version == 4, IHL >= 5, and Header Checksum. Drop if corrupted!
            |
            v
3. TTL DECREMENT & EXPIRATION CHECK:
   TTL = TTL - 1.
   If TTL <= 0: Drop packet immediately! Transmit ICMP Time Exceeded (Type 11 Code 0).
            |
            v
4. CHECKSUM RECALCULATION:
   Recalculate IPv4 Header Checksum because TTL field was modified!
            |
            v
5. FORWARDING INFORMATION BASE (FIB) LOOKUP:
   Execute Longest Prefix Match (LPM) on Destination IP to select Egress Interface & Next-Hop IP.
            |
            v
6. LAYER 2 ENCAPSULATION & TRANSMISSION:
   Query ARP table for Next-Hop MAC address. Wrap packet in NEW Ethernet header and send!
```

---

## 3. Inside Linux Netfilter: Connection Tracking (`conntrack`)

NAT is fundamentally **stateful**. The Linux kernel tracks every active bidirectional connection using the Netfilter **`conntrack`** subsystem (`include/net/netfilter/nf_conntrack_tuple.h`).

```
THE 5-TUPLE CONNECTION TRACKING BIPOLAR TUPLE:
ORIGINAL DIRECTION (Client -> Server):
  (Src IP: 192.168.1.10, Dst IP: 93.184.216.34, Src Port: 50234, Dst Port: 80, Proto: TCP)
                                |
                                v
REPLY DIRECTION (Server -> Client):
  (Src IP: 93.184.216.34, Dst IP: 203.0.113.5, Src Port: 80, Dst Port: 61000, Proto: TCP)
```

### 3.1 Network Address and Port Translation (NAPT / Masquerade) Flow:
1. Client `192.168.1.10:50234` sends an HTTP SYN packet to `93.184.216.34:80`.
2. The packet hits the NAT Gateway's `POSTROUTING` Netfilter chain.
3. The NAT engine allocates an unused public ephemeral port on its public IP: `61000`.
4. It rewrites the packet:
   - Source IP: `192.168.1.10` $\to$ `203.0.113.5`
   - Source Port: `50234` $\to$ `61000`
   - Recalculates IPv4 and TCP checksums!
5. When the remote web server replies to `203.0.113.5:61000`, the NAT gateway intercepts the packet at `PREROUTING`, looks up `61000` in the `conntrack` table, rewrites Destination IP to `192.168.1.10:50234`, and forwards it to the client!

---

## 4. NAT Traversal Topologies: STUN, TURN & ICE (VoIP & WebRTC)

Because NAT gateways block unsolicited incoming packets from the public internet, peer-to-peer protocols (such as WebRTC, Zoom, and VoIP SIP) require NAT Traversal techniques.

```
THE 4 CLASSIC NAT TOPOLOGIES (RFC 3489):
+-------------------------------+---------------------------------------------------------+
| NAT Type                      | Mapping Behavior                                        |
+-------------------------------+---------------------------------------------------------+
| 1. Full Cone NAT              | External port X mapped to Internal IP:Port. Anyone can   |
|                               | send packets to port X and reach the client!            |
| 2. Restricted Cone NAT        | External port X only accepts packets from IP addresses  |
|                               | that the client has previously sent a packet to.        |
| 3. Port-Restricted Cone NAT   | External port X only accepts packets from exact IP:Port |
|                               | combinations previously contacted.                      |
| 4. Symmetric NAT (Enterprise) | Allocates a BRAND NEW external port for EVERY unique     |
|                               | destination IP:Port! Direct P2P hole punching FAILS!    |
+-------------------------------+---------------------------------------------------------+
```

### 4.1 Traversal Protocols:
* **STUN (Session Traversal Utilities for NAT, RFC 5389)**:
  Client queries a public STUN server: "What is my public reflexive IP and port?" Enables direct peer-to-peer UDP hole punching.
* **TURN (Traversal Using Relays around NAT, RFC 5766)**:
  When symmetric NAT makes direct P2P impossible, TURN acts as an in-cloud relay server, routing all voice/video data between peers.
* **ICE (Interactive Connectivity Establishment, RFC 5245)**:
  Systematically tests STUN, local host, and TURN candidates to establish the lowest-latency connection.

---

---

## 6. Complete Linux Netfilter NAT Command Reference

### 6.1 Production `iptables` NAT Rules:
```bash
# 1. Enable IP Forwarding in Linux Kernel:
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

# 2. Source NAT / Masquerade (All private traffic egressing eth0 shares public IP):
iptables -t nat -A POSTROUTING -o eth0 -s 192.168.1.0/24 -j MASQUERADE

# 3. Destination NAT / Port Forwarding (Forward public port 8080 to internal server):
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 8080 -j DNAT --to-destination 192.168.1.100:80

# 4. View Active Connection Tracking Table:
conntrack -L

# 5. Check Maximum Allowable Connections:
cat /proc/sys/net/netfilter/nf_conntrack_max
```

## 7. Real-World Production War Stories

### 5.1 War Story 1: The AWS NAT Gateway Ephemeral Port Exhaustion
* **The Incident**: During a Black Friday flash sale, an e-commerce microservice deployed on AWS ECS (in a private subnet) began failing 98% of outgoing API calls to an external credit card payment processor.
* **The Investigation**:
  - AWS CloudWatch metric: `ErrorPortAllocation` spiked to 50,000 errors/minute on the AWS NAT Gateway.
  - The microservice used a naive HTTP client library that did not implement connection pooling: every single API query created a brand new TCP connection.
* **The Physics**:
  - An AWS NAT Gateway has a single public IP, providing exactly **64,512 ephemeral ports**.
  - When a TCP connection terminates, it enters the `TIME_WAIT` state for **120 seconds** before the kernel can reuse the port.
  - At a throughput of 600 requests per second, all 64,512 ports were consumed within 100 seconds!
  - Subsequent connection attempts were dropped by the NAT gateway!
* **The Fix**:
  1. Implemented HTTP client keep-alive connection pooling (`requests.Session()`), reusing existing TCP sockets across queries.
  2. Associated multiple Elastic IP addresses with the NAT Gateway to expand the ephemeral port pool.

---

## 8. Staff-Level Technical Interview Deep-Dives

### Question 1: Why does NAT break end-to-end IP architecture and require Application Layer Gateways (ALGs)?
**Exhaustive Answer**:
* The fundamental architectural design of the Internet Protocol assumes **End-to-End Transparency**: every node possesses a unique global address, and intermediate routers only inspect Layer 3 headers.
* NAT violates Layer 3/Layer 4 encapsulation boundaries by rewriting IP addresses and TCP/UDP ports.
* Certain legacy protocols (such as FTP and SIP) transmit raw IP addresses and port numbers **inside the Layer 7 application payload**:
  - In Active FTP, the client issues the command: `PORT 192,168,1,10,195,80`.
  - The remote FTP server attempts to initiate a new TCP connection back to `192.168.1.10`—which fails because `192.168.1.10` is an unroutable private address!
* To make FTP work across NAT, the router must run an **Application Layer Gateway (ALG)**: a deep-packet inspection kernel module that parses the Layer 7 stream, rewrites the ASCII IP string inside the payload, and adjusts TCP sequence numbers accordingly!

---

## 9. Complete Verification Checklist (Zero Gaps)
- [ ] Detail the 6 phases of the router packet forwarding algorithm.
- [ ] Diagram the 5-tuple structure used by Linux Netfilter `conntrack`.
- [ ] Explain why Symmetric NAT blocks standard STUN UDP hole-punching.
- [ ] What causes NAT Gateway ephemeral port exhaustion in high-volume microservices?
