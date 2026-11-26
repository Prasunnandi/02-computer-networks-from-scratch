# Day 36: DNS Caching Dynamics & Negative TTL (RFC 2308)

## 1. Architectural Foundations: Caching as the Scalability Pillar
The global Domain Name System processes hundreds of billions of queries per second.
The only reason the 13 root server clusters and authoritative nameservers do not melt under the immense load is **Hierarchical Caching**.
Every intermediate resolver (browser cache, operating system stub cache, home gateway router, recursive ISP resolver) caches DNS records for a period defined by the record's **Time-To-Live (TTL)**.

When a client queries a record with a TTL of 300 seconds:
1. The first query takes 80ms to traverse the internet.
2. The subsequent 5,000 queries over the next 5 minutes are answered from local RAM cache in **0.1 milliseconds**!
3. Each intermediate resolver decrements the TTL before returning it to the next client, preserving exact timing across the network.

---

## 2. Negative Caching (RFC 2308): Caching Failures
What happens if a client queries a domain name that **does not exist** (e.g. `badtypo.google.com`)?
If failures were not cached, an application stuck in a retry loop could bombard authoritative nameservers with millions of failing queries per second, causing a denial of service!

RFC 2308 introduced **Negative Caching**:
When an authoritative server returns a negative response:
- **`NXDOMAIN` (RCODE 3)**: Name does not exist anywhere in the zone.
- **`NODATA` (RCODE 0, ANCOUNT 0)**: Name exists, but has no records of the requested type (e.g. requesting `AAAA` for a host that only has an `A` record).

The authoritative server includes its **`SOA` (Start of Authority) record** in the `AUTHORITY` section.
The negative caching duration is calculated as:
$$	ext{Negative TTL} = \min(	ext{SOA.TTL}, 	ext{SOA.MINIMUM})$$

```
+-------------------------------------------------------------------------+
| NEGATIVE CACHING FLOW (RFC 2308)                                        |
|                                                                         |
| Client: "What is IPv4 of fake.example.com?"                             |
|                           |                                             |
|                           v                                             |
| Authoritative Server: "NXDOMAIN! (Does not exist)"                      |
|                       Authority: SOA example.com ... MINIMUM = 3600     |
|                           |                                             |
|                           v                                             |
| Recursive Resolver saves: ("fake.example.com" -> NXDOMAIN, TTL: 3600s)  |
|                           |                                             |
| Next 1,000 queries for "fake.example.com" within 1 hour:                |
| -> Answered INSTANTLY with cached NXDOMAIN! Zero upstream traffic!      |
+-------------------------------------------------------------------------+
```

---

## 3. Cache Eviction Policies & Poisoning Boundaries
In high-throughput recursive resolvers (e.g. BIND, Unbound, PowerDNS):
1. **LRU (Least Recently Used) Eviction**: When cache memory is full, the resolver evicts records that have not been queried recently, even if their TTL has not expired.
2. **TTL Clamping**: Many public resolvers clamp TTLs:
   - Minimum TTL clamp: Capped at 5 to 60 seconds (prevents servers from setting `TTL 0` and hammering resolvers).
   - Maximum TTL clamp: Capped at 86,400 seconds (24 hours) or 604,800 seconds (7 days) (prevents stale records from lingering forever if an upstream server sets `TTL 10 years`).

---

## 4. Compilable C Program: In-Memory DNS Cache Engine with TTL Expiration
```c
/*
 * dns_cache_engine.c - Implements an in-memory DNS cache with positive and negative TTL
 * Compile: gcc -O2 -Wall dns_cache_engine.c -o dns_cache_engine
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define CACHE_SIZE 10

typedef enum { CACHE_POSITIVE, CACHE_NEGATIVE } cache_type_t;

typedef struct {
    char domain[64];
    char ip[16];
    time_t expires_at;
    cache_type_t type;
    int is_valid;
} cache_entry_t;

cache_entry_t cache[CACHE_SIZE];

void add_cache(const char *domain, const char *ip, int ttl, cache_type_t type) {
    for (int i = 0; i < CACHE_SIZE; i++) {
        if (!cache[i].is_valid || cache[i].expires_at < time(NULL)) {
            strncpy(cache[i].domain, domain, sizeof(cache[i].domain) - 1);
            strncpy(cache[i].ip, ip ? ip : "NXDOMAIN", sizeof(cache[i].ip) - 1);
            cache[i].expires_at = time(NULL) + ttl;
            cache[i].type = type;
            cache[i].is_valid = 1;
            return;
        }
    }
}

const char *lookup_cache(const char *domain) {
    time_t now = time(NULL);
    for (int i = 0; i < CACHE_SIZE; i++) {
        if (cache[i].is_valid && strcmp(cache[i].domain, domain) == 0) {
            if (cache[i].expires_at >= now) {
                return cache[i].ip;
            } else {
                cache[i].is_valid = 0; /* Expired */
            }
        }
    }
    return NULL; /* Cache Miss */
}

int main(void) {
    memset(cache, 0, sizeof(cache));

    printf("=========================================\n");
    printf("RFC 2308 DNS CACHE ENGINE SIMULATOR\n");
    printf("=========================================\n");

    /* Populate cache */
    add_cache("api.stripe.com", "198.51.100.42", 300, CACHE_POSITIVE);
    add_cache("typo.stripe.com", NULL, 60, CACHE_NEGATIVE);

    printf("Lookup 1: api.stripe.com  -> %s (Cached Positive)\n", lookup_cache("api.stripe.com"));
    printf("Lookup 2: typo.stripe.com -> %s (Cached Negative RFC 2308)\n", lookup_cache("typo.stripe.com"));
    printf("Lookup 3: unknown.com     -> %s (Cache Miss - Needs Upstream)\n",
           lookup_cache("unknown.com") ? lookup_cache("unknown.com") : "CACHE_MISS");

    printf("=========================================\n");
    return 0;
}
```

