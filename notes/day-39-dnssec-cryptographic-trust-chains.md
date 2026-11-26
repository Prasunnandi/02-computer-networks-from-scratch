# Day 39: DNSSEC: Cryptographic Zone Trust Chains

## 1. Architectural Foundations: Cryptographic Authenticity in DNS
Source Port Randomization makes DNS cache poisoning difficult, but it does not provide **cryptographic proof** of authenticity.
An attacker on the same local network, Wi-Fi router, or ISP transit provider can easily eavesdrop on UDP queries and inject forged answers.

**DNSSEC (Domain Name System Security Extensions)** (RFC 4033, 4034, 4035) solves this by adding digital signatures to DNS records using public key cryptography.
DNSSEC provides three critical security guarantees:
1. **Origin Authentication**: Guarantees the answer originated from the true zone owner.
2. **Data Integrity**: Guarantees the records were not tampered with in transit.
3. **Authenticated Denial of Existence**: Cryptographically proves that a domain name does NOT exist!

> **Critical Note**: DNSSEC does **NOT** encrypt DNS traffic! Queries and answers remain plaintext. (Confidentiality is provided by DoT and DoH).

---

## 2. The 4 Fundamental DNSSEC Record Types

### 1. `DNSKEY` (Type 48) - Public Keys
Stores the public keys of the zone:
- **ZSK (Zone Signing Key)**: Used to sign individual resource records. Rotated frequently (e.g. monthly).
- **KSK (Key Signing Key)**: Used to sign the ZSK. Rotated infrequently (e.g. yearly).

### 2. `RRSIG` (Type 46) - Resource Record Signature
Contains the digital signature for a specific record set (RRset).
Every `A` or `MX` record has an accompanying `RRSIG` containing:
- Algorithm ID (e.g. RSA-SHA256, ECDSA-P256-SHA256, Ed25519).
- Signature validity start and expiration timestamps (protects against replay attacks!).
- Cryptographic signature bytes.

### 3. `DS` (Type 43) - Delegation Signer
Stored in the **parent zone** (e.g. `.com` stores the DS record for `example.com`).
The DS record contains a cryptographic SHA-256 hash of the child zone's KSK!
This binds the parent zone to the child zone, building the **Chain of Trust**.

### 4. `NSEC` / `NSEC3` (Type 47 / Type 50) - Authenticated Denial of Existence
How do you sign a negative response (`NXDOMAIN`) when the domain does not exist?
- `NSEC` alphabetically links existing domains: *"There are no domains between `alpha.com` and `charlie.com`!"* (Proves `bravo.com` does not exist).
- `NSEC3` hashes names with salt to prevent **Zone Walking** (harvesting all records in a zone).

```
+-------------------------------------------------------------------------+
| THE DNSSEC CHAIN OF TRUST HIERARCHY                                    |
|                                                                         |
| [Root Zone .]                                                           |
| Root Trust Anchor (Pre-installed in all validating resolvers)           |
| Signs DS record for ".com" using Root KSK                               |
|       |                                                                 |
|       v                                                                 |
| [.com TLD Zone]                                                         |
| Verifies .com DNSKEY matches Root DS record                             |
| Signs DS record for "example.com" using .com KSK                        |
|       |                                                                 |
|       v                                                                 |
| [example.com Zone]                                                      |
| Verifies example.com DNSKEY matches .com DS record                      |
| Validates RRSIG signature on A record "93.184.216.34"                   |
|       |                                                                 |
|       v                                                                 |
| ALL SIGNATURES VALIDATED! (Resolver sets AD=1: Authentic Data!)         |
+-------------------------------------------------------------------------+
```

---

## 3. Dissecting an `RRSIG` Record
```dns
example.com.  300  IN  RRSIG  A 13 2 300 (
    20261201000000 ; Expiration timestamp
    20261120000000 ; Inception timestamp
    34521          ; Key tag
    example.com.   ; Signer's name
    oW3k9z...      ; Raw base64 cryptographic signature
)
```
- `A 13 2 300`: Type covered (A), Algorithm 13 (ECDSA Curve P-256 with SHA-256), Label count (2), Original TTL (300).

---

## 4. Compilable C Program: Verifying DNSSEC Algorithm IDs
```c
/*
 * dnssec_algo_audit.c - Displays standardized IANA DNSSEC cryptographic algorithms
 * Compile: gcc -O2 -Wall dnssec_algo_audit.c -o dnssec_algo_audit
 */
#include <stdio.h>

typedef struct {
    int id;
    const char *name;
    const char *status;
} dnssec_algo_t;

int main(void) {
    dnssec_algo_t algos[] = {
        { 1,  "RSA/MD5",            "DEPRECATED (Insecure)" },
        { 5,  "RSA/SHA-1",          "DEPRECATED (Weak)" },
        { 7,  "RSASHA1-NSEC3-SHA1", "DEPRECATED (Weak)" },
        { 8,  "RSA/SHA-256",        "SUPPORTED" },
        { 10, "RSA/SHA-512",        "SUPPORTED" },
        { 13, "ECDSA P-256/SHA256", "RECOMMENDED (Modern Standard)" },
        { 14, "ECDSA P-384/SHA384", "RECOMMENDED" },
        { 15, "Ed25519",            "RECOMMENDED (Fastest/Safest)" },
        { 16, "Ed448",              "SUPPORTED" }
    };

    printf("=====================================================\n");
    printf("IANA DNSSEC CRYPTOGRAPHIC ALGORITHM STATUS AUDIT\n");
    printf("=====================================================\n");
    printf("%-5s | %-22s | %-25s\n", "ID", "Algorithm", "Security Status");
    printf("-----------------------------------------------------\n");

    for (int i = 0; i < 9; i++) {
        printf("%-5d | %-22s | %-25s\n", algos[i].id, algos[i].name, algos[i].status);
    }
    printf("=====================================================\n");
    return 0;
}
```

