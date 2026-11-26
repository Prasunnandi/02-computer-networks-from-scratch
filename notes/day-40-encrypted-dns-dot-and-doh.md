# Day 40: Encrypted DNS: DNS-over-TLS (DoT) & DNS-over-HTTPS (DoH)

## 1. Architectural Foundations: The Last-Mile Privacy Problem
DNSSEC guarantees that DNS answers cannot be forged, but it provides **zero confidentiality**.
Every standard DNS query over UDP port 53 is transmitted in **cleartext plaintext across the physical network**:
- Coffee shop Wi-Fi sniffers can see every domain you visit.
- Internet Service Providers (ISPs) log and sell browsing history.
- Nation-state censorship firewalls inspect DNS queries and inject spoofed responses to block access to services.

To protect the "last mile" between the client stub resolver and the recursive resolver, the IETF standardized two encrypted protocols:
1. **DNS-over-TLS (DoT)** (RFC 7858) - Port 853
2. **DNS-over-HTTPS (DoH)** (RFC 8484) - Port 443

```
+-------------------------------------------------------------------------+
| ENCRYPTED DNS PROTOCOL COMPARISON                                       |
|                                                                         |
| Protocol:     DNS-over-UDP            DNS-over-TLS (DoT)  DNS-over-HTTPS|
| Port:         Port 53 (UDP/TCP)       Port 853 (TCP)      Port 443 (TCP)|
| Transport:    Plaintext               TLS 1.3             HTTP/2 or H3  |
| Framing:      Raw Packet              2-byte Length + DNS HTTP POST/GET |
| Privacy:      None (Eavesdropped)     Encrypted           Encrypted     |
| Blockability: Cannot be hidden        Easy to block (853) Indistinguishable |
|                                                           from web HTTPS|
+-------------------------------------------------------------------------+
```

---

## 2. RFC 7858: DNS-over-TLS (DoT) Mechanics
DoT encapsulates raw DNS binary messages directly inside a standard **TLS 1.3 tunnel** on dedicated **TCP Port 853**:
1. Client establishes TCP 3-way handshake to `port 853`.
2. Client negotiates TLS 1.3 handshake and authenticates server certificate.
3. Client transmits standard RFC 1035 wire format DNS packets prefixed by a 2-byte length field.
4. The connection is persistent and multiplexes multiple queries over a single TLS session.

**Advantages**: Clean architectural separation of concerns; low protocol overhead.
**Disadvantages**: Because it runs on dedicated Port 853, authoritarian firewalls can easily block all DoT traffic with a single firewall rule (`iptables -A OUTPUT -p tcp --dport 853 -j DROP`).

---

## 3. RFC 8484: DNS-over-HTTPS (DoH) Mechanics
DoH takes a radically different approach: it encodes raw DNS wireformat packets inside **HTTP/2 or HTTP/3 binary frames** transmitted over standard **HTTPS Port 443**!

### The HTTP POST Wire Format
```http
POST /dns-query HTTP/2
Host: cloudflare-dns.com
Content-Type: application/dns-message
Content-Length: 33
Accept: application/dns-message

[33 bytes of raw RFC 1035 binary DNS query payload]
```

### The HTTP GET Wire Format (Base64URL)
Queries can also be executed via HTTP GET using base64url encoding, enabling intermediate HTTP caching:
`GET /dns-query?dns=AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB HTTP/2`

### Why DoH is Unblockable
Because DoH traffic uses the standard `standard HTTPS port` port (443) and shares the same TLS session headers, ALPN, and ciphers as standard web traffic, a firewall **cannot block DoH without blocking the entire World Wide Web!**

---

## 4. Compilable C Program: Base64URL Encoding for DoH Queries
```c
/*
 * doh_query_encoder.c - Encodes raw DNS wire query into RFC 8484 base64url
 * Compile: gcc -O2 -Wall doh_query_encoder.c -o doh_query_encoder
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

static const char b64url_table[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

void base64url_encode(const unsigned char *src, size_t len, char *dst) {
    size_t i = 0, j = 0;
    while (i < len) {
        uint32_t octet_a = i < len ? src[i++] : 0;
        uint32_t octet_b = i < len ? src[i++] : 0;
        uint32_t octet_c = i < len ? src[i++] : 0;
        uint32_t triple = (octet_a << 16) + (octet_b << 8) + octet_c;

        dst[j++] = b64url_table[(triple >> 18) & 0x3F];
        dst[j++] = b64url_table[(triple >> 12) & 0x3F];
        if (i > len + 1) break;
        dst[j++] = b64url_table[(triple >> 6) & 0x3F];
        if (i > len) break;
        dst[j++] = b64url_table[triple & 0x3F];
    }
    dst[j] = '\0';
}

int main(void) {
    /* Minimal DNS query for "google.com" */
    unsigned char raw_dns[] = {
        0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x06, 'g', 'o', 'o', 'g', 'l', 'e', 0x03, 'c', 'o', 'm', 0x00,
        0x00, 0x01, 0x00, 0x01
    };

    char encoded[128];
    base64url_encode(raw_dns, sizeof(raw_dns), encoded);

    printf("=========================================\n");
    printf("RFC 8484 DNS-OVER-HTTPS (DoH) URL ENCODER\n");
    printf("=========================================\n");
    printf("Raw DNS Message : %zu bytes\n", sizeof(raw_dns));
    printf("Base64URL Param : %s\n", encoded);
    printf("Target DoH URI  : dns.provider.internal/dns-query?dns=%s\n", encoded);
    printf("=========================================\n");

    return 0;
}
```

