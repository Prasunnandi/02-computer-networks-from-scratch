# Day 54: HTTP Caching Architecture: Cache-Control, ETag Validation, and 304 Not Modified

Modern web performance is fundamentally governed by caching. Without distributed caching across browser memory, service workers, enterprise forward proxies, and global Content Delivery Networks (CDNs), the global internet backbone would collapse under video streaming and API traffic. HTTP/1.1 establishes a mathematically rigorous caching specification defined in RFC 7234 and RFC 9111. This masterclass deconstructs the freshness lifetime equation, conditional validation headers, strong vs weak ETags, and the mechanics of `304 Not Modified`.

---

## 1. Freshness Lifetime vs Validation

HTTP caching operates across two distinct operational phases:

1. **Freshness Inspection (Zero Network Round-Trips)**: If a cached response has not exceeded its calculated *Freshness Lifetime*, the cache serves the asset immediately from disk/RAM with zero network latency.
2. **Conditional Validation (One Lightweight Round-Trip)**: Once an asset becomes *stale*, the cache transmits a conditional request to the origin server. If the asset has not changed, the server replies with `304 Not Modified` and zero payload bytes, refreshing the local cache TTL.

```text
Cache Request Flow:
Is response in cache?
       |
       +--> NO  --> Full Network Request (200 OK with Data)
       |
       +--> YES --> Has Freshness Lifetime expired?
                      |
                      +--> NO  --> Serve directly from Cache (Instant!)
                      |
                      +--> YES --> Emit Conditional Request (If-None-Match / If-Modified-Since)
                                     |
                                     +--> Unmodified? --> Server returns 304 Not Modified (Refresh TTL)
                                     +--> Modified?   --> Server returns 200 OK with New Data
```

---

## 2. Mathematical Formalization of Freshness Lifetime (RFC 9111)

A cache evaluates whether an asset is fresh by calculating two values: **Freshness Lifetime** and **Current Age**.

### Calculating Freshness Lifetime ($L$)
The freshness lifetime represents how long the origin intended the asset to remain fresh:

$$L = \begin{cases}
\text{max-age} & \text{if } \text{Cache-Control: s-maxage (for CDNs)} \\
\text{max-age} & \text{if } \text{Cache-Control: max-age exists} \\
T_{\text{Expires}} - T_{\text{Date}} & \text{if } \text{Expires header exists} \\
(T_{\text{Date}} - T_{\text{Last-Modified}}) \times 0.10 & \text{Heuristic Fallback (10\% rule)}
\end{cases}$$

### Calculating Current Age ($A$)
To account for clock drift and network propagation delay:

$$\text{Apparent Age} = \max(0, T_{\text{ResponseReceived}} - T_{\text{Date}})$$

$$\text{Response Delay} = T_{\text{ResponseReceived}} - T_{\text{RequestSent}}$$

$$\text{Corrected Initial Age} = \text{Apparent Age} + \text{Response Delay}$$

$$\text{Resident Time} = T_{\text{Now}} - T_{\text{ResponseReceived}}$$

$$\text{Current Age } A = \text{Corrected Initial Age} + \text{Resident Time}$$

$$\text{Cache Verdict} = \begin{cases}
\text{FRESH (Serve immediately)} & \text{if } A < L \\
\text{STALE (Revalidate with server)} & \text{if } A \ge L
\end{cases}$$

---

### Kernel & Reverse Proxy Cache Table C Struct
In enterprise proxy caches (such as NGINX proxy_cache, Squid, or Varnish), cached HTTP responses are tracked in shared memory using optimized cache table entry descriptors:

```c
struct http_cache_entry {
    uint8_t  etag_hash[16];        /* 128-bit MD5/Murmur3 hash of the ETag header */
    uint64_t last_modified_sec;    /* UNIX timestamp of Last-Modified header */
    uint32_t max_age_seconds;      /* Parsed max-age or s-maxage freshness limit */
    uint32_t response_time_sec;    /* UNIX timestamp when origin response arrived */
    uint16_t http_status;          /* Stored origin response code (200, 206, 301) */
    uint8_t  is_public:1;          /* Bitfield: 1 if Cache-Control: public */
    uint8_t  must_revalidate:1;    /* Bitfield: 1 if must-revalidate is present */
    uint8_t  no_transform:1;       /* Bitfield: 1 if proxy transformations prohibited */
    uint8_t  is_weak_etag:1;       /* Bitfield: 1 if ETag is semantic weak (W/) */
    uint8_t  reserved_bits:4;      /* Alignment padding bits */
    uint8_t  padding[1];           /* Struct boundary alignment padding */
} __attribute__((packed));
```

