# Day 19: Fast Retransmit & 3 Duplicate ACKs

## 1. Architectural Foundations: Loss Recovery Without Waiting for RTO
Waiting for a Retransmission Timeout (RTO) is catastrophic for throughput: the pipeline drains, the sender goes idle, and the congestion window collapses to 1 MSS.

To recover lost segments in a fraction of an RTT, TCP employs **Fast Retransmit** (RFC 5681).

```
SENDER                                           RECEIVER
  |                                                 |
  | ----- Segment 1 (seq=1-1000) -----------------> | [Received: OK]
  |                                                 |
  | ----- Segment 2 (seq=1001-2000) [DROPPED!] ---->X (Lost in transit)
  |                                                 |
  | ----- Segment 3 (seq=2001-3000) --------------> | [Out of order! Emits DupACK 1: ack=1001]
  | <---- ACK 1001 (DupACK 1) --------------------- |
  |                                                 |
  | ----- Segment 4 (seq=3001-4000) --------------> | [Out of order! Emits DupACK 2: ack=1001]
  | <---- ACK 1001 (DupACK 2) --------------------- |
  |                                                 |
  | ----- Segment 5 (seq=4001-5000) --------------> | [Out of order! Emits DupACK 3: ack=1001]
  | <---- ACK 1001 (DupACK 3) --------------------- |
  |                                                 |
  | [3 DUPLICATE ACKS RECEIVED!]                    |
  | FAST RETRANSMIT: Retransmit Segment 2!          |
  | ----- Segment 2 (seq=1001-2000) --------------> | [Received! Cumulative ACK catches up: ack=5001]
  | <---- ACK 5001 -------------------------------- |
```

---

## 2. Why Exactly 3 Duplicate ACKs?
In an IP network, packets can take parallel multi-path ECMP routes and arrive out-of-order.
- If receiver generates a duplicate ACK on receiving packet $N+1$ before packet $N$:
  - If sender retransmitted on the **1st duplicate ACK**, normal minor packet reordering would trigger constant spurious retransmissions.
  - If sender retransmitted on the **2nd duplicate ACK**, reordering over 2 hops would still trigger false retransmissions.
- Measurement studies of Internet packet reordering show that over **99% of packet reorderings span at most 2 positions**.
- Therefore, receiving **3 consecutive duplicate ACKs** gives overwhelming statistical certainty ($>99.9\%$) that the missing segment was dropped rather than reordered!

---

## 3. Fast Recovery (TCP Reno)
When 3 Duplicate ACKs trigger Fast Retransmit, TCP Reno avoids resetting $cwnd$ to 1:
1. Set slow-start threshold: $ssthresh \leftarrow \max(\frac{\text{FlightSize}}{2}, 2 \times \text{MSS})$.
2. Retransmit missing segment.
3. Set $cwnd \leftarrow ssthresh + 3 \times \text{MSS}$ (inflating $cwnd$ for the 3 packets that cleared the network to generate the dupACKs).
4. For each additional duplicate ACK received, inflate $cwnd$ by 1 MSS and transmit a new packet if allowed.
5. When the ACK for the retransmitted segment arrives, deflate $cwnd \leftarrow ssthresh$ and resume Congestion Avoidance.

---

## 4. Production Masterclass: Compilable C DupACK & Fast Retransmit Engine

Save as `fast_retransmit_sim.c` and compile with `gcc -Wall -Wextra -O2 fast_retransmit_sim.c -o fast_retransmit_sim`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define DUPACK_THRESHOLD 3

typedef struct {
    uint32_t last_ack;
    int      dupack_count;
    int      in_fast_recovery;
    uint32_t ssthresh;
    uint32_t cwnd;
} tcp_loss_engine_t;

void init_engine(tcp_loss_engine_t *e) {
    e->last_ack = 1000;
    e->dupack_count = 0;
    e->in_fast_recovery = 0;
    e->ssthresh = 65535;
    e->cwnd = 14600; // 10 MSS
}