---

## 5. Production War Story: The Corporate DLP Blind Spot & Enterprise DoH Canaries
In 2019, Mozilla enabled DNS-over-HTTPS by default in Firefox for all US users.
Enterprise security directors were in a panic:
Corporate security stacks rely on monitoring internal DNS queries (on UDP port 53) to detect malware command-and-control (`C2`) channels and enforce Data Loss Prevention (DLP).
When Firefox switched to DoH, employee laptops bypassed internal corporate DNS servers and routed all queries encrypted through external cloud providers, blinding corporate intrusion detection systems!
To resolve this enterprise conflict, the IETF and browser vendors introduced the **DoH Canary Domain**:
Enterprises configure their internal DNS servers to return `NXDOMAIN` for:
`use-application-dns.net`
When Firefox or Chrome launches, it queries `use-application-dns.net`. If it receives `NXDOMAIN`, the browser recognizes that enterprise policies are active and automatically disables DoH, restoring corporate network visibility.
---

## 6. HTTP/3 (QUIC) DNS: DNS-over-QUIC (DoQ - RFC 9250)
The latest evolution in encrypted DNS is **DNS-over-QUIC (DoQ)** (RFC 9250) on dedicated UDP Port 853:
1. Combines the speed of UDP with the military-grade encryption of TLS 1.3!
2. **Zero Head-of-Line Blocking**: In TCP-based DoT and DoH, if a single packet is dropped, all pipelined DNS queries freeze until TCP retransmits. In DoQ, independent QUIC streams ensure a dropped packet on query 1 never delays query 2!
3. **0-RTT Resumption**: Clients reconnecting to known resolvers resolve queries on the very first packet!

---

## 7. Enterprise Unbound Configuration for Encrypted DNS
To deploy a privacy-respecting local caching DNS resolver using DoT upstream forwarding:

```conf
# /etc/unbound/unbound.conf
server:
    interface: 127.0.0.1
    port: 53
    do-ip4: yes
    do-udp: yes
    do-tcp: yes
    qname-minimisation: yes
    harden-glue: yes
    harden-dnssec-stripped: yes

forward-zone:
    name: "."
    forward-tls-upstream: yes
    # Forward to Cloudflare DoT
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
    # Forward to Quad9 DoT
    forward-addr: 9.9.9.9@853#dns.quad9.net
```
---

## 8. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Query a DNS-over-HTTPS (DoH) endpoint using curl:
curl -H 'accept: application/dns-message' \
     'dns.provider.internal/dns-query?dns=AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB' \
     --output - | xxd

# Test DNS-over-TLS (DoT) resolution using kdig:
kdig -d @1.1.1.1 +tls-ca +tls-host=cloudflare-dns.com example.com

# Wireshark filter for encrypted DNS traffic:
# tcp.port == 853 || (tcp.port == 443 && tls.handshake.extensions_alpn_str == "h2")
```

---

## 9. Production Verification Checklist & Architecture Audit
- [ ] Verify that mobile and endpoint devices enforce DoT (Port 853) or DoH (Port 443) with mutual certificate verification.
- [ ] In corporate enterprise networks, deploy the `use-application-dns.net` canary domain to gracefully coordinate endpoint DoH with corporate DLP and firewall appliances.
- [ ] For maximum performance on mobile networks, evaluate DNS-over-QUIC (DoQ - RFC 9250) to eliminate TCP head-of-line blocking.
---

## 10. Mathematical & Algorithmic Foundations: DoH Wire Format vs JSON API Comparison
While some cloud providers offer non-standard JSON DNS APIs (`dns.provider.internal/resolve?name=example.com`), RFC 8484 strictly mandates **`application/dns-message`**:
- **JSON Overhead**: A typical A-record query formatted in JSON is 450 bytes.
- **RFC 1035 Binary Message**: The exact same query is only **29 bytes**!
- Using raw binary wire formats over HTTP/2 eliminates JSON serialization CPU overhead, reduces bandwidth by $93\%$, and allows DNSSEC signatures and EDNS0 options to pass through cleanly without schema translation.
---

## 11. Production DNS Security Hardening Matrix & Standards
1. **Certificate Verification & Pinned Spki**:
   - Encrypted DNS client resolvers MUST validate the upstream server's TLS certificate against public CA roots or match a pinned Subject Public Key Info (`spki-pin`) hash.
   - If certificate verification is disabled, DoT and DoH are completely vulnerable to Man-In-The-Middle interception!
2. **RFC Compliance Matrix**:
   - RFC 7858: Specification for DNS over Transport Layer Security (DoT)
   - RFC 8484: DNS Queries over HTTPS (DoH)
   - RFC 9250: DNS over Dedicated QUIC Connections (DoQ)
   - RFC 8310: Usage Profiles for DNS over TLS and DNS over DTLS