Field Alignment Breakdown:
- `etag_hash` (16 bytes): Fast binary index into hashtable lookup buckets.
- `last_modified_sec` (8 bytes): 64-bit integer timestamp for conditional `If-Modified-Since` validation.
- `max_age_seconds` & `response_time_sec` (4 bytes each): High-precision TTL evaluation fields.
- `http_status` (2 bytes): Compact representation of cached response status.
- Bitfields (1 byte total): 5 packed state flags storing caching directives.
- Total memory footprint: exactly 36 bytes per cache entry.

---

## 3. Validation Primitives: Strong vs Weak ETags

When an asset is stale, the client sends a conditional request using validators:
- `Last-Modified` $\to$ `If-Modified-Since` (Timestamp-based, 1-second resolution).
- `ETag` $\to$ `If-None-Match` (Cryptographic or entity-state hash).

### Strong vs Weak Entity Tags
1. **Strong ETag (`ETag: "33a64df5"`)**: Guarantees byte-for-byte identity across the entity body. If even 1 bit changes, the ETag must change. Mandatory for byte-range requests (`206 Partial Content`).
2. **Weak ETag (`ETag: W/"33a64df5"`)**: Guarantees semantic equivalence, but physical bytes may differ (e.g. whitespace changes, gzip compression differences, or dynamically generated timestamps).

```text
Client Revalidation Request:
GET /app.js HTTP/1.1
Host: cdn.site.com
If-None-Match: "33a64df5"
If-Modified-Since: Wed, 21 Oct 2026 07:28:00 GMT

Server Evaluation:
Does current ETag match "33a64df5"?
  -> YES: Emit 304 Not Modified

 (Empty Body! Saves 2 MB payload!)
  -> NO:  Emit 200 OK

 (Full Response Payload)
```

---

## 4. Cache-Control Directive Matrix

| Directive | Scope | Semantic Guarantee |
| :--- | :---: | :--- |
| **`max-age=<sec>`** | All | Asset is fresh for $N$ seconds from origin generation. |
| **`s-maxage=<sec>`** | Shared/CDN | Overrides `max-age` strictly on intermediate shared proxies (CDNs). |
| **`no-cache`** | All | **Does NOT mean "do not cache"!** Means asset may be cached, but MUST be revalidated with server before every use! |
| **`no-store`** | All | **Zero Caching!** Neither browser nor CDN may write response bytes to disk or storage (confidential/banking data). |
| **`immutable`** | Browser | Asset will *never* change during its freshness lifetime; browser suppresses revalidation on user page refresh. |
| **`must-revalidate`**| All | Stale assets must never be served stale under network disconnect. |

---

## 5. Compilable C Implementation: ETag Generator & 304 Revalidation Engine

Compile with: `gcc -O2 -Wall -Wextra etag_validator.c -o etag_validator`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

/* FNV-1a 64-bit hash function to generate fast entity tags */
uint64_t calculate_fnv1a(const char *data, size_t len) {
    uint64_t hash = 14695981039346656037ULL;
    for (size_t i = 0; i < len; i++) {
        hash ^= (uint8_t)data[i];
        hash *= 1099511628211ULL;
    }
    return hash;
}

void process_conditional_request(const char *resource_content, const char *client_if_none_match) {
    size_t content_len = strlen(resource_content);
    uint64_t hash = calculate_fnv1a(resource_content, content_len);

    char server_etag[32];
    snprintf(server_etag, sizeof(server_etag), "\"%016lx\"", hash);

    printf("Server Asset State: Length=%zu, Current ETag=%s\n", content_len, server_etag);
    printf("Client Provided If-None-Match: %s\n", client_if_none_match ? client_if_none_match : "(None)");

    /* Conditional validation check */
    if (client_if_none_match && strcmp(client_if_none_match, server_etag) == 0) {
        printf("--- Response: 304 Not Modified ---\n");
        printf("HTTP/1.1 304 Not Modified\r\n");
        printf("ETag: %s\r\n", server_etag);
        printf("Cache-Control: max-age=3600\r\n");
        printf("\r\n(Zero body bytes transferred!)\n\n");
    } else {
        printf("--- Response: 200 OK ---\n");
        printf("HTTP/1.1 200 OK\r\n");
        printf("ETag: %s\r\n", server_etag);
        printf("Content-Length: %zu\r\n", content_len);
        printf("\r\n%s\n\n", resource_content);
    }
}

