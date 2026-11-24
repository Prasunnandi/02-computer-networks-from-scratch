# Day 20: TCP Selective ACKs (SACK) & ECN Flags

## 1. Architectural Foundations: Multi-Packet Loss Recovery
Classical TCP cumulative ACKs only convey a single integer: the highest contiguous byte received.
When multiple packets are dropped within the same window (e.g. packets 3, 5, and 7):
- Standard Reno can only recover **one lost packet per RTT**. Recovering 3 lost packets requires 3 full round-trip times, during which the sender's pipeline stalls!

To resolve this limitation, RFC 2018 defines **Selective Acknowledgments (SACK)**.

---

## 2. SACK Option Format (Kind 5)
Negotiated during the initial SYN handshake via Option Kind 4 (`SACK Permitted`). During data transfer, when non-contiguous blocks arrive, the receiver includes Option Kind 5 in its ACKs:

```
+-------------+-------------+---------------------------------------+
| Kind = 5    | Length = N  | SACK Block 1 (Left Edge, Right Edge)  |
| (1 byte)    | (1 byte)    | (8 bytes: two 32-bit integers)        |
+-------------+-------------+---------------------------------------+
| SACK Block 2 (Optional, 8B)                                       |
+-------------------------------------------------------------------+
| SACK Block 3 (Optional, 8B)                                       |
+-------------------------------------------------------------------+
| SACK Block 4 (Optional, 8B)                                       |
+-------------------------------------------------------------------+
```
Because the maximum TCP option space is 40 bytes, and timestamps take 10 bytes:
$$\text{Max SACK Blocks} = \frac{40 - 2\text{ (Kind/Len)} - 10\text{ (TSopt)} - 2\text{ (NOP)}}{8} = 3 \text{ blocks (or 4 without timestamps)}$$

Each SACK block specifies an interval $[\text{Left Edge}, \text{Right Edge})$ of data successfully received and queued. The sender immediately retransmits **only the missing gaps** in a single burst!

---

## 3. Explicit Congestion Notification (ECN, RFC 3168)
Historically, the only way a router could signal congestion was to **drop packets**. This caused tail drops, retransmissions, and high latency.

ECN allows routers to signal congestion **without dropping packets** using bits in both the IP and TCP headers.

### 1. IP Header ECN Bits (Bits 6-7 of DiffServ / ToS byte)
- `00`: Non ECN-Capable Transport (Non-ECT)
- `10`: ECN Capable Transport `ECT(0)`
- `01`: ECN Capable Transport `ECT(1)`
- `11`: **Congestion Experienced (CE)** - Marked by router when queue buffer builds up!

### 2. TCP Header ECN Flags
- **ECE (ECN-Echo)**: Sent by receiver to sender when it receives an IP packet with `CE = 11`.
- **CWR (Congestion Window Reduced)**: Sent by sender to acknowledge ECE and confirm it reduced $cwnd$.

```
SENDER                                 ROUTER (Active Queue Mgmt)           RECEIVER
  |                                                |                            |
  | --- Data (IP: ECT=10) -----------------------> | [Queue threshold reached]  |
  |                                                | [Marks CE = 11, NO DROP!]   |
  |                                                | -------------------------> |
  |                                                                             | [Sees CE=11 in IP]
  | <--------------------------- ACK with ECE = 1 ----------------------------- |
  |                                                                             |
  | [Reduces cwnd by 50% without dropping any packets!]                         |
  | --- Data with CWR = 1 ----------------------------------------------------> |
  |                                                                             | [Clears ECE flag]
```

---

## 4. Production Masterclass: Compilable C SACK Block Decoder

Save as `sack_decoder.c` and compile with `gcc -Wall -Wextra -O2 sack_decoder.c -o sack_decoder`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <arpa/inet.h>

typedef struct {
    uint32_t left_edge;
    uint32_t right_edge;
} sack_block_t;