---

## 5. Production War Story: The Expired RRSIG Global Outage
In 2020, a major European cloud registrar migrated their DNS management platform.
The automation script responsible for re-signing zones every 14 days crashed silently due to an unhandled API error.
DNSSEC signatures (`RRSIG`) have hard expiration timestamps.
On a Tuesday morning, the inception-to-expiration window elapsed.
Suddenly, every validating recursive resolver in the world (Google `8.8.8.8`, Cloudflare `1.1.1.1`, enterprise ISP resolvers) verified the signatures, detected that `now > RRSIG.Expiration`, and **rejected all queries with `SERVFAIL`**!
Over 40,000 corporate domains disappeared from the internet simultaneously.
Lesson: **DNSSEC automation must be monitored with rigorous alerting on signature expiration buffers (alerting if `RRSIG` expiration is $< 7$ days)**.
---

## 6. Mathematical Verification of ECDSA Curve P-256 (Algorithm 13)
Modern DNSSEC predominantly uses **Algorithm 13 (ECDSAP256SHA256)** over legacy RSA-2048:
- **RSA-2048**: Public key is 256 bytes, signature is 256 bytes. Blows past 512-byte UDP limit immediately!
- **ECDSA P-256**: Public key is 64 bytes, signature is **only 64 bytes** (two 32-byte integers $r$ and $s$)!
Signatures fit easily inside standard EDNS0 UDP packets without fragmentation.

### Signature Verification Equation:
Given public key $Q$, message hash $e = 	ext{SHA256}(m)$, signature $(r, s)$:
1. Compute $w = s^{-1} mod n$.
2. Compute $u_1 = e \cdot w mod n$ and $u_2 = r \cdot w mod n$.
3. Compute elliptic curve point $(x_1, y_1) = u_1 G + u_2 Q$.
4. Signature is VALID if and only if $r \equiv x_1 \pmod n$!

---

## 7. NSEC3 Opt-Out & Zone Walking Defense
In standard `NSEC`, anyone can run `dig NSEC` iteratively to discover every single private host in an entire corporate network (Zone Walking).
`NSEC3` (RFC 5155) hashes domain names using iterated salted SHA-1:
$$	ext{Hash} = 	ext{SHA1}(	ext{name} + 	ext{salt})$$
It publishes the cryptographic hash of the next name rather than the plaintext label, rendering automated zone walking computationally infeasible.
---

## 8. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Query a domain with full DNSSEC validation and output flags:
dig example.com +dnssec +multiline

# Query the DNSKEY public key records for a zone:
dig example.com DNSKEY +multiline

# Query the parent zone for the Delegation Signer (DS) record:
dig com. DS example.com +short

# Verify if the Authentic Data (AD) flag is set in the response header:
dig example.com +dnssec | grep "flags:"
```

---

## 9. Production Verification Checklist & Architecture Audit
- [ ] Ensure automated Key Signing Key (KSK) and Zone Signing Key (ZSK) rollover automation is monitored with strict alerting.
- [ ] Set up alerts if the time remaining on active `RRSIG` signatures drops below 7 days.
- [ ] Always publish the child zone's updated `DS` record at the registrar BEFORE activating the new KSK!
---

## 10. Mathematical & Algorithmic Foundations: RRSIG Expiration Buffer Strategy
When managing automated DNSSEC signing engines (e.g. OpenDNSSEC, BIND auto-dnssec, Cloudflare DNSSEC):
- **Signature Lifetime ($L$)**: Typically 14 to 30 days.
- **Re-sign Frequency ($R$)**: Every 3 to 7 days.
- **Expiration Safety Buffer**:
$$	ext{Buffer} = L - R \ge 7 	ext{ days}$$
This mathematical buffer ensures that even if signing daemons or API credentials fail over a 3-day holiday weekend, signatures remain valid on global recursive resolvers without customer outages.
---

## 11. Production DNS Security Hardening Matrix & Standards
1. **DNSSEC Trust Anchor Maintenance**:
   - All modern validating resolvers automatically maintain the Root Trust Anchor via **RFC 5011 (Automated Updates of DNSSEC Trust Anchors)**.
   - When ICANN rolled the root KSK in October 2018 (the first KSK rollover in internet history), automated RFC 5011 tracking ensured zero global downtime.
2. **RFC Compliance Matrix**:
   - RFC 4033: DNS Security Introduction and Requirements
   - RFC 4034: Resource Records for the DNS Security Extensions
   - RFC 4035: Protocol Modifications for the DNS Security Extensions
   - RFC 5155: DNS Security (DNSSEC) Hashed Authenticated Denial of Existence (NSEC3)
   - RFC 5011: Automated Updates of DNSSEC Trust Anchors
