# Day 34: Modern DNS Records: `SRV`, `CAA`, `HTTPS`/`SVCB`

## 1. Architectural Foundations: Extending DNS Beyond Simple IPs
For the first 15 years of the internet, DNS only answered one question: *"What is the IP address of hostname X?"*
However, modern distributed systems and microservices have much more complex requirements:
- What if a service runs on a **custom non-standard port** (e.g. port 8443)?
- What if multiple server instances should receive traffic weighted by capacity (client-side load balancing)?
- How do we prevent rogue Certificate Authorities from issuing fraudulent SSL certificates?
- How do web browsers discover HTTP/3 (QUIC) support and negotiate Encrypted Client Hello (ECH) **before** opening a TCP connection?

To solve these problems, the IETF developed modern specialized record types: `SRV`, `CAA`, `SVCB`, and `HTTPS`.

---

## 2. RFC 2782: The `SRV` (Service Location) Record
Standardized in 2000, `SRV` records allow clients to discover servers providing a specific service without hardcoding port numbers.
Used universally in Active Directory, Kerberos, SIP (VoIP), Kubernetes, and Minecraft!

### Wire Format & Record Structure:
`_Service._Proto.Name TTL Class SRV Priority Weight Port Target`

```dns
_sip._tcp.example.com.  3600  IN  SRV  10  60  5060  server1.example.com.
_sip._tcp.example.com.  3600  IN  SRV  10  40  5060  server2.example.com.
_sip._tcp.example.com.  3600  IN  SRV  20   0  5060  backup.example.com.
```

- **`Priority` (16 bits)**: Lower priority is chosen first (Priority 10 before Priority 20).
- **`Weight` (16 bits)**: Probabilistic load balancing among identical priority servers. (server1 gets 60% of requests, server2 gets 40%).
- **`Port` (16 bits)**: Exact TCP or UDP port number (e.g. 5060).
- **`Target`**: Canonical hostname of providing host.

---

## 3. RFC 8659: The `CAA` (Certificate Authority Authorization) Record
Before 2017, ANY public Certificate Authority (out of hundreds worldwide) could issue an SSL certificate for ANY domain name! If a small regional CA in Kazakhstan was compromised by hackers, the attackers could issue a valid certificate for `google.com`.
The `CAA` record allows domain owners to specify **which Certificate Authorities are legally permitted to issue certificates** for their domain:

```dns
example.com.  3600  IN  CAA  0 issue "letsencrypt.org"
example.com.  3600  IN  CAA  0 issuewild ";"
example.com.  3600  IN  CAA  0 iodef "mailto:security@example.com"
```

