# Day 29: TCP SYN Floods & Cryptographic SYN Cookies

## 1. Architectural Foundations: The SYN Queue Exhaustion Attack
In the standard TCP connection establishment protocol, the server allocates a kernel Transmission Control Block (TCB) upon receiving the initial `SYN` packet and places it in the **SYN Backlog Queue** (`tcp_max_syn_backlog`).

Because the server must wait for the client's final `ACK` (which takes 1 RTT, typically 50ms - 200ms), a malicious attacker spoofing non-existent IP addresses can transmit 100,000 `SYN` packets per second:
1. The server allocates a TCB for each spoofed SYN.
2. The server returns a `SYN+ACK` into the void.
3. The server waits for final ACKs that will never arrive.
4. Within **5 milliseconds**, the SYN queue fills to capacity!
5. Legitimate connection requests from real users are dropped with `Connection refused` or silent timeouts.

```
ATTACKER (Spoofed IP Addresses)                   TARGET SERVER
  |                                                     |
  | --- SYN (IP: 1.2.3.4) ----------------------------> | [Allocates TCB in SYN Queue: Slot 1]
  | --- SYN (IP: 5.6.7.8) ----------------------------> | [Allocates TCB in SYN Queue: Slot 2]
  | --- SYN (IP: 9.10.11.12) -------------------------> | [Allocates TCB in SYN Queue: Slot 3]
  | ...                                                 | ...
  | --- SYN (IP: 200.1.2.3) --------------------------> | [SYN Queue 100% FULL! Overflow!]
  |                                                     |
LEGITIMATE USER                                         |
  | --- SYN ------------------------------------------> X [DROPPED! Service Offline!]
```

---

## 2. Stateless SYN Cookies (RFC 4987)
In 1996, D. J. Bernstein and Eric Schenk developed **SYN Cookies**: a cryptographic mechanism allowing servers to accept TCP connections **without allocating a single byte of memory** in kernel space.

When the SYN queue overflows:
1. The server **disables TCB allocation**.
2. Instead of generating a random Initial Sequence Number ($ISN_s$), the server encodes all connection metadata into the 32-bit $ISN_s$:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   t (5 bits)  | MSS Index (3) |          MAC Secret (24 bits) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
- **$t$ (5 bits)**: A slow counter incrementing every 64 seconds ($\text{mod } 32$), providing a 32-minute expiration window.
- **MSS Index (3 bits)**: Encodes one of 8 standard MSS values (536, 1200, 1360, 1400, 1440, 1452, 1460, 8960).
- **MAC (24 bits)**: A cryptographic hash of the 5-tuple, timestamp $t$, and a secret kernel key.

3. The server sends `SYN+ACK` containing this cookie sequence number.
4. **Zero memory is allocated!** Spoofed SYNs consume exactly 0 bytes of server RAM.
5. When a legitimate client returns the final `ACK` (`ack = ISN_s + 1`), the server calculates $\text{Cookie} = \text{ack} - 1$, validates the MAC, verifies timestamp freshness, and constructs the connection block on-the-fly!

---

## 3. Production Masterclass: Compilable C RFC 4987 SYN Cookie Validator

Save as `syn_cookie_crypto.c` and compile with `gcc -Wall -Wextra -O2 syn_cookie_crypto.c -o syn_cookie_crypto`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <assert.h>

static const uint16_t MSS_CODE_TABLE[8] = { 536, 1200, 1360, 1400, 1440, 1452, 1460, 8960 };

uint32_t compute_cookie_hash(uint32_t saddr, uint32_t daddr, uint16_t sport,
                             uint16_t dport, uint8_t t, uint32_t secret) {
    uint32_t hash = secret;
    hash ^= saddr; hash *= 0x5bd1e995; hash ^= hash >> 15;
    hash ^= daddr; hash *= 0x5bd1e995; hash ^= hash >> 15;
    hash ^= ((uint32_t)sport << 16) | dport; hash *= 0x5bd1e995; hash ^= hash >> 15;
    hash ^= t;     hash *= 0x5bd1e995; hash ^= hash >> 15;
    return hash & 0x00FFFFFF; // 24-bit MAC
}

