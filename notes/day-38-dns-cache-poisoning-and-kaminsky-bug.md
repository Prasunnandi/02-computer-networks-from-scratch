# Day 38: DNS Cache Poisoning & The Kaminsky Vulnerability

## 1. Architectural Foundations: Stateless UDP Spoofing
Under standard DNS over UDP, transactions are completely stateless.
When a recursive resolver sends a DNS query to an authoritative server:
1. It chooses a 16-bit **Transaction ID (TxID)** (numbers 0 to 65,535).
2. It sends the query to the authoritative server's IP address.
3. It accepts the **first response packet** that matches the 16-bit TxID, destination IP, and UDP destination port!

### Traditional Birthday Attack Poisoning
Before 2008, an attacker attempting to poison a cache (e.g. inject `google.com -> attacker_ip` into a resolver's cache) faced a major limitation:
- If the attacker flooded the resolver with fake answers, the resolver only listened while waiting for a single query.
- If the real authoritative server answered first, the resolver cached the genuine IP and **ignored all subsequent queries** until the 24-hour TTL expired!
- The attacker had to wait 24 hours before trying again.

---

## 2. The 2008 Dan Kaminsky Vulnerability (CVE-2008-1440)
In July 2008, computer security researcher Dan Kaminsky discovered a devastating architectural flaw in the DNS protocol specification that completely eliminated the TTL waiting barrier!

### The Kaminsky Attack Mechanism
Instead of querying `google.com` directly, the attacker queries random, non-existent subdomains:
- Query 1: `random123.google.com`
- Query 2: `random456.google.com`
- Query 3: `random789.google.com`

Because these subdomains do not exist in the resolver's cache, **every single query forces the resolver to send an upstream query to the authoritative server!**
While the resolver waits, the attacker blasts thousands of forged UDP replies spoofing the authoritative server's IP.
Inside the forged reply, the attacker includes:
1. `ANSWER`: `random123.google.com` $	o$ `203.0.113.1`
2. **`AUTHORITY` (The Poison Payload!)**:
   `google.com.  IN  NS  ns.evil-attacker.com.`
3. **`ADDITIONAL`**:
   `ns.evil-attacker.com.  IN  A  6.6.6.6`

```
+-------------------------------------------------------------------------+
| THE KAMINSKY ATTACK FLOW (CVE-2008-1440)                                |
|                                                                         |
| Attacker                                              Target Resolver   |
|    |                                                         |          |
|    | 1. Query: "What is IPv4 of a8f91z.bank.com?"            |          |
|    |-------------------------------------------------------->|          |
|    |                                                         |          |
|    | 2. Attacker floods with 5,000 spoofed UDP replies:      |          |
|    |    - Guesses TxID: 0x0001, 0x0002, 0x0003...            |          |
|    |    - Authority Payload: "bank.com NS ns.evil.com!"      |          |
|    |========================================================>|          |
|    |                                                         | MATCH!   |
|    |                                                         | TxID hits!
|    |                                                         |          |
|    | RESULT: Target resolver overwrites the entire authority |          |
|    |         delegation for bank.com!                        |          |
|    |         All future user queries for bank.com are        |          |
|    |         hijacked to attacker's server!                  |          |
+-------------------------------------------------------------------------+
```

Because the attacker can generate millions of random subdomains continuously, the attack takes **less than 10 seconds** to succeed over broadband connections!

---

## 3. The Countermeasure: Source Port Randomization (RFC 5452)
Before 2008, resolvers used a static UDP source port (e.g. port 53 or port 1024).
The attacker only had to guess the 16-bit TxID ($2^{16} = 65,536$ possibilities).

Kaminsky coordinated with all global OS and DNS vendors to release **Source Port Randomization (RFC 5452)**:
1. The resolver randomizes both the 16-bit **TxID** ($2^{16}$) AND the 16-bit **UDP source port** ($2^{16}$, $pprox 50,000$ ephemeral ports).
2. Total entropy expands to:
   $$	ext{Entropy} = 65,536 	imes 50,000 pprox 3.2 	imes 10^9 	ext{ combinations!}$$
3. Guessing the correct combination now requires flooding billions of packets, making real-time cache poisoning mathematically infeasible before the genuine reply arrives.

---

## 4. Additional Entropy: The 0x20 Bit-Encoding (RFC Draft)
In 2008, Paul Vixie proposed using mixed-case encoding in domain names:
Because DNS label matching is case-insensitive, `gOoGLe.cOm` resolves identically to `google.com`.
The resolver randomizes the case of every letter (`wWw.gOOglE.cOm`) and verifies that the authoritative server's response echoes the **exact same capitalization**.
Every letter adds 1 bit of cryptographic entropy!

---

## 5. Compilable C Program: Entropy Calculator for DNS Queries
```c
/*
 * dns_entropy_calc.c - Computes probability of successful DNS spoofing
 * Compile: gcc -O2 -Wall dns_entropy_calc.c -lm -o dns_entropy_calc
 */
#include <stdio.h>
#include <math.h>

int main(void) {
    uint32_t txid_space = 65536;       /* 16-bit Transaction ID */
    uint32_t static_port_entropy = txid_space;
    uint32_t randomized_ports = 50000; /* Ephemeral port range */
    uint64_t full_entropy = (uint64_t)txid_space * randomized_ports;

    printf("=====================================================\n");
    printf("DNS CACHE POISONING ENTROPY ANALYSIS (RFC 5452)\n");
    printf("=====================================================\n");
    printf("Pre-Kaminsky (Static Port) Entropy : %u combinations\n", static_port_entropy);
    printf("Packets needed for 50%% crack       : ~%u packets (Instant!)\n\n",
           (uint32_t)(sqrt(static_port_entropy) * 1.177));

    printf("Post-Kaminsky (Port Randomization) : %llu combinations\n", (unsigned long long)full_entropy);
    printf("Packets needed for 50%% crack       : ~%llu packets (Infeasible!)\n",
           (unsigned long long)(sqrt(full_entropy) * 1.177));
    printf("=====================================================\n");

    return 0;
}
```

---

## 6. Production War Story: The Brazilian Banking DNS Hijacking
In 2016, attackers compromised the DNS registrar credentials of a major financial institution in Brazil.
The attackers changed the authoritative nameservers for 36 domain names, redirecting all online banking traffic to fake clone websites equipped with valid SSL certificates.
For 4 hours, all customer transactions, passwords, and credit card numbers were harvested.
This incident highlighted that even with Source Port Randomization, if registrar credentials or authoritative nameservers are tampered with, pure DNS provides zero cryptographic integrity.
This vulnerability drove global adoption of **DNSSEC (Domain Name System Security Extensions)**.
---

## 7. Mathematical Derivation: The Birthday Paradox in DNS Spoofing
Why was DNS cache poisoning so easy before Dan Kaminsky's discovery?
Let:
- $N = 65536$ (The 16-bit TxID space).
- $k$ = Number of forged packets flooded by attacker.
- $m$ = Number of concurrent queries issued by resolver.

From the **Birthday Problem**, the probability of at least one collision (matching TxID) is approximately:
$$P(	ext{Collision}) pprox 1 - e^{-rac{k \cdot m}{2N}}$$

In the Kaminsky attack:
The attacker issues $m = 100$ queries for random subdomains and floods $k = 1000$ spoofed replies.
$$k \cdot m = 100,000$$
$$rac{100,000}{2 	imes 65536} = rac{100,000}{131,072} pprox 0.763$$
$$P(	ext{Collision}) pprox 1 - e^{-0.763} pprox 1 - 0.466 = 53.4\%!$$
In just **100 queries and 1000 spoofed packets**, the probability of successfully poisoning the target cache exceeds **$50\%$**!
This mathematical proof stunned the security community and forced immediate emergency patching globally.
---

## 8. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Test if your recursive resolver randomizes UDP source ports:
dig +short porttest.dns-oarc.net TXT

# Inspect the spread of UDP source ports across multiple queries:
for i in {1..5}; do dig +short whoami.akamai.net; done

# Wireshark filter to audit DNS source port distribution:
# udp.dstport == 53
```

---

## 9. Production Verification Checklist & Architecture Audit
- [ ] Verify that all recursive resolvers enforce RFC 5452 Source Port Randomization across at least 40,000 ephemeral ports.
- [ ] Ensure that network NAT gateways and stateful firewalls do NOT rewrite DNS UDP source ports to static values!
- [ ] Deploy DNSSEC cryptographic validation to render all cache poisoning and spoofing attacks mathematically impossible.
---

## 10. Mathematical & Algorithmic Foundations: Cryptographic PRNG Entropy Requirements
In Source Port Randomization (RFC 5452), generating pseudo-random port numbers requires a **Cryptographically Secure Pseudorandom Number Generator (CSPRNG)**:
- Never use C's standard `rand()`! `rand()` is a Linear Congruential Generator (LCG) where an attacker observing 3 consecutive ports can mathematically compute all future port numbers in milliseconds.
- Modern resolvers use kernel entropy (`/dev/urandom` or `getrandom(2)`) or the ChaCha20 stream cipher to generate unpredictable 16-bit ports and transaction IDs, ensuring that entropy remains at full $2^{31}$ strength.
---

## 11. Production DNS Security Hardening Matrix & Standards
1. **Ephemeral Port Range Expansion**:
   - Ensure the Linux kernel ephemeral port range is maximized to provide full entropy:
     `sysctl -w net.ipv4.ip_local_port_range="10240 65535"` (55,000+ ports).
   - Ensure hardware NAT routers do not map outgoing connections to sequential internal ports!
2. **RFC Compliance Matrix**:
   - RFC 5452: Measures for Making DNS More Resilient against Forgery
   - CVE-2008-1440: Dan Kaminsky DNS Cache Poisoning Vulnerability
   - RFC 3833: Threat Analysis of the Domain Name System
   - RFC 1996: A Mechanism for Prompt Notification of Zone Changes (DNS NOTIFY)
---

## 12. Detailed Payload Dissection: Kaminsky Forged Packet Anatomy
In the 2008 Kaminsky attack, the forged UDP packet injected by the attacker has this exact binary construction:
```
+-------------------------------------------------------------------------+
| FORGED KAMINSKY POISON PACKET ANATOMY                                   |
|                                                                         |
| IP Header:   Src IP = 199.19.56.1 (.org TLD) | Dst IP = Target Resolver |
| UDP Header:  Src Port = 53                   | Dst Port = Guessed Port  |
|                                                                         |
| DNS Header:  ID = Guessed TxID | QR = 1 (Response) | AA = 0 | RCODE = 0 |
|              QDCOUNT = 1 | ANCOUNT = 1 | NSCOUNT = 1 | ARCOUNT = 1      |
|                                                                         |
| Question:    random98741.bank.com.            IN  A                     |
|                                                                         |
| Answer:      random98741.bank.com.  300  IN  A   203.0.113.1           |
|                                                                         |
| Authority:   bank.com.              86400 IN  NS  ns.attacker.com.       |
|              (OVERWRITES ENTIRE APEX DELEGATION FOR BANK.COM!)          |
|                                                                         |
| Additional:  ns.attacker.com.       86400 IN  A   6.6.6.6               |
+-------------------------------------------------------------------------+
```
If the target resolver has NOT randomized its UDP source port, guessing the 16-bit TxID requires only sending 65,536 packets. Over a 100 Mbps broadband link, 65,000 UDP packets take **under 0.15 seconds to transmit**, practically guaranteeing successful domain hijacking!