void on_ack_received(tcp_loss_engine_t *e, uint32_t ack) {
    if (ack == e->last_ack) {
        e->dupack_count++;
        printf("[DupACK #%d] Received duplicate ACK for byte %u\n", e->dupack_count, ack);

        if (e->dupack_count == DUPACK_THRESHOLD) {
            printf("\n====================================================\n");
            printf("[!] 3 DUPLICATE ACKS THRESHOLD REACHED!\n");
            printf("  ACTION: Triggering IMMEDIATE Fast Retransmit of segment %u\n", ack);
            e->ssthresh = e->cwnd / 2;
            e->cwnd = e->ssthresh + 3 * 1460;
            e->in_fast_recovery = 1;
            printf("  State: Entered Fast Recovery (ssthresh=%u, cwnd inflated to %u)\n",
                   e->ssthresh, e->cwnd);
            printf("====================================================\n\n");
        } else if (e->dupack_count > DUPACK_THRESHOLD && e->in_fast_recovery) {
            e->cwnd += 1460;
            printf("  [Fast Recovery] Additional DupACK -> Inflated cwnd to %u bytes\n", e->cwnd);
        }
    } else if (ack > e->last_ack) {
        if (e->in_fast_recovery) {
            printf("[+] RECOVERY ACK: Full cumulative ACK %u received! Exiting Fast Recovery.\n", ack);
            e->cwnd = e->ssthresh;
            e->in_fast_recovery = 0;
        } else {
            printf("[+] Normal ACK received: %u\n", ack);
        }
        e->last_ack = ack;
        e->dupack_count = 0;
    }
}

int main(void) {
    printf("====================================================\n");
    printf("TCP FAST RETRANSMIT & 3-DUPACK SIMULATION\n");
    printf("====================================================\n");

    tcp_loss_engine_t engine;
    init_engine(&engine);

    // Simulate loss of segment 1001, while segments 2001, 3001, 4001 arrive
    on_ack_received(&engine, 1000); // Baseline
    on_ack_received(&engine, 1000); // DupACK 1
    on_ack_received(&engine, 1000); // DupACK 2
    on_ack_received(&engine, 1000); // DupACK 3 -> Fast Retransmit!
    on_ack_received(&engine, 1000); // DupACK 4 -> cwnd inflation
    on_ack_received(&engine, 5000); // Cumulative recovery ACK

    return 0;
}
```

---

## 5. Production Post-Mortem: Mobile Handover Packet Reordering False Retransmits
### The Outage
A video streaming app reported severe throughput drops whenever users walked between Wi-Fi and 5G cellular coverage. Video quality degraded from 4K to 480p with high retransmit rates.

### Root Cause Analysis
During cell tower / Wi-Fi handover, packets were split across both interfaces. Packets traversing 5G arrived 12ms faster than Wi-Fi packets, causing 4 to 5 packets to arrive out of order without any packet loss. The sender interpreted the 4 duplicate ACKs as segment loss, cut its congestion window in half, and triggered unnecessary retransmissions.

### Remediation
Linux TCP supports dynamic reordering detection (FACK / RACK). Tuning `net.ipv4.tcp_reordering`:
```bash
sysctl -w net.ipv4.tcp_reordering=6
```
instructed the kernel to wait for 6 duplicate ACKs on wireless interfaces before declaring loss, completely preventing false window cuts.---

## 6. Linux TCP Congestion State Machine
The Linux kernel implements a formal finite state machine (`tcp_fastretrans_alert()`) to manage loss recovery:

```
+----------------------------------------------------------------------------+
|                          TCP_CA_Open (Normal State)                        |
+----------------------------------------------------------------------------+
                                      |
                         (Duplicate ACK arrives)
                                      v
+----------------------------------------------------------------------------+
|                        TCP_CA_Disorder (DupACK < 3)                        |
|              Suspects minor packet reordering in network                   |
+----------------------------------------------------------------------------+
                                      |
                      (3 Duplicate ACKs accumulate)
                                      v
+----------------------------------------------------------------------------+
|                        TCP_CA_Recovery (Fast Recovery)                     |
|           Retransmits lost segment; inflates cwnd per DupACK               |
+----------------------------------------------------------------------------+
                                      |
                        (Full Cumulative ACK arrives)
                                      v
+----------------------------------------------------------------------------+
|                   TCP_CA_Open (Resumes Congestion Avoidance)               |
+----------------------------------------------------------------------------+
```

### The Emergency Fallback: `TCP_CA_Loss`
If the retransmission timeout (RTO) expires while in any state, the kernel transitions into `TCP_CA_Loss`:
- Collapses $cwnd \leftarrow 1 \text{ MSS}$.
- Resets slow-start threshold $ssthresh \leftarrow \max(cwnd/2, 2 \times \text{MSS})$.
- Enters slow start from scratch to drain network congestion.
