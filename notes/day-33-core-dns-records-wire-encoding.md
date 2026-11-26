# Day 33: Core DNS Records Wire Encoding

## 1. Architectural Foundations: Resource Records (RR) Layout
Every answer, authority, and additional record in a DNS response conforms to the standardized **Resource Record (RR)** wire format (RFC 1035):

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
/                               NAME                            /
/                                                               /
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|              TYPE             |             CLASS             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                              TTL                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           RDLENGTH            |                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+                               /
/                               RDATA                           /
/                                                               /
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **`NAME`**: Domain name (using length labels or compression pointers).
- **`TYPE` (16 bits)**: Record type identifier (e.g. `1` for A, `28` for AAAA).
- **`CLASS` (16 bits)**: Network class (almost always `1` = `IN` for Internet).
- **`TTL` (32 bits)**: Time-To-Live in seconds. Caching duration permitted before eviction.
- **`RDLENGTH` (16 bits)**: Number of bytes in the `RDATA` field.
- **`RDATA`**: Type-specific binary payload.

---

## 2. Wire Format Dissection of the 7 Core Record Types

### 1. `A` Record (Type 1) - IPv4 Address
- `RDLENGTH`: Fixed at `4` bytes.
- `RDATA`: Exactly 4 bytes of IPv4 binary octets in network byte order.
  Example: `192.0.2.1` $	o$ `[0xC0, 0x00, 0x02, 0x01]`.

### 2. `AAAA` Record (Type 28) - IPv6 Address
- `RDLENGTH`: Fixed at `16` bytes.
- `RDATA`: Exactly 16 bytes representing the 128-bit IPv6 address.

### 3. `CNAME` Record (Type 5) - Canonical Name
- Maps an alias to the true canonical domain name.
- `RDATA`: Length-prefixed domain name (eligible for compression pointers).
- **Crucial Rule**: RFC 1034 forbids any other record type (like MX or TXT) from coexisting with a CNAME on the exact same domain label. (This is why you cannot put a CNAME on the root apex `@`!).

### 4. `MX` Record (Type 15) - Mail Exchange
- `RDATA`:
  - `Preference` (16 bits): Lower value = higher delivery priority.
  - `Exchange` (Variable): Domain name of receiving mail server.

### 5. `TXT` Record (Type 16) - Text Strings (SPF, DKIM, DMARC)
- `RDATA`: One or more length-prefixed text chunks (each chunk maximum 255 bytes).
- Used for email authentication (SPF `v=spf1 ...`, DKIM public keys) and domain ownership verification.

### 6. `NS` Record (Type 2) - Authoritative Name Server
- `RDATA`: Domain name of authoritative nameserver.

### 7. `SOA` Record (Type 6) - Start of Authority
Defines authoritative parameters for the zone:
- `MNAME`: Primary master nameserver.
- `RNAME`: Email address of zone administrator (with `@` replaced by a dot `.`).
- `SERIAL` (32 bits): Version number of zone file (format: `YYYYMMDDNN`).
- `REFRESH` (32 bits): How often secondary servers check master for changes.
- `RETRY` (32 bits): Retry interval if master refresh fails.
- `EXPIRE` (32 bits): Time after which secondary stops answering if master is unreachable.
- `MINIMUM` (32 bits): Negative cache TTL (RFC 2308).

---

## 3. Compilable C Program: Decoding Resource Record Wire Payloads
```c
/*
 * rr_decoder_demo.c - Decodes A, MX, and SOA record binary wire formats
 * Compile: gcc -O2 -Wall rr_decoder_demo.c -o rr_decoder_demo
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <arpa/inet.h>

int main(void) {
    /* Wire payload of an A record: 192.168.1.100 (TTL: 300s) */
    unsigned char a_rr[] = {
        0xC0, 0x0C,             /* Pointer to Name at offset 12 */
        0x00, 0x01,             /* Type: A (1) */
        0x00, 0x01,             /* Class: IN (1) */
        0x00, 0x00, 0x01, 0x2C, /* TTL: 300 seconds */
        0x00, 0x04,             /* RDLENGTH: 4 bytes */
        192, 168, 1, 100        /* IPv4 Address */
    };

    uint16_t type = ntohs(*(uint16_t *)(a_rr + 2));
    uint32_t ttl = ntohl(*(uint32_t *)(a_rr + 6));
    uint16_t rdlen = ntohs(*(uint16_t *)(a_rr + 10));

    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, a_rr + 12, ip_str, sizeof(ip_str));

    printf("=========================================\n");
    printf("DNS RESOURCE RECORD (RR) WIRE DECODING\n");
    printf("=========================================\n");
    printf("Record Type    : %u (A - IPv4)\n", type);
    printf("Record TTL     : %u seconds\n", ttl);
    printf("Payload Length : %u bytes\n", rdlen);
    printf("Parsed IPv4    : %s\n", ip_str);
    printf("=========================================\n");

    return 0;
}
```

---

