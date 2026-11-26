# Day 37: DNS Transport: UDP Fallback & EDNS0

## 1. Architectural Foundations: The 512-Byte UDP Barrier
RFC 1035 established UDP port 53 as the primary transport protocol for DNS:
- UDP has zero connection handshake latency ($0 	imes 	ext{RTT}$).
- It is stateless and handles millions of ephemeral transactions efficiently.
However, RFC 1035 imposed a strict architectural ceiling:
**DNS messages over standard UDP cannot exceed 512 bytes!**

Why 512 bytes?
Because in 1987, IPv4 guaranteed a minimum reassembly buffer of only 576 bytes. Subtracting the 20-byte IP header and 8-byte UDP header left exactly 548 bytes, rounded down to 512 bytes to guarantee zero IP fragmentation over any internet link.

```
+-------------------------------------------------------------------------+
| THE DNS 512-BYTE TRUNCATION & TCP FALLBACK FLOW                         |
|                                                                         |
| Client                                                 DNS Server       |
|   |                                                        |            |
|   | 1. Standard UDP Query (512-byte limit)                 |            |
|   |------------------------------------------------------->|            |
|   |                                                        | Answer is  |
|   | 2. Response with TRUNCATION BIT SET (TC=1)             | 850 bytes! |
|   |<-------------------------------------------------------|            |
|   |    (Header: TC=1, Body truncated, no answer payload)   |            |
|   |                                                        |            |
|   | 3. Client initiates TCP 3-Way Handshake (Port 53)      |            |
|   |<======================================================>|            |
|   |                                                        |            |
|   | 4. TCP Query (Length-prefixed 2-byte header)           |            |
|   |------------------------------------------------------->|            |
|   |                                                        |            |
|   | 5. Full 850-byte Response delivered over TCP stream!   |            |
|   |<-------------------------------------------------------|            |
+-------------------------------------------------------------------------+
```

---

## 2. The Truncation Bit (`TC=1`) & TCP Fallback
When a DNS server generates a response that exceeds 512 bytes:
1. The server sets the **Truncation Flag (`TC=1`)** in the DNS header.
2. The server discards the answer records and sends the truncated header back to the client.
3. The client's stub resolver detects `TC=1`, opens a **TCP connection to port 53**, and re-issues the query over TCP!
4. **Wire Format Difference over TCP**: In TCP mode, DNS messages are prefixed with a **2-byte length integer** (`uint16_t`) indicating total message byte length, because TCP is a continuous byte stream without packet boundaries.

---

## 3. RFC 6891: EDNS0 (Extension Mechanisms for DNS)
TCP fallback works, but paying a $3 	imes 	ext{RTT}$ penalty for a DNS query is too slow for modern web browsing.
With the introduction of **DNSSEC** (which adds massive 2,048-bit cryptographic signatures to DNS answers), almost all responses exceed 512 bytes!
To allow large UDP responses without falling back to TCP, RFC 2671 (updated in RFC 6891) introduced **EDNS0 (Extension Mechanisms for DNS)**.

### The `OPT` Pseudo-Resource Record
EDNS0 does not change the 12-byte DNS header; instead, it injects an **`OPT` Pseudo-Record (Type 41)** into the `ADDITIONAL` section:
- **`UDP Payload Size`**: Advertises client buffer capacity (typically **4,096 bytes** or **1,232 bytes**).
- **`Extended RCODE`**: Expands the 4-bit RCODE to 12 bits.
- **`DO` Bit (DNSSEC OK)**: Tells server to include DNSSEC RRSIG cryptographic signatures.
- **`EDNS Client Subnet (ECS - RFC 7871)`**: Forwards the client's `/24` subnet to authoritative CDN servers to optimize geolocation routing!

---

## 4. The 1,232-Byte Buffer Size Consensus (DNS Flag Day 2020)
While EDNS0 allows 4,096-byte UDP buffers, large UDP packets suffer from **IPv4 Fragmentation**.
Firewalls, NAT routers, and security appliances frequently block fragmented UDP packets (`IP_MF=1`), causing queries to hang and time out.
In 2020, major DNS providers (Google, Cloudflare, Quad9, ISC BIND, NLnet Labs) established the **DNS Flag Day 2020 consensus**:
- Maximum EDNS0 UDP buffer size is standardized to **1,232 bytes**.
- This guarantees packets fit inside standard 1,280-byte IPv6 MTU links with zero fragmentation!

---

## 5. Compilable C Program: Crafting an EDNS0 OPT Pseudo-Record
```c
/*
 * edns0_opt_builder.c - Packs an RFC 6891 EDNS0 OPT pseudo-resource record
 * Compile: gcc -O2 -Wall edns0_opt_builder.c -o edns0_opt_builder
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <arpa/inet.h>

typedef struct __attribute__((packed)) {
    uint8_t  root_name;      /* Must be 0 (Root domain) */
    uint16_t type;           /* Type 41 (OPT) */
    uint16_t udp_buf_size;   /* Client UDP buffer size (e.g. 1232) */
    uint8_t  ext_rcode;      /* Extended RCODE high bits */
    uint8_t  version;        /* EDNS version (0) */
    uint16_t flags;          /* DO bit (DNSSEC OK = 0x8000) */
    uint16_t rdlength;       /* Extension data length (0) */
} edns0_opt_rr_t;

int main(void) {
    edns0_opt_rr_t opt;
    memset(&opt, 0, sizeof(opt));
    opt.root_name    = 0;
    opt.type         = htons(41);   /* OPT */
    opt.udp_buf_size = htons(1232); /* 1232 bytes buffer */
    opt.version      = 0;
    opt.flags        = htons(0x8000); /* Set DO (DNSSEC OK) bit */
    opt.rdlength     = 0;

    printf("=========================================\n");
    printf("RFC 6891 EDNS0 OPT RECORD GENERATION\n");
    printf("=========================================\n");
    printf("Pseudo-Record Size: %zu bytes\n", sizeof(opt));
    printf("Advertised UDP Size: %u bytes\n", ntohs(opt.udp_buf_size));
    printf("DNSSEC OK (DO bit): %s\n", (ntohs(opt.flags) & 0x8000) ? "ENABLED (1)" : "DISABLED");
    printf("=========================================\n");

    return 0;
}
```

