# Day 35: Recursive vs Iterative Resolution Mechanics

## 1. Architectural Foundations: The Two Modes of DNS Resolution
When a web browser requests `www.wikipedia.org`, it triggers a multi-stage lookup process involving two fundamentally different query models:
1. **Recursive Resolution**: *"Do all the work for me and return the final IP address (or error)!"*
   - Used between the client stub resolver (your laptop) and the recursive DNS server (e.g. `8.8.8.8`, `1.1.1.1`, or local ISP resolver).
2. **Iterative Resolution**: *"I cannot give you the final answer, but here is a referral to another nameserver who knows more than I do!"*
   - Used between the recursive resolver and the authoritative hierarchy (Root $	o$ TLD $	o$ Authoritative).

```
+-------------------------------------------------------------------------+
| RECURSIVE VS ITERATIVE RESOLUTION WALKTHROUGH                           |
|                                                                         |
| [Client Stub]                                                           |
|       |                                                                 |
|       | 1. Query "www.wikipedia.org" (RD=1: Recursive)                  |
|       v                                                                 |
| [Recursive Resolver (e.g. 8.8.8.8)]                                     |
|       |                                                                 |
|       | 2. Iterative Query: "www.wikipedia.org" (RD=0)                  |
|       +---------------------------------------------> [Root Server .]   |
|       | 3. Referral: "I don't know, ask .org TLD!" <---+ (Returns NS)   |
|       |                                                                 |
|       | 4. Iterative Query: "www.wikipedia.org" (RD=0)                  |
|       +---------------------------------------------> [.org TLD Server] |
|       | 5. Referral: "Ask ns0.wikimedia.org!" <--------+ (Returns NS)   |
|       |                                                                 |
|       | 6. Iterative Query: "www.wikipedia.org" (RD=0)                  |
|       +---------------------------------------------> [wikimedia.org]   |
|       | 7. Authoritative Answer: 208.80.154.224 <-----+ (AA=1, A=IP)    |
|       |                                                                 |
|       v 8. Final Answer Delivered to Client!                            |
| [Client Stub]                                                           |
+-------------------------------------------------------------------------+
```

---

## 2. The Mechanics of Referral Chasing
When an iterative query arrives at a non-authoritative server:
1. The server sets return code `status: NOERROR`.
2. `ANCOUNT` is `0` (Zero answers).
3. `NSCOUNT` $> 0$ (Lists delegated nameservers in the `AUTHORITY` section).
4. `ARCOUNT` $> 0$ (Provides Glue records in the `ADDITIONAL` section if available).

The recursive resolver extracts the nameservers from the authority section, picks the nameserver with the lowest measured round-trip time (`SRTT`), and repeats the query.

---

## 3. The Bailiwick Rules: Preventing Cross-Domain Poisoning
What stops a malicious nameserver for `evil.com` from including the following record in its response?
```dns
; In response from ns.evil.com:
evil.com.       3600  IN  NS  ns.evil.com.
google.com.     3600  IN  A   6.6.6.6   <-- MALICIOUS POISONING ATTEMPT!
```
To protect the internet, all recursive resolvers enforce **Bailiwick Rules** (RFC 2181):
- A nameserver is only permitted to provide authoritative answers or referrals for domain names that fall **strictly within its own administrative tree (its bailiwick)**!
- Because `google.com` is outside the domain tree of `evil.com`, the recursive resolver discards the `google.com` record as "out-of-bailiwick", completely neutralizing the hijacking attempt.

---