uint32_t generate_cookie(uint32_t saddr, uint32_t daddr, uint16_t sport,
                         uint16_t dport, uint16_t mss, uint32_t secret) {
    uint8_t t = (time(NULL) / 64) & 0x1F; // 5-bit time
    uint8_t mss_idx = 0;
    for (int i = 7; i >= 0; i--) {
        if (mss >= MSS_CODE_TABLE[i]) { mss_idx = i; break; }
    }
    uint32_t mac = compute_cookie_hash(saddr, daddr, sport, dport, t, secret);
    return ((uint32_t)t << 27) | ((uint32_t)mss_idx << 24) | mac;
}

int verify_cookie(uint32_t cookie, uint32_t saddr, uint32_t daddr,
                  uint16_t sport, uint16_t dport, uint32_t secret, uint16_t *out_mss) {
    uint8_t t = (cookie >> 27) & 0x1F;
    uint8_t mss_idx = (cookie >> 24) & 0x07;
    uint32_t mac = cookie & 0x00FFFFFF;

    uint8_t current_t = (time(NULL) / 64) & 0x1F;
    if (((current_t - t) & 0x1F) > 2) return 0; // Expired

    uint32_t expected_mac = compute_cookie_hash(saddr, daddr, sport, dport, t, secret);
    if (mac != expected_mac) return 0; // Forged / Invalid

    *out_mss = MSS_CODE_TABLE[mss_idx];
    return 1;
}

int main(void) {
    printf("====================================================\n");
    printf("RFC 4987 CRYPTOGRAPHIC SYN COOKIE ENGINE\n");
    printf("====================================================\n");

    uint32_t secret = 0xCAFEBABE;
    uint32_t client_ip = 0x0A000105; // 10.0.1.5
    uint32_t server_ip = 0x0A000101; // 10.0.1.1
    uint16_t c_port = 54321, s_port = 443;
    uint16_t client_mss = 1460;

    printf("[+] Step 1: SYN Flood saturates backlog -> Generating Stateless Cookie...\n");
    uint32_t cookie_isn = generate_cookie(client_ip, server_ip, c_port, s_port, client_mss, secret);
    printf("  Stateless ISN Generated: 0x%08X (Memory Allocated: 0 bytes!)\n", cookie_isn);

    printf("\n[+] Step 2: Client returns final ACK with ack = ISN + 1...\n");
    uint32_t client_ack = cookie_isn + 1;

    printf("[+] Step 3: Server validates ACK sequence %u without prior state...\n", client_ack);
    uint16_t recovered_mss;
    int ok = verify_cookie(client_ack - 1, client_ip, server_ip, c_port, s_port, secret, &recovered_mss);

    if (ok) {
        printf("  [SUCCESS] Cookie Verified! Recovered MSS: %u bytes\n", recovered_mss);
        assert(recovered_mss == 1460);
    } else {
        printf("  [FAIL] Cookie verification failed!\n");
    }

    return 0;
}
```

---

## 4. Production Post-Mortem: SYN Cookie Tradeoffs & TCP Timestamp Integration
### The Historical Tradeoff
In original RFC 4987 implementations, using SYN Cookies had one major drawback: **it broke TCP Options (Window Scale and SACK)**, because the 32-bit ISN only had enough bits to encode the MSS index.
When SYN cookies activated, high-speed clients lost Window Scaling, locking throughput at 64 KB!

### The Modern Solution (RFC 7323 Timestamp Embedding)
Modern Linux solves this by encoding the Window Scale and SACK Permitted bits into the **32-bit TCP Timestamp Option (`TSval`)** sent in the `SYN+ACK`.
When the client reflects the timestamp back in `TSecr`, Linux extracts the Window Scale and SACK flags, providing **100% feature preservation under active DDoS attacks**.---

## 5. SipHash-2-4 Cryptography in Modern Linux SYN Cookies
Historically, SYN cookies used MD5 or SHA-1 hashes. In modern kernels (Linux 4.4+), the kernel utilizes **SipHash-2-4**:
- Optimized specifically for short 64-bit to 128-bit network inputs.
- Provides cryptographic defense against **HashDoS attacks** and secret key recovery.
- Executes in less than **15 nanoseconds** per packet on modern x86-64 CPUs, enabling a single Linux host to validate over **50 million SYN cookies per second** in hardware line-rate DDoS filtering appliances.
---

## 7. Deep Architectural Mechanics: Kernel `secure_tcp_syn_cookie` C Implementation

### The Linux Kernel SYN Cookie Function Dissection
In `net/ipv4/syncookies.c`, the Linux kernel generates SYN cookies using cryptographic SipHash:
```c
/* Simplified conceptual view of Linux kernel syncookies.c */
__u32 cookie_v4_init_sequence(const struct iphdr *iph, const struct tcphdr *th, u16 *mssp) {
    u32 count = tcp_cookie_time(); /* Slow counter incrementing every 64s */
    u32 mssind = find_mss_index(*mssp);

    /* Compute keyed SipHash over 5-tuple and count */
    u32 hash = secure_tcp_syn_cookie(iph->saddr, iph->daddr,
                                     th->source, th->dest,
                                     count, mssind);

    return (count << 27) | (mssind << 24) | (hash & 0x00FFFFFF);
}
```

### The Trade-offs of SYN Cookies: Why They Are Not Always On
While SYN Cookies are an incredible defense against Denial of Service attacks, they carry distinct trade-offs:
1. **Loss of TCP Options**:
   - The standard SYN packet header carries essential options: Window Scale (RFC 7323), SACK Permitted (RFC 2018), and Timestamps.
   - Because the server does not store state when issuing a SYN Cookie, these options are lost unless encoded into the timestamp option!
2. **Workaround - Timestamp Option Encoding (RFC 7323)**:
   - Modern Linux kernels encode the client's Window Scale and SACK support into the lower bits of the `TSval` (Timestamp Value) header if the client supports TCP timestamps.

### Complete Compilable C Program: Demonstrating 32-Bit Bitfield Packing
```c
/*
 * syn_cookie_packing.c - Demonstrates bitfield packing for RFC 4987
 * Compile: gcc -O2 -Wall syn_cookie_packing.c -o syn_cookie_packing
 */
