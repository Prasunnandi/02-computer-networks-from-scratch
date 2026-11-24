# Day 12: TCP 3-Way Handshake & Sequence Numbers

## 1. Architectural Foundations: Connection Establishment
TCP establishes a bidirectional, reliable communication channel across an unreliable network through the **Three-Way Handshake**. The purpose of the handshake is threefold:
1. Confirm bidirectional IP reachability between client and server.
2. Synchronize starting sequence numbers in both directions.
3. Negotiate TCP options (MSS, Window Scale, SACK Permitted, Timestamps).

```
CLIENT (Initiator)                               SERVER (Listener)
State: CLOSED                                    State: LISTEN
      |                                                |
      | ------------- 1. SYN (seq=ISN_c) ------------> | [Allocates TCB / SYN queue]
      |                                                | State: SYN_RECEIVED
State: SYN_SENT                                        |
      |                                                |
      | <------- 2. SYN+ACK (seq=ISN_s, ack=ISN_c+1) - |
      |                                                |
State: ESTABLISHED                                     |
      |                                                |
      | ------------- 3. ACK (ack=ISN_s+1) ----------> | [Moves to Accept queue]
      |                                                | State: ESTABLISHED
      v                                                v
      ========= BIDIRECTIONAL DATA TRANSFER ESTABLISHED =========
```

---

## 2. Initial Sequence Number (ISN) Generation & Cryptography

### Why Sequence Numbers Cannot Start at Zero
If every TCP connection began with `seq = 0`:
1. **Old Duplicate Packets**: A delayed segment from an old connection with the exact same 4-tuple could arrive after a new connection is established, corrupting the new stream.
2. **TCP Sequence Prediction Attacks (Mitnick Attack)**: If ISNs increment predictably (e.g. by a fixed constant every second), an attacker can spoof a trusted host's IP, blind-send a SYN, guess the server's sequence number, and inject malicious commands without ever seeing the server's response.

### Modern RFC 6528 ISN Algorithm
Modern Linux kernels compute the ISN using a cryptographically secure pseudorandom function (PRF) with a high-resolution timer and a secret key:
$$\text{ISN} = M + F(\text{LocalIP}, \text{LocalPort}, \text{RemoteIP}, \text{RemotePort}, \text{SecretKey})$$
where:
- $M$ is a monotonic 64-bit microsecond counter.
- $F$ is a cryptographic hash (SipHash-2-4 or MD5) parameterized by a boot-time 128-bit random kernel secret.
This ensures sequence numbers increment rapidly enough to avoid collision while being mathematically indistinguishable from random noise to an outside observer.

---

## 3. SYN Flood Attacks and SYN Cookies

### The Vulnerability: Half-Open Connection Exhaustion
When a server receives a `SYN`, it allocates a Transmission Control Block (TCB) in kernel memory and places it in the **SYN Backlog Queue** (`tcp_max_syn_backlog`).
An attacker sending millions of spoofed `SYN` packets from non-existent IP addresses will exhaust the server's SYN queue within milliseconds. Legitimate clients receive connection refused or dropped packets.

### The Solution: SYN Cookies (RFC 4987)
When the SYN queue fills to capacity, Linux activates **SYN Cookies** (`net.ipv4.tcp_syncookies = 1`).
The server **allocates zero memory** in kernel space! Instead, it encodes the entire connection state into the 32-bit `ISN_s` returned in the `SYN+ACK`:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   t (5 bits)  | MSS Index (3) |          MAC Secret (24 bits) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
1. **$t$ (5 bits)**: A slow counter incrementing every 64 seconds ($\text{mod } 32$), providing a 32-minute expiration window.
2. **MSS Index (3 bits)**: Encodes one of 8 standard MSS values (e.g. 536, 1200, 1440, 1460).
3. **MAC (24 bits)**: A cryptographic hash:
   $$\text{MAC} = \text{Hash}(LocalIP, RemoteIP, LocalPort, RemotePort, t, \text{SecretKey})$$

When the client returns the final `ACK` (`ack = ISN_s + 1`), the server extracts the cookie by computing $\text{Cookie} = \text{ack} - 1$, re-evaluates the MAC, verifies timestamp freshness, and recreates the socket connection block on-the-fly!

---

## 4. Production Masterclass: Compilable C SYN Cookie Implementation

Save as `syn_cookie_engine.c` and compile with `gcc -Wall -Wextra -O2 syn_cookie_engine.c -o syn_cookie_engine`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <assert.h>

// 8 standard MSS values mapped to 3-bit indices
static const uint16_t MSS_TABLE[8] = { 536, 1200, 1360, 1400, 1440, 1452, 1460, 8960 };

// Minimal MurmurHash3 / PRF simulator for 24-bit MAC
uint32_t compute_mac(uint32_t src_ip, uint32_t dst_ip, uint16_t src_port,
                    uint16_t dst_port, uint8_t t, uint32_t secret) {
    uint32_t h = secret;
    h ^= src_ip;  h *= 0x5bd1e995; h ^= h >> 15;
    h ^= dst_ip;  h *= 0x5bd1e995; h ^= h >> 15;
    h ^= ((uint32_t)src_port << 16) | dst_port; h *= 0x5bd1e995; h ^= h >> 15;
    h ^= t;       h *= 0x5bd1e995; h ^= h >> 15;
    return h & 0x00FFFFFF; // 24-bit mask
}