int main(void) {
    const char *asset = "console.log('Production Application v1.0.4');";

    /* Scenario 1: First client request (no ETag) */
    process_conditional_request(asset, NULL);

    /* Scenario 2: Subsequent request with matching ETag */
    process_conditional_request(asset, "\"a6a8e3295c3b9b4f\"");

    /* Scenario 3: Request with stale ETag */
    process_conditional_request(asset, "\"old_outdated_hash\"");

    return EXIT_SUCCESS;
}
```

---

## 6. Production Post-Mortem: The Cache Stampede (Thundering Herd) Outage

### Incident Overview
A high-traffic media portal served a viral breaking news article. The origin web servers deployed a caching policy of `Cache-Control: public, max-age=300` across 40 CDN edge points. The page received $50,000$ requests per second.

### The Catastrophic Expiration
1. At $t = 300$ seconds, the asset expired simultaneously across all CDN edge points.
2. In the next 100 milliseconds, $5,000$ incoming client requests arrived at the CDN edges.
3. Because the asset was stale, the CDN edges initiated $5,000$ concurrent backend requests to the origin database servers.
4. The database connection pool exhausted in 200 ms, CPU spiked to 100%, and the origin crashed.

### Modern Architectural Mitigation
1. **`stale-while-revalidate=<sec>`**: Directs the cache to immediately serve the stale asset to users while asynchronously querying the origin in the background:
```text
Cache-Control: max-age=300, stale-while-revalidate=60
```
2. **Locking / Request Collapsing**: Configure CDN reverse proxies to coalesce concurrent backend fetches for the identical URI into a single origin request (`proxy_cache_use_stale updating` in NGINX).
---

## 7. The Vary Header & Multidimensional Cache Indexing

When an origin server serves different representations of the same URI based on client request headers (e.g. gzip vs brotli, English vs Spanish, mobile vs desktop), standard URI-only caching causes cross-client pollution (e.g. serving a gzip-compressed stream to a client that does not support compression).

### The Secondary Cache Key
The `Vary` header instructs caches to store responses indexed by a compound key consisting of the URI and the specified request headers:

$$\text{Cache Key} = \text{Hash}(\text{URI} \parallel \text{Header}_1 \parallel \text{Header}_2)$$

```text
HTTP/1.1 200 OK
Content-Type: text/html
Content-Encoding: gzip
Vary: Accept-Encoding, User-Agent
```

If a cache receives a subsequent request for the identical URI but with `Accept-Encoding: identity`, the cache detects the mismatch in the compound key and avoids serving the cached gzip response.

---

## 8. Cache Topologies: Private vs Shared and Hit Ratio Economics

Distributed caching hierarchies operate across three distinct tiers:

1. **Private Browser Cache**: Dedicated exclusively to a single user in local storage. Caches personalized user profile data (`Cache-Control: private`).
2. **Gateway / CDN Edge Cache**: Shared reverse proxies deployed in 300+ global edge datacenters (e.g. Cloudflare, Fastly). Caches public static assets (`Cache-Control: public, s-maxage=86400`).
3. **Forward Corporate Proxy**: Shared caching proxy deployed at enterprise network egress boundaries.

### Economic Impact of Cache Hit Ratio
Let $B_{\text{total}}$ be the total consumer bandwidth requested. The traffic load $B_{\text{origin}}$ reaching the backend origin database servers is:

$$B_{\text{origin}} = B_{\text{total}} \times (1 - \text{Hit Ratio})$$

Increasing the global CDN cache hit ratio from $90\%$ to $99\%$ achieves a **10-fold reduction ($90\%$ decrease)** in origin infrastructure costs and database connection saturation!