---

## 5. Production War Story: The 30-Day Negative TTL Outage
In 2018, an infrastructure engineer created a new DNS record `prod-db.internal` for a database migration scheduled for Friday night.
On Wednesday, another developer accidentally queried `prod-db.internal` before the record had been created in Route53.
Route53 returned `NXDOMAIN`.
The authoritative zone had misconfigured `SOA MINIMUM = 2592000` (**30 days!**).
The company's central caching resolvers cached the `NXDOMAIN` failure with a 30-day lifetime!
When Friday night arrived and the database was brought online, none of the internal microservices could resolve the database hostname.
Every query returned cached `NXDOMAIN`!
The engineers had to manually flush the DNS cache on 2,000 production servers to restore service.
Rule of thumb: **Never set SOA MINIMUM higher than 300 to 3600 seconds!**
---

## 6. The TTL Degradation Flow Across Caches
Consider a record published with `TTL = 3600` (1 hour):
1. $t=0$: Authoritative server emits record with `TTL = 3600`.
2. $t=600$ (10 minutes later): ISP Recursive Resolver answers a query. It returns `TTL = 3000` (3600 - 600).
3. $t=1800$ (30 minutes later): Local Home Gateway router answers. It returns `TTL = 1800`.
4. $t=3590$ (59 minutes later): Local stub resolver returns `TTL = 10`.
5. $t=3601$: Record is purged from all caches globally. The next query triggers a fresh upstream lookup.

---

## 7. DNS Prefetching & Stale-While-Revalidate (RFC 8767)
Modern resolvers (Unbound, BIND9, Chrome) implement **Serve-Stale (RFC 8767)**:
- If an authoritative nameserver suffers an outage or DDoS attack, instead of failing with `SERVFAIL`, the caching resolver continues serving expired records for up to several days!
- **DNS Prefetching**: When a cached record reaches $90\%$ of its TTL and is frequently queried, the resolver proactively refreshes the record in the background before it expires, eliminating query latency for users!
---

## 8. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Inspect remaining TTL of a cached record:
dig api.github.com | grep -A 2 "ANSWER SECTION"

# Verify negative caching by querying a non-existent subdomain:
dig this-domain-does-not-exist-12345.google.com

# Inspect local systemd-resolved cache statistics and hit ratios:
resolvectl statistics

# Flush local operating system DNS cache:
resolvectl flush-caches
```

---

## 9. Production Verification Checklist & Architecture Audit
- [ ] Verify that authoritative zones configure `SOA MINIMUM` between 300 and 3,600 seconds to prevent lingering negative cache lockouts.
- [ ] For production microservices subject to rapid cloud failovers, set record TTLs between 30 and 300 seconds.
- [ ] Ensure caching resolvers implement RFC 8767 (Serve-Stale) to maintain high availability during authoritative DNS outages.
---

## 10. Mathematical & Algorithmic Foundations: Cache Hit Ratio & Erlang B Modeling
The efficiency of a caching resolver is measured by its **Cache Hit Ratio ($H$)**:
$$H = rac{N_{	ext{hits}}}{N_{	ext{total}}}$$
For a power-law (Zipfian) distribution of domain popularity where the $k$-th most popular domain has query probability $P(k) \propto 1 / k^s$ with $s pprox 0.8$:
- A small cache of only 10,000 domains can satisfy **over $85\%$ of all global queries**!
- This mathematical reality allows enterprise recursive resolvers to achieve sub-millisecond average lookup times while shielding upstream root and TLD nameservers from billions of repetitive requests.
---

## 11. Production DNS Security Hardening Matrix & Standards
1. **Cache Sizing & Memory Guidelines**:
   - For an enterprise recursive resolver serving 10,000 users, allocate at least 512 MB to 2 GB of RAM for cache buffers (`max-cache-size 2048M` in BIND).
   - Set `max-cache-ttl 86400` (24 hours) and `max-ncache-ttl 3600` (1 hour) to prevent memory saturation from stale records.
2. **RFC Compliance Matrix**:
   - RFC 1035 Section 4.1.3: Resource Record Time-to-Live
   - RFC 2308: Negative Caching of DNS Queries (DNS NCACHE)
   - RFC 8767: Serving Stale Data to Improve DNS Resiliency
   - RFC 2181: Clarifications to the DNS Specification