uint8_t find_mss_index(uint16_t mss) {
    for (int i = 7; i >= 0; i--) {
        if (mss >= MSS_TABLE[i]) return i;
    }
    return 0;
}

uint32_t generate_syn_cookie(uint32_t src_ip, uint32_t dst_ip, uint16_t src_port,
                            uint16_t dst_port, uint16_t client_mss, uint32_t secret) {
    uint8_t t = (time(NULL) / 64) & 0x1F; // 5-bit time counter
    uint8_t mss_idx = find_mss_index(client_mss) & 0x07; // 3-bit MSS index
    uint32_t mac = compute_mac(src_ip, dst_ip, src_port, dst_port, t, secret);

    uint32_t cookie = ((uint32_t)t << 27) | ((uint32_t)mss_idx << 24) | mac;
    return cookie;
}

int validate_syn_cookie(uint32_t cookie, uint32_t src_ip, uint32_t dst_ip,
                        uint16_t src_port, uint16_t dst_port, uint32_t secret,
                        uint16_t *recovered_mss) {
    uint8_t cookie_t = (cookie >> 27) & 0x1F;
    uint8_t cookie_mss_idx = (cookie >> 24) & 0x07;
    uint32_t cookie_mac = cookie & 0x00FFFFFF;

    uint8_t current_t = (time(NULL) / 64) & 0x1F;

    // Verify time window (must be within last 2 increments, ~128 seconds)
    uint8_t diff = (current_t - cookie_t) & 0x1F;
    if (diff > 2) {
        return 0; // Cookie expired!
    }

    uint32_t expected_mac = compute_mac(src_ip, dst_ip, src_port, dst_port, cookie_t, secret);
    if (cookie_mac != expected_mac) {
        return 0; // Invalid signature!
    }

    *recovered_mss = MSS_TABLE[cookie_mss_idx];
    return 1; // Valid cookie!
}

int main(void) {
    printf("====================================================\\n");
    printf("TCP SYN COOKIE GENERATION & VALIDATION ENGINE\\n");
    printf("====================================================\\n");

    uint32_t secret_key = 0xDEADBEEF;
    uint32_t client_ip  = 0xC0A80164; // 192.168.1.100
    uint32_t server_ip  = 0xC0A80101; // 192.168.1.1
    uint16_t client_port = 49152;
    uint16_t server_port = 80;
    uint16_t client_mss = 1460;

    printf("[+] Step 1: Client sends SYN with MSS = %u bytes\\n", client_mss);
    printf("[+] Server SYN Queue full -> Engaging Stateless SYN Cookie\\n");

    uint32_t isn_cookie = generate_syn_cookie(client_ip, server_ip, client_port, server_port, client_mss, secret_key);
    printf("  Generated Server ISN (Cookie): 0x%08X (%u)\\n", isn_cookie, isn_cookie);

    printf("\\n[+] Step 2: Client returns final ACK with ack = ISN + 1\\n");
    uint32_t client_ack = isn_cookie + 1;
    uint32_t returned_cookie = client_ack - 1;

    printf("[+] Step 3: Server validates cookie from ACK (zero prior memory allocated)...\\n");
    uint16_t recovered_mss = 0;
    int is_valid = validate_syn_cookie(returned_cookie, client_ip, server_ip, client_port, server_port, secret_key, &recovered_mss);

    if (is_valid) {
        printf("  [SUCCESS] Cookie is VALID!\\n");
        printf("  Recovered Client MSS : %u bytes\\n", recovered_mss);
        assert(recovered_mss == 1460);
    } else {
        printf("  [FAILED] Cookie validation failed!\\n");
    }

    return 0;
}
```

---

## 5. Production Post-Mortem: The somaxconn SYN Drop Blackout
### The Outage
During a major e-commerce flash sale, a company's Nginx frontend nodes experienced catastrophic connection drops. While CPU utilization was under 25% and network bandwidth was at 15%, over 40% of customer connection attempts timed out with `ETIMEDOUT`.

### Root Cause Analysis
Linux maintains two separate queues during the TCP handshake:
1. **The SYN Backlog Queue** (`net.ipv4.tcp_max_syn_backlog`): Holds connections in `SYN_RECEIVED` state awaiting final ACK.
2. **The Accept Queue** (bounded by `listen(fd, backlog)` and `net.core.somaxconn`): Holds connections in `ESTABLISHED` state awaiting the application's `accept()` system call.

Inspection with `ss -lnt` revealed:
```
State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port
LISTEN  128     128     0.0.0.0:443         0.0.0.0:*
```
`Recv-Q` was pinned at `128` (equal to `Send-Q`).
When the Accept Queue fills completely:
- By default, Linux silently **drops incoming final ACKs** (`net.ipv4.tcp_abort_on_overflow = 0`).
- The server assumes the client will retransmit the ACK, but clients assume the connection is established and wait for the HTTP response.
- The client connection hangs until timeout!

### Remediation
1. **Enlarge Kernel Core Somaxconn**:
   ```bash
   sysctl -w net.core.somaxconn=65535
   sysctl -w net.ipv4.tcp_max_syn_backlog=65535
   ```
2. **Update Application Listen Backlog**:
   In `nginx.conf`:
   ```nginx
   listen 443 ssl backlog=65535;
   ```
3. Enable SYN cookies permanently:
   ```bash
   sysctl -w net.ipv4.tcp_syncookies=1
   ```
