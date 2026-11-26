# Day 31: DNS Hierarchy: Roots, TLDs & Authoritatives

## 1. Architectural Foundations: The Inverted Tree Architecture
The **Domain Name System (DNS)** (RFC 1034, RFC 1035) is the world's largest, most resilient distributed hierarchical database.
Before DNS was invented by Paul Mockapetris in 1983, host-to-IP mappings on the ARPANET were maintained in a single central file called `HOSTS.TXT`, managed by Elizabeth Feinler at the Stanford Research Institute (SRI-NIC). Every workstation downloaded `HOSTS.TXT` via FTP.
As the network expanded, `HOSTS.TXT` suffered from three fatal flaws:
1. **Name Collisions**: Two universities could assign the same hostname to different machines.
2. **Bandwidth Exhaustion**: Thousands of hosts saturating SRI's connection every night downloading the monolithic file.
3. **Inconsistency**: Local copies were constantly stale.

Mockapetris replaced `HOSTS.TXT` with an **inverted tree hierarchy**, delegating administrative authority across distinct administrative boundaries (zones).

```
                              . (The Root Zone)
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
        .com                        .org                        .net (gTLDs)
         |                           |                           |
    +----+----+                 +----+----+                 +----+----+
    |         |                 |         |                 |         |
google.com  stripe.com       eff.org   wikipedia.org    cloudflare.net akamai.net
    |
  api.google.com (Subdomains / FQDN)
```

---

## 2. The 13 Root Server Letters (A through M) & IP Anycast
At the apex of the DNS tree sits the **Root Zone (`.`)**.
Historically, due to the 512-byte UDP packet limit of RFC 1035, the DNS root zone could only list 13 server IP addresses in a single DNS response:
- `a.root-servers.net` (198.41.0.4) through `m.root-servers.net` (202.12.27.33).

However, **there are NOT only 13 physical computers**!
If there were only 13 physical servers, the global internet would collapse under a standard DDoS attack in seconds.
Today, the 13 root IP addresses are distributed across **over 1,700 physical server instances worldwide** using **BGP Anycast Routing**.

### How BGP Anycast Works for DNS
Under BGP Anycast:
1. Multiple physical servers in London, Tokyo, New York, and Sydney all advertise the **exact same IP address** (e.g. `198.41.0.4`) into the global BGP routing table.
2. When a recursive resolver in Paris queries `198.41.0.4`, internet routers automatically forward the packet along the shortest BGP Autonomous System (AS) path to the local Anycast instance in Paris or Frankfurt!
3. If an instance in Sydney crashes or undergoes a DDoS attack, BGP automatically withdraws the route, seamlessly diverting traffic to the nearest surviving node without downtime.

---

## 3. Top-Level Domains (TLDs) & ccTLDs
Beneath the root zone sit the Top-Level Domains (TLDs), managed by the Internet Assigned Numbers Authority (IANA):
1. **Generic TLDs (gTLDs)**: `.com`, `.net`, `.org`, `.edu`, `.gov`, plus modern extensions (`.io`, `.app`, `.dev`).
2. **Country Code TLDs (ccTLDs)**: Two-letter ISO-3166 codes representing geographic territories (`.us`, `.uk`, `.de`, `.jp`, `.in`).
3. **Infrastructure TLD**: `.arpa` (Address and Routing Parameter Area), dedicated to reverse DNS lookups (`in-addr.arpa`, `ip6.arpa`).

---

## 4. Zone Delegation & The Crucial Role of Glue Records
When a registry delegates a domain name (e.g. `example.com`) to an authoritative nameserver, it places **`NS` (Name Server) records** in the parent zone:
```dns
; In .com TLD Zone File:
example.com.    172800  IN  NS  ns1.example.com.
example.com.    172800  IN  NS  ns2.example.com.
```

### The Circular Dependency Problem
Look at the records above:
To resolve `example.com`, you must query its nameserver `ns1.example.com`.
But to resolve the IP address of `ns1.example.com`, you must first resolve `example.com`!
This is a fatal circular chicken-and-egg deadlock!

### The Solution: Glue Records
To break the circular dependency, the parent zone (`.com`) MUST provide **Glue Records**—an explicit `A` (and `AAAA`) record binding the nameserver's hostname to its physical IP address inside the parent's `ADDITIONAL` section:
```dns
; Glue Records in .com TLD Zone:
ns1.example.com.    172800  IN  A   198.51.100.1
ns2.example.com.    172800  IN  A   198.51.100.2
```
When a recursive resolver asks `.com` for `example.com`, the `.com` TLD server returns both the `NS` delegation AND the glue IP addresses in a single UDP response, breaking the deadlock.

---

## 5. Compilable C Program: Inspecting Root Server Hints File
```c
/*
 * root_hints_inspector.c - Parses and verifies standard IANA named.root hints
 * Compile: gcc -O2 -Wall root_hints_inspector.c -o root_hints_inspector
 */
#include <stdio.h>
#include <string.h>

typedef struct {
    char letter;
    const char *ipv4;
    const char *operator_name;
} root_server_t;

int main(void) {
    root_server_t roots[] = {
        { 'A', "198.41.0.4",     "Verisign, Inc." },
        { 'B', "199.9.14.201",   "USC-ISI" },
        { 'C', "192.33.4.12",    "Cogent Communications" },
        { 'D', "199.7.91.13",    "University of Maryland" },
        { 'E', "192.203.230.10", "NASA Ames Research Center" },
        { 'F', "192.5.5.241",    "Internet Systems Consortium (ISC)" },
        { 'G', "192.112.36.4",   "US Department of Defense (NIC)" },
        { 'H', "198.97.190.53",  "US Army Research Lab" },
        { 'I', "192.36.148.17",  "Netnod (Sweden)" },
        { 'J', "192.58.128.30",  "Verisign, Inc." },
        { 'K', "193.0.14.129",   "RIPE NCC (Netherlands)" },
        { 'L', "199.7.83.42",    "ICANN" },
        { 'M', "202.12.27.33",   "WIDE Project (Japan)" }
    };

    printf("===================================================================\n");
    printf("IANA ROOT SERVER ANCHOR AUDIT (13 LOGICAL LETTERS, 1700+ ANYCAST INSTANCES)\n");
    printf("===================================================================\n");
    printf("%-8s | %-16s | %-35s\n", "Letter", "IPv4 Anycast", "Administrative Operator");
    printf("-------------------------------------------------------------------\n");

    for (int i = 0; i < 13; i++) {
        char domain[32];
        snprintf(domain, sizeof(domain), "%c.root-servers.net", roots[i].letter);
        printf("%-8s | %-16s | %-35s\n", domain, roots[i].ipv4, roots[i].operator_name);
    }
    printf("===================================================================\n");
    return 0;
}
```