## 4. Production War Story: The CNAME Apex Cloudflare Disaster
In 2017, a major SaaS startup wanted to point their apex domain `example.com` to their cloud load balancer `lb-123.elasticloadbalancing.amazonaws.com`.
The developer configured a `CNAME` on the apex:
`example.com. IN CNAME lb-123...`
Within 15 minutes, **all corporate email stopped flowing across the company!**
Why?
Per RFC 1034 Section 3.6.2, if a CNAME exists for a node, **no other record type can exist for that name**.
Because `example.com` had a CNAME, global mail transfer agents (MTAs) discarded the domain's `MX` records!
Email servers around the world could no longer locate mail exchangers and bounced all messages.
Solution:
Never put a raw CNAME on apex `@`.
Modern DNS providers support **CNAME Flattening** or **ALIAS/ANAME records**, where the authoritative nameserver queries the target CNAME in real-time and dynamically emits raw `A` records to clients!
---

## 5. SPF, DKIM, and DMARC TXT Record Engineering
Modern enterprise security relies on DNS TXT records to authenticate outbound email and stop phishing:

### 1. SPF (Sender Policy Framework - RFC 7208)
Specifies which IP addresses are authorized to send email for the domain:
```dns
example.com.  300  IN  TXT  "v=spf1 ip4:198.51.100.0/24 include:_spf.google.com -all"
```
- `-all`: Hard fail (reject all unauthorized senders).
- `~all`: Soft fail (accept but flag as spam).

### 2. DKIM (DomainKeys Identified Mail - RFC 6376)
Publishes the cryptographic public key used to verify digital signatures on email headers:
```dns
google._domainkey.example.com.  300  IN  TXT  "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ..."
```

### 3. DMARC (RFC 7489)
Instructs receiving mail servers what to do if SPF or DKIM validation fails:
```dns
_dmarc.example.com.  300  IN  TXT  "v=DMARC1; p=reject; rua=mailto:dmarc-reports@example.com; pct=100"
```
- `p=reject`: Instructs global email providers (Gmail, Outlook, Yahoo) to discard forged emails immediately!

---

## 6. SOA Serial Number Math (RFC 1982)
The SOA `SERIAL` field is a 32-bit unsigned integer compared using **Serial Number Arithmetic** (RFC 1982):
$$s_1 < s_2 \iff (s_1 < s_2 	ext{ and } s_2 - s_1 < 2^{31}) \lor (s_1 > s_2 	ext{ and } s_1 - s_2 > 2^{31})$$
This allows zone versions to wrap around $2^{32} - 1$ back to $0$ without breaking secondary replication!
Standard convention: `YYYYMMDDNN` (e.g. `2026112601`).
---

## 7. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Inspect all DNS record types for a domain in a single command:
dig example.com ANY +noall +answer

# Verify SPF record syntax and validation:
dig example.com TXT +short | grep "v=spf1"

# Query the authoritative SOA record to verify serial numbers and timers:
dig example.com SOA +multiline

# Query mail exchangers ordered by priority preference:
dig example.com MX +short
```

---

## 8. Production Verification Checklist & Architecture Audit
- [ ] Never place a `CNAME` record on the zone apex (`@`); use `A`/`AAAA` or an alias flattening provider.
- [ ] Verify that the `SOA REFRESH` timer is between 1,800 and 14,400 seconds, and `RETRY` is between 600 and 3,600 seconds.
- [ ] Ensure the `SOA SERIAL` number increments monotonically on every single zone file update (format: `YYYYMMDDNN`).
- [ ] Validate that all mail exchange hosts specified in `MX` records resolve directly to `A`/`AAAA` records, never to CNAMEs!
---

## 9. Mathematical & Algorithmic Foundations: Resource Record Sorting & Round-Robin
When an authoritative DNS server returns multiple `A` records for a single domain (e.g. `example.com` has IPs `[IP_1, IP_2, IP_3]`):
1. **DNS Round-Robin**: The server cyclicly permutes the order of the records on every query:
   - Query 1: `[IP_1, IP_2, IP_3]`
   - Query 2: `[IP_2, IP_3, IP_1]`
   - Query 3: `[IP_3, IP_1, IP_2]`
2. Because client stub resolvers choose the **first IP address** in the answer section, this implements simple, stateless load distribution across web servers without hardware load balancers!
3. **Glibc RFC 6724 Destination Address Selection**:
   - Modern Linux clients re-sort the returned IP addresses using RFC 6724 rules (preferring matching scopes, longest prefix match against local source IPs, and IPv6 over IPv4 if available).
---

## 10. Production DNS Security Hardening Matrix & Standards
To prevent domain hijacking, subdomain takeovers, and email spoofing:
1. **Dangling CNAME Auditing**:
   - When pointing a CNAME to external services (e.g. S3 buckets, GitHub Pages, Heroku apps), if the external service is deleted, the CNAME remains pointing to the dead name!
   - Attackers can register the abandoned bucket name or GitHub username and immediately take over your subdomain!
   - Regularly audit and delete all dangling CNAMEs.
2. **RFC Compliance Matrix**:
   - RFC 1034: Domain Concepts and Facilities
   - RFC 1035: Domain Implementation and Specification
   - RFC 1982: Serial Number Arithmetic
   - RFC 7208: Sender Policy Framework (SPF)
   - RFC 6376: DomainKeys Identified Mail (DKIM)
   - RFC 7489: Domain-based Message Authentication, Reporting, and Conformance (DMARC)