## 4. Compilable C Program: Simulating Iterative Referral Chasing
```c
/*
 * iterative_resolver_sim.c - Simulates iterative DNS referral logic
 * Compile: gcc -O2 -Wall iterative_resolver_sim.c -o iterative_resolver_sim
 */
#include <stdio.h>
#include <string.h>

typedef struct {
    const char *zone_name;
    const char *next_referral_ns;
    const char *final_ip;
} mock_dns_db_t;

int main(void) {
    mock_dns_db_t hierarchy[] = {
        { ".",           "a0.org.afilias-nst.info (TLD .org)", NULL },
        { ".org",        "ns0.wikimedia.org (Authoritative)",  NULL },
        { "wikipedia.org", NULL,                               "208.80.154.224" }
    };

    const char *target = "www.wikipedia.org";
    printf("=====================================================\n");
    printf("SIMULATING RECURSIVE RESOLVER ITERATIVE RESOLUTION WALK\n");
    printf("Target FQDN: %s\n", target);
    printf("=====================================================\n");

    for (int step = 0; step < 3; step++) {
        printf("Hop %d: Querying zone '%s'...\n", step + 1, hierarchy[step].zone_name);
        if (hierarchy[step].final_ip == NULL) {
            printf("  -> Response: REFERRAL (status: NOERROR, ANCOUNT=0)\n");
            printf("  -> Next Authority: %s\n\n", hierarchy[step].next_referral_ns);
        } else {
            printf("  -> Response: AUTHORITATIVE ANSWER (AA=1, ANCOUNT=1)\n");
            printf("  -> Resolved IPv4: %s\n", hierarchy[step].final_ip);
        }
    }
    printf("=====================================================\n");

    return 0;
}
```

---

## 5. Production War Story: Open Resolvers and the 400 Gbps Amplification Attack
In 2013, internet security firm Cloudflare was hit by a massive **400 Gbps Distributed Denial of Service (DDoS) attack**—the largest in internet history at the time.
The attackers did not possess 400 Gbps of bandwidth. They exploited misconfigured **Open Recursive Resolvers**!
1. A standard DNS query is tiny (e.g. 40 bytes: `dig ANY isc.org`).
2. An `ANY` or `DNSKEY` response with DNSSEC signatures can exceed 3,500 bytes!
3. This creates an **Amplification Factor of up to $70	imes$**!
4. The attackers spoofed the target victim's source IP address and sent queries to tens of thousands of open resolvers on the internet.
5. The resolvers amplified the traffic by 70x and blasted 400 Gbps of traffic directly at the victim!
Fix: Modern recursive resolvers **strictly disable open recursion for external IPs** (`recursion no;` in BIND, or restrict `allow-recursion` to internal subnets) and enforce **Response Rate Limiting (RRL)**.
---

## 6. The QNAME Minimization Privacy Standard (RFC 7816)
Historically, when a recursive resolver queried the Root server for `www.secret-company.com`, it sent the **entire domain name** to the Root server!
The 13 root operators and TLD operators could observe every specific website every human on earth was looking up.

In 2016, RFC 7816 introduced **QNAME Minimization**:
- When querying the Root server, the resolver queries **only the TLD**: `dig .com NS`.
- When querying the `.com` TLD server, it queries **only the SLD**: `dig secret-company.com NS`.
- Only when querying the authoritative server does it send the full FQDN: `dig www.secret-company.com A`.
This prevents upstream root and TLD servers from learning user browsing patterns.

---

## 7. DNS Lame Delegation & Glueless Referrals
- **Lame Delegation**: Occurs when a parent zone delegates a domain to a nameserver (`NS ns1.target.com`), but `ns1.target.com` has not been configured to serve the zone and replies with `REFUSED` or `SERVFAIL`.
- **Glueless Referral**: Occurs when nameservers reside outside the delegated zone (e.g. `example.com` uses `ns1.cloudflare.com`). No glue records are required in `.com` because `.cloudflare.com` is resolved independently in its own zone.
---

## 8. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Perform a complete iterative resolution trace from Root servers down:
dig +trace www.wikipedia.org

# Wireshark filter to observe iterative referral chasing packets:
# dns.flags.response == 1 && dns.flags.authoritative == 0 && dns.count.auth_rr > 0