- **`issue`**: Authorizes specific CA (e.g. Let's Encrypt).
- **`issuewild ";"`**: Semicolon denies wildcard certificate issuance entirely!
- **`iodef`**: URL/email where CAs must report unauthorized certificate issuance attempts.
All commercial CAs are legally mandated by the CA/Browser Forum to query and enforce CAA records before issuing certificates.

---

## 4. RFC 9460: The Revolution of `HTTPS` and `SVCB` Records
Standardized in 2023, the **`HTTPS` (Type 65)** and **`SVCB` (Service Binding, Type 64)** records represent the largest evolution in web networking in two decades.

### The Fundamental Problem of Legacy Web Browsing
When a user types `example.com` into Chrome:
1. Browser resolves `A` record $	o$ gets IPv4.
2. Browser opens TCP connection to port 80.
3. Server redirects `301 Moved Permanently` to `HTTPS endpoint` (Wastes 1 full RTT!).
4. Browser opens TLS connection to port 443.
5. Server sends `Alt-Svc: h3=":443"` header announcing HTTP/3 (QUIC) support.
6. Only on the **second visit** can the browser use HTTP/3!

### The Solution: The `HTTPS` Record
The `HTTPS` record delivers all transport parameters in the **very first DNS query**:
```dns
example.com.  3600  IN  HTTPS  1 . (
    alpn="h3,h2"
    port=443
    ipv4hint=198.51.100.1
    ipv6hint=2001:db8::1
    ech=AEn+DQBF...
)
```
- **ALPN (`alpn="h3,h2"`)**: Announces that the server supports HTTP/3 (QUIC) immediately! The browser skips TCP completely and sends QUIC UDP packets on turn 1!
- **IP Hints (`ipv4hint`, `ipv6hint`)**: Bundles target IPs inside the record, eliminating secondary DNS lookups.
- **Encrypted Client Hello (`ech`)**: Contains the server's public key to encrypt the SNI (Server Name Indication) domain in the TLS handshake, completely blinding network eavesdroppers!
- **Alias Mode on Apex**: Allows clean CNAME-like aliasing on root apex domains (`example.com. IN HTTPS 0 target.com.`) without breaking RFC 1034!

---

## 5. Compilable C Program: Inspecting SRV Record Binary Wire Structure
```c
/*
 * srv_record_parser.c - Parses RFC 2782 SRV record binary payload
 * Compile: gcc -O2 -Wall srv_record_parser.c -o srv_record_parser
 */
#include <stdio.h>
#include <stdint.h>
#include <arpa/inet.h>

int main(void) {
    /* Sample wire payload of an SRV record:
     * Priority: 10 (0x000A)
     * Weight:   50 (0x0032)
     * Port:     5060 (0x13C4)
     * Target:   "sip.corp.internal"
     */
    unsigned char srv_rdata[] = {
        0x00, 0x0A,             /* Priority: 10 */
        0x00, 0x32,             /* Weight: 50 */
        0x13, 0xC4,             /* Port: 5060 */
        0x03, 's', 'i', 'p',
        0x04, 'c', 'o', 'r', 'p',
        0x00                    /* Terminator */
    };

    uint16_t priority = ntohs(*(uint16_t *)(srv_rdata + 0));
    uint16_t weight   = ntohs(*(uint16_t *)(srv_rdata + 2));
    uint16_t port     = ntohs(*(uint16_t *)(srv_rdata + 4));

    printf("=========================================\n");
    printf("RFC 2782 SRV RECORD WIRE PARSING\n");
    printf("=========================================\n");
    printf("Priority : %u (Lower = higher preference)\n", priority);
    printf("Weight   : %u (Load balancing weight)\n", weight);
    printf("Port     : %u (Service listening port)\n", port);
    printf("=========================================\n");

    return 0;
}
```

---

## 6. Production War Story: The Rogue CA Phishing Breach
In 2011, Dutch Certificate Authority DigiNotar was breached by sophisticated hackers.
The attackers issued over 500 rogue wildcard SSL certificates, including certificates for `*.google.com`, `*.torproject.org`, and `*.microsoft.com`.
These certificates were used to execute Man-In-The-Middle attacks intercepting communications of over 300,000 citizens.
This incident led directly to the creation of the `CAA` record (RFC 8659).
Today, by placing `CAA issue "digicert.com"` on your domain, if any other CA is breached or tricked into issuing a certificate for your domain, modern security monitors and automated CA auditors immediately flag and block the fraudulent certificate.
---

## 7. Deep Systems Internals: Encrypted Client Hello (ECH) Mechanics
In standard HTTPS (TLS 1.3), while the HTTP request payload is encrypted, the **SNI (Server Name Indication)** header is sent in **cleartext plaintext**!
Anyone watching your network traffic can see that you are visiting `secure forum domain`!

**Encrypted Client Hello (ECH)** (RFC 9460 + IETF draft) solves this:
1. The client queries the domain's `HTTPS` DNS record.
2. The record returns the `ech` parameter containing the server's public encryption key.
3. The client splits the TLS Client Hello into two messages:
   - **Outer Hello**: Contains a benign dummy domain (e.g. `cloudflare.com`).
   - **Inner Hello**: Contains the real private domain (`private-forum.org`), **completely encrypted** using the public key from DNS!
4. Network eavesdroppers only see a connection to `cloudflare.com`, preserving absolute browsing privacy!

---

## 8. Client-Side SRV Load Balancing Algorithm (RFC 2782)
When multiple SRV records have identical priority, RFC 2782 mandates a weighted randomized selection algorithm:
1. Compute the sum of all weights: $S = \sum w_i$.
2. Choose a uniform random integer $r \in [0, S]$.
3. Iterate through records accumulating running sum until running sum $\ge r$.
4. Select that server for the connection!
This guarantees zero server-side state while distributing load proportionally to hardware capacity.
---

## 9. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Query modern HTTPS records using dig:
dig example.com TYPE65 +short
dig example.com HTTPS +noall +answer

# Query Certificate Authority Authorization records:
dig example.com CAA +noall +answer

# Query Active Directory or Kerberos SRV service records:
dig _kerberos._tcp.corp.internal SRV +noall +answer

# Wireshark filter for modern DNS record types:
# dns.qry.type == 65 || dns.qry.type == 257 || dns.qry.type == 33
```

---

## 10. Production Verification Checklist & Architecture Audit
- [ ] Configure `CAA` records with `issue` and `issuewild` directives to strictly confine SSL certificate issuance to trusted CAs.
- [ ] For modern HTTP/3 and ECH-enabled web services, publish RFC 9460 `HTTPS` records with `alpn="h3,h2"` to eliminate redirection RTT.
- [ ] Verify that all SRV targets point to fully qualified domain names (FQDNs), not IP addresses.
---

## 11. Mathematical & Algorithmic Foundations: SVCB SvcParamKey Encoding
In RFC 9460, `SVCB` and `HTTPS` parameters are encoded as high-efficiency binary Type-Length-Value (TLV) keys:
- `Key 1 (alpn)`: List of length-prefixed protocol strings (e.g. `[0x02, 'h', '2', 0x02, 'h', '3']`).
- `Key 2 (no-default-alpn)`: Empty flag indicating that default protocols are forbidden.
- `Key 3 (port)`: 2-byte integer (`uint16_t`) in network byte order.
- `Key 4 (ipv4hint)`: Array of 4-byte IPv4 addresses.
- `Key 5 (ech)`: Base64-decoded binary Encrypted Client Hello configuration.
- `Key 6 (ipv6hint)`: Array of 16-byte IPv6 addresses.
Keys are strictly sorted in **ascending numerical order** in the wire payload, enabling binary search parsing in $O(\log_2 K)$ time!
---

## 12. Production DNS Security Hardening Matrix & Standards
1. **CAA Validation Mandate**:
   - All public domains should publish `CAA 0 issue ";"` if no SSL certificates should ever be issued, or strictly list approved CAs.
   - Restricting certificate issuance to a single provider prevents unauthorized shadow-IT certificate generation.
2. **RFC Compliance Matrix**:
   - RFC 2782: A DNS RR for specifying the location of services (DNS SRV)
   - RFC 8659: DNS Certification Authority Authorization (CAA) Resource Record
   - RFC 9460: Service Binding and Parameter Specification via the DNS (SVCB and HTTPS RRs)
   - RFC 8744: Issues and Requirements for Server Name Indication (SNI) Encryption
---

## 13. Client-Side SRV Failover and Priority State Machine
When an application connects to a cluster using SRV records:
1. The client groups all returned records by **Priority** in ascending order.
2. It examines the lowest priority bucket (e.g. Priority `10`).
3. If multiple records share Priority `10`, it applies the weighted random selection algorithm.
4. If the selected server fails to respond to `connect()` within 2 seconds:
   - The client marks that specific host as dead for 60 seconds.
   - It selects the next host in the Priority `10` bucket.
5. If ALL hosts in Priority `10` fail:
   - The client seamlessly falls back to the **Priority 20 bucket** (the standby disaster recovery cluster)!
This provides instant, zero-touch client-side failover without requiring Anycast hardware or expensive BGP routing changes.