---

## 6. Production War Story: The Firewall Port 53 TCP Block Outage
In 2019, a corporate security team configured an enterprise firewall rule:
*"Allow DNS: UDP Port 53 only. Block TCP Port 53 to prevent unauthorized data exfiltration tunnels."*
Immediately after deploying DNSSEC to the company's public domain, internal employees reported that **all corporate email and VPNs broke!**
Why?
DNSSEC answers with 2048-bit RSA keys were 1,450 bytes long.
The external DNS servers truncated the responses (`TC=1`).
When client resolvers attempted to fall back to TCP port 53, the firewall dropped the TCP SYN packets!
The resolvers waited 15 seconds for timeouts and returned `SERVFAIL`.
Rule of thumb: **DNS is NOT UDP only! Both UDP and TCP on Port 53 are strictly mandatory per RFC 7766!**
---

## 7. Binary Layout of the EDNS0 OPT Header (RFC 6891)
Let's dissect the exact 11-byte binary structure of the EDNS0 `OPT` pseudo-record:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          NAME (Root domain = 0x00)            |   TYPE (41)   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       UDP Payload Size (e.g. 1232 or 4096)    | EXT-RCODE |VER|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|DO|                    Z (Reserved = 0)        |    RDLEN (0)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Notice:
- `EXT-RCODE`: High 8 bits of RCODE (combines with header RCODE to form 12-bit error codes like `BADVERS`).
- `VER`: EDNS version (currently `0`).
- `DO` (Bit 15 of flags): **DNSSEC OK**. When set by client, authoritative server is required to include `RRSIG`, `DNSKEY`, and `NSEC` records in response.

---

## 8. TCP Connection Pooling & Pipeline Multiplexing (RFC 7766)
When DNS operates over TCP:
- RFC 7766 mandates that resolvers maintain persistent TCP connections and pipeline queries.
- A client can blast 50 queries over a single TCP socket simultaneously without waiting for responses in lockstep.
- The 16-bit Transaction ID (`ID`) enables matching out-of-order responses across the TCP stream.
---

## 9. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Test EDNS0 buffer negotiation and verify DO bit:
dig example.com +dnssec +bufsize=1232

# Force a DNS query over TCP port 53:
dig +tcp example.com A

# Force a large ANY query and observe truncation (TC=1) and automatic TCP retry:
dig +ignore large-record.dnssec-tools.org ANY

# Wireshark display filter for truncated DNS packets:
# dns.flags.truncated == 1 || tcp.port == 53
```

---

## 10. Production Verification Checklist & Architecture Audit
- [ ] Verify enterprise firewalls permit BOTH UDP and TCP traffic on Port 53 per RFC 7766.
- [ ] Enforce standard EDNS0 buffer size of 1,232 bytes (DNS Flag Day 2020) to prevent IPv4 packet fragmentation drops.
- [ ] Ensure recursive resolvers maintain persistent TCP connection pools with idle timeouts of at least 10 to 60 seconds.
---

## 11. Mathematical & Algorithmic Foundations: MTU Path Traversal & Truncation Math
Why is 1,232 bytes the optimal EDNS0 buffer size?
Let's calculate the exact packet math:
- Minimum IPv6 MTU guaranteed by RFC 8200: **1,280 bytes**.
- IPv6 Header: **40 bytes**.
- UDP Header: **8 bytes**.
- Maximum Payload Space:
$$1280 - 40 - 8 = 1232 	ext{ bytes!}$$
By setting EDNS0 buffer size to exactly 1,232 bytes, a DNS server guarantees that even over IPv6 networks with minimum MTU links, **zero packet fragmentation can ever occur**!
---

## 12. Production DNS Security Hardening Matrix & Standards
1. **Firewall & NAT Gateway Configuration for Port 53**:
   - Ensure stateful firewalls do not drop TCP port 53 packets or enforce aggressive 5-second TCP idle timeouts on DNS.
   - For Linux servers handling high DNS traffic, ensure conntrack limits are expanded: `sysctl -w net.netfilter.nf_conntrack_max=1048576`.
2. **RFC Compliance Matrix**:
   - RFC 1035 Section 4.2.1: UDP Usage & 512-Byte Limit
   - RFC 6891: Extension Mechanisms for DNS (EDNS(0))
   - RFC 7766: DNS Transport over TCP - Implementation Requirements
   - RFC 7871: Client Subnet in DNS Queries (ECS)
---

## 13. High-Performance TCP Socket Tuning for DNS Servers
When operating an authoritative nameserver handling high volumes of TCP fallback traffic (e.g. during large zone transfers or heavy DNSSEC validation):
In `/etc/sysctl.conf`:
```bash
# Expand TCP listen backlog
net.core.somaxconn = 4096

# Enable TCP Fast Open for DNS clients to eliminate handshake RTT
net.ipv4.tcp_fastopen = 3

# Reduce TCP keepalive probe intervals to reclaim abandoned client sockets
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_keepalive_probes = 5
```