void parse_sack_option(const uint8_t *opt_data, uint8_t opt_len) {
    if (opt_len < 2 || (opt_len - 2) % 8 != 0) {
        printf("[-] Invalid SACK option length: %u\n", opt_len);
        return;
    }

    int num_blocks = (opt_len - 2) / 8;
    printf("[+] Decoding SACK Option: %d isolated block(s) detected\n", num_blocks);

    const uint8_t *ptr = opt_data + 2;
    for (int i = 0; i < num_blocks; i++) {
        uint32_t left  = ntohl(*(const uint32_t *)ptr);
        uint32_t right = ntohl(*(const uint32_t *)(ptr + 4));
        ptr += 8;

        printf("  |-- Block %d: [%u ... %u) (%u bytes isolated in buffer)\n",
               i + 1, left, right, right - left);
    }
}

int main(void) {
    printf("====================================================\n");
    printf("TCP SACK (SELECTIVE ACK) OPTION DECODER\n");
    printf("====================================================\n");

    // Construct synthetic SACK option with 2 blocks:
    // Block 1: [5000 ... 6000)
    // Block 2: [8000 ... 9500)
    uint8_t sack_buf[18];
    sack_buf[0] = 5;  // Kind = 5 (SACK)
    sack_buf[1] = 18; // Length = 2 + 2*8 = 18 bytes

    uint32_t b1_l = htonl(5000), b1_r = htonl(6000);
    uint32_t b2_l = htonl(8000), b2_r = htonl(9500);

    memcpy(sack_buf + 2,  &b1_l, 4);
    memcpy(sack_buf + 6,  &b1_r, 4);
    memcpy(sack_buf + 10, &b2_l, 4);
    memcpy(sack_buf + 14, &b2_r, 4);

    parse_sack_option(sack_buf, sizeof(sack_buf));

    return 0;
}
```

---

## 5. Production Post-Mortem: Legacy Middlebox ECN Drop Outage
### The Outage
When an enterprise enabled `net.ipv4.tcp_ecn = 1` globally on its web infrastructure to reduce latency, 15% of customer requests from legacy corporate networks failed completely during connection setup.

### Root Cause Analysis
Legacy firewalls and low-end router firmware from early 2000s were configured to treat any IP packet with non-zero DiffServ bits 6 and 7 (`ECT` bits) as malformed protocol violations, silently dropping them without generating ICMP replies.

### Remediation
Modern Linux uses `net.ipv4.tcp_ecn = 2` (fallback mode):
- ECN is requested on incoming requests, but if a connection attempt with ECN fails to receive a `SYN+ACK`, the kernel automatically falls back to standard non-ECN SYN retransmissions, guaranteeing compatibility while enabling zero-loss congestion signaling for all modern clients.---

## 6. Bufferbloat & Active Queue Management (CoDel / FQ-CoDel)
When routers have excessive packet buffers, packets sit in queues for hundreds of milliseconds without being dropped. This is **Bufferbloat**.

### Controlled Delay (CoDel) Algorithm
Instead of measuring queue length in bytes, CoDel measures the **sojourn time** (time a packet spends waiting in the queue):
- If the minimum sojourn time over a 100ms interval exceeds **5 milliseconds**, CoDel engages!
- Under standard IP, CoDel drops packets to force sender congestion reduction.
- Under **ECN**, CoDel leaves packets intact and sets the **CE bit (`11`)** in the IP header. The sender receives immediate ECE feedback and cuts its sending rate without a single dropped packet or retransmission!

---

## 7. Data Center TCP (DCTCP, RFC 8257)
In cloud datacenters, standard TCP Reno/Cubic responds too aggressively to ECN: receiving a single CE mark cuts $cwnd$ by 50%, devastating throughput.

**DCTCP** uses multi-bit feedback:
1. The receiver marks ECE proportionally for every CE packet received.
2. The sender estimates the exact fraction $\alpha \in [0, 1]$ of packets marked by the switch:
   $$\alpha \leftarrow (1 - g) \times \alpha + g \times F \quad (g = 1/16)$$
3. The sender cuts $cwnd$ proportionally to the actual congestion severity:
   $$cwnd \leftarrow cwnd \times (1 - \frac{\alpha}{2})$$
If only 5% of packets are marked, $cwnd$ is reduced by only 2.5%, maintaining 99% throughput while preventing packet drops in ultra-low-latency financial and microservice networks.