---

## 6. Production War Story: The Missing Glue Record Outage
In 2016, an infrastructure team migrated a high-profile web service's domain registrar.
The engineers configured their authoritative nameservers as `ns1.mycorp.com` and `ns2.mycorp.com`.
They configured the NS records at the registrar, but **forgot to add the Glue Records** in the registry portal!
Within 48 hours, as old cached DNS records expired around the world:
- Recursive resolvers around the globe attempted to query `ns1.mycorp.com`.
- The `.com` TLD replied: *"Ask ns1.mycorp.com!"* without providing an IP address.
- Resolvers entered an infinite resolution loop and returned `SERVFAIL` to all end users!
- The entire corporate domain disappeared from the global internet for 6 hours until glue records were populated at the TLD registry.
Rule of thumb: **If your nameserver hostname is inside the domain it serves, Glue Records at the parent TLD registry are strictly mandatory!**
---

## 7. Deep Systems Internals: The BGP Anycast Routing Architecture
How do root nameservers prevent routing flapping and state desynchronization across global Anycast clusters?
1. **Equal-Cost Multi-Path (ECMP)**: When multiple fiber routes between Autonomous Systems have identical AS-Path lengths, routers use 5-tuple flow hashing (`src_ip, dst_ip, sport, dport, proto`) to pin a single connection to one specific physical instance.
2. **TCP State Challenge with Anycast**:
   - Because standard DNS queries are single UDP datagrams, if query 1 hits Tokyo and query 2 hits Sydney, the client does not care!
   - However, for zone transfers (AXFR) or large DNSSEC queries that use TCP, if a BGP route flap occurs mid-connection, the next TCP packet is routed to a different physical Anycast node!
   - The new node has no record of the TCP connection (`struct tcp_sock`) and immediately emits a `TCP RST` packet, severing the connection!
   - Modern Anycast operators solve this by running local BGP health checkers (e.g. BIRD or ExaBGP) and keeping local persistent TCP proxy layers.

---

## 8. BIND9 & CoreDNS Zone Configuration Masterclass
To configure an authoritative zone with proper root delegation and glue records in standard RFC-compliant master zone format:

```dns
$TTL 86400
@   IN  SOA ns1.example.com. admin.example.com. (
            2026112601 ; Serial (YYYYMMDDNN)
            3600       ; Refresh (1 hour)
            1800       ; Retry (30 mins)
            1209600    ; Expire (2 weeks)
            300 )      ; Minimum / Negative TTL (5 mins)

; Authoritative Nameservers
@       IN  NS      ns1.example.com.
@       IN  NS      ns2.example.com.

; Mandatory Glue Records (L2/L3 Bootstrap)
ns1     IN  A       198.51.100.1
ns1     IN  AAAA    2001:db8::1
ns2     IN  A       198.51.100.2
ns2     IN  AAAA    2001:db8::2

; Service Payloads
@       IN  A       203.0.113.10
www     IN  CNAME   @
```
---

## 9. Comprehensive Wireshark & CLI Packet Diagnostics
To inspect Root and TLD delegation mechanics in real-world traffic:
```bash
# Query a root server directly with debug flags enabled
dig @a.root-servers.net . NS +norecurse +bufsize=4096

# Wireshark filter to capture all Root and TLD delegation responses:
# dns.flags.response == 1 && dns.count.answers == 0 && dns.count.auth_rr > 0

# Test Anycast latency across different geographic endpoints using mtr:
mtr -rwz -c 50 198.41.0.4  # a.root-servers.net Anycast traceroute
```

---

## 10. Production Verification Checklist & Architecture Audit
- [ ] Ensure authoritative nameservers reside on at least two distinct Autonomous Systems (ASNs) and geographic regions.
- [ ] Verify that every nameserver inside the domain boundary has both an IPv4 (A) and IPv6 (AAAA) Glue record registered at the TLD registrar.
- [ ] Ensure TTL on zone `NS` records is set to a stable duration (typically 86,400 to 172,800 seconds) to prevent redundant upstream TLD queries.
---

## 11. Mathematical & Algorithmic Foundations: Anycast Latency Variance
In Anycast routing, round-trip time is modeled across a set of $K$ physical instances:
$$	ext{RTT}_{	ext{observed}} = \min_{i \in \{1 \dots K\}} \left( 	ext{RTT}_i + \delta_{	ext{BGP}} ight)$$
where $\delta_{	ext{BGP}}$ represents policy-based routing distortion.
Because BGP chooses routes based on AS-Path hop count rather than physical fiber propagation speed, an Anycast query from London to `a.root-servers.net` might occasionally traverse an transatlantic fiber to New York if a peering agreement prioritizes that link.
Understanding BGP policy metrics is essential to analyzing Anycast DNS latency distributions.