#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint32_t timestamp = 19;     /* 5 bits (0..31) */
    uint32_t mss_idx   = 6;      /* 3 bits (0..7)  */
    uint32_t mac_24    = 0xA3F12C; /* 24 bits */

    uint32_t cookie = (timestamp << 27) | (mss_idx << 24) | (mac_24 & 0x00FFFFFF);

    printf("=========================================\n");
    printf("RFC 4987 SYN COOKIE BITFIELD EXTRACTION\n");
    printf("=========================================\n");
    printf("Generated 32-bit Cookie : 0x%08X\n", cookie);
    printf("Extracted Timestamp (5b): %u (Expected %u)\n", (cookie >> 27) & 0x1F, timestamp);
    printf("Extracted MSS Index (3b): %u (Expected %u)\n", (cookie >> 24) & 0x07, mss_idx);
    printf("Extracted MAC       (24b): 0x%06X (Expected 0x%06X)\n", cookie & 0x00FFFFFF, mac_24);
    printf("=========================================\n");
    return 0;
}
```

---

## 8. Production War Story: The Mirai Botnet SYN Flood Attack
In October 2016, the Mirai botnet launched a massive distributed denial of service attack against DNS provider Dyn, taking down major internet services across North America and Europe.
The attack flooded recursive DNS servers with tens of millions of spoofed TCP SYN packets per second.
Servers running older configurations with small SYN backlogs (`net.ipv4.tcp_max_syn_backlog = 128`) and disabled SYN cookies crashed within milliseconds, dropping all legitimate DNS queries.
Systems running Linux with automated SYN Cookies (`net.ipv4.tcp_syncookies = 1`) and hardware SYN-proxy offload modules were able to maintain uninterrupted TCP connections, proving that cryptographic stateless handshakes are critical internet infrastructure defense mechanisms.