# Measure resolver latency differences between cached and cold lookups:
dig www.wikipedia.org | grep "Query time"
```

---

## 9. Production Verification Checklist & Architecture Audit
- [ ] Verify that public DNS recursive resolvers strictly enforce Bailiwick rules (discarding out-of-zone records).
- [ ] Ensure that internal enterprise resolvers disable open recursion (`allow-recursion { 10.0.0.0/8; 192.168.0.0/16; };`) to prevent being weaponized in DDoS reflection attacks.
- [ ] Enable QNAME minimization (`qname-minimisation: yes` in Unbound or BIND9) to protect user browsing privacy against upstream TLD monitoring.
---

## 10. Mathematical & Algorithmic Foundations: Resolvers RTT Selection Algorithm
When a recursive resolver has multiple authoritative nameservers for a zone (e.g. `ns1`, `ns2`, `ns3`, `ns4`), how does it select which one to query?
BIND and Unbound use an **Exponentially Decaying Smoothed RTT (SRTT)** algorithm:
$$	ext{SRTT}_{	ext{new}} = (1 - lpha) \cdot 	ext{SRTT}_{	ext{old}} + lpha \cdot 	ext{RTT}_{	ext{measured}}$$
with $lpha pprox 0.1$.
- The resolver queries the server with the lowest SRTT.
- If a server fails to answer, a large penalty ($+1,000	ext{ms}$) is added to its SRTT, causing the resolver to instantly fail over to the secondary server.
- Every few minutes, the resolver randomly sends a query to the slower servers to detect if their connectivity has recovered!
---

## 11. Production DNS Security Hardening Matrix & Standards
1. **Bailiwick Enforcement Rules (RFC 2181)**:
   - In-Bailiwick: `sub.example.com` nameserver answering for `example.com` (Permitted).
   - Out-of-Bailiwick: `ns.attacker.com` answering for `example.com` (Allowed only if explicitly delegated by parent `.com`).
   - Sibling Glue: Glue records pointing to sister domains must never overwrite existing authoritative cache entries.
2. **RFC Compliance Matrix**:
   - RFC 1034 Section 4.3.2: Algorithm for Recursive Resolution
   - RFC 2181 Section 5.4.1: Ranking Data Authenticity
   - RFC 7816: DNS Query Name Minimisation to Improve Privacy
   - RFC 8499: DNS Terminology
---

## 12. Full Ladder Timing Trace: Iterative Referral Resolution
Let's trace the exact network packet exchanges and elapsed milliseconds when resolving `www.wikipedia.org` from a cold cache:

```
Time (ms)  Source                  Target                 Protocol / Message
0.0 ms     Client (192.168.1.50)   Resolver (8.8.8.8)     DNS UDP Query: www.wikipedia.org (A, RD=1)
0.8 ms     Resolver (8.8.8.8)      Root (198.41.0.4)      DNS UDP Query: www.wikipedia.org (A, RD=0)
15.2 ms    Root (198.41.0.4)       Resolver (8.8.8.8)     DNS Referral: NS a0.org.afilias-nst.info (ANCOUNT=0, NSCOUNT=6)
15.8 ms    Resolver (8.8.8.8)      .org TLD (199.19.56.1) DNS UDP Query: www.wikipedia.org (A, RD=0)
32.4 ms    .org TLD (199.19.56.1)  Resolver (8.8.8.8)     DNS Referral: NS ns0.wikimedia.org (ANCOUNT=0, NSCOUNT=3)
33.0 ms    Resolver (8.8.8.8)      Auth (208.80.154.238)  DNS UDP Query: www.wikipedia.org (A, RD=0)
54.2 ms    Auth (208.80.154.238)   Resolver (8.8.8.8)     DNS Authoritative Answer: 208.80.154.224 (AA=1, ANCOUNT=1, TTL=600)
55.0 ms    Resolver (8.8.8.8)      Client (192.168.1.50)  DNS Final Response: 208.80.154.224 (Cached!)
```
Notice: The entire cold iterative walk required **3 sequential internet round trips (55ms)**. Once cached, the next client query completes in **0.8ms** directly from resolver memory!
