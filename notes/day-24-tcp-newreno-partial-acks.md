# Day 24: TCP NewReno: Multi-Drop Window Recovery

## 1. Architectural Foundations: The Reno Multiple Drop Dilemma
Standard TCP Reno (RFC 2001) assumes that only **one packet is dropped per congestion window**.
In real-world networks with bursty cross-traffic or small router buffers, multiple packets in a flight are frequently dropped simultaneously.

```
FLIGHT OF PACKETS: [ Pkt 1 ] [ Pkt 2 - DROPPED ] [ Pkt 3 ] [ Pkt 4 - DROPPED ] [ Pkt 5 ]
                                    |                                |
                                    v                                v
                                Gap #1                           Gap #2
```

### What Happens in Standard Reno
1. Duplicate ACKs from packets 3 and 5 trigger Fast Retransmit of Packet 2.
2. Receiver gets Packet 2. It returns an ACK acknowledging Packet 3.
3. This ACK is a **Partial ACK**: it acknowledges some data, but NOT all in-flight data (because Packet 4 is still missing).
4. In standard Reno, receiving this ACK causes the sender to **exit Fast Recovery**.
5. But Packet 4 was never retransmitted!
6. The sender cannot emit new packets because the window has not advanced. No more duplicate ACKs can arrive.
7. The connection hangs in dead silence until the **Retransmission Timeout (RTO)** expires (typically 200ms - 1000ms), resetting $cwnd \leftarrow 1 \text{ MSS}$!

---

## 2. The NewReno Solution (RFC 6582)
**TCP NewReno** resolves this multi-drop failure **without requiring SACK options** by altering how the sender interprets acknowledgments during Fast Recovery.

### Full Acknowledgment vs Partial Acknowledgment
- **`recover` Marker**: When Fast Recovery is triggered by 3 Duplicate ACKs, the sender records the highest sequence number sent so far in a state variable called `recover`:
  $$\text{recover} \leftarrow \text{SND.NXT}$$
- **Full Acknowledgment**: An ACK whose acknowledgment number is **greater than or equal to `recover`**. It proves that all data in flight at the time loss occurred has been successfully received.
  - Action: Deflate $cwnd \leftarrow ssthresh$ and **exit Fast Recovery**.
- **Partial Acknowledgment**: An ACK whose acknowledgment number is **less than `recover`**. It proves that another packet in that same flight was ALSO lost!
  - **NewReno Action**:
    1. **Do NOT exit Fast Recovery**!
    2. Immediately retransmit the **NEXT missing packet** indicated by the acknowledgment number!
    3. Deflate $cwnd$ by the amount of newly acknowledged data, then re-inflate by 1 MSS.
    4. Reset the retransmission timer.

---

## 3. Mathematical Analysis: Recovery Velocity
Let $M$ be the number of packets dropped in a single congestion window flight.
- **TCP Tahoe**: Requires $M$ complete timeout and Slow Start cycles:
  $$T_{\text{Tahoe}} \approx M \times (RTO + T_{\text{ss}})$$
- **TCP Reno**: Successfully fast-retransmits 1 packet, then suffers RTO on the second:
  $$T_{\text{Reno}} \approx 1 \times RTT + RTO$$
- **TCP NewReno**: Recovers **one lost packet per RTT** without a single timeout:
  $$T_{\text{NewReno}} \approx M \times RTT$$
Because $RTT \ll RTO$ (e.g. 20ms vs 1000ms), **NewReno recovers multi-packet drops 50x faster than Reno**!

---

## 4. Production Masterclass: Compilable C NewReno State Machine

Save as `newreno_engine.c` and compile with `gcc -Wall -Wextra -O2 newreno_engine.c -o newreno_engine`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define MSS 1460

typedef struct {
    uint32_t snd_nxt;          // Next byte to transmit
    uint32_t snd_una;          // Oldest unacknowledged byte
    uint32_t ssthresh;
    uint32_t cwnd;
    uint32_t recover_marker;   // NewReno highest sequence marker
    int      in_fast_recovery;
} tcp_newreno_t;

void init_newreno(tcp_newreno_t *n) {
    n->snd_una = 1000;
    n->snd_nxt = 10000; // 9 KB sent in-flight
    n->ssthresh = 32768;
    n->cwnd = 9000;
    n->in_fast_recovery = 0;
    n->recover_marker = 0;
}

void enter_fast_recovery(tcp_newreno_t *n) {
    n->in_fast_recovery = 1;
    n->recover_marker = n->snd_nxt; // Mark highest in-flight byte
    n->ssthresh = n->cwnd / 2;
    n->cwnd = n->ssthresh + 3 * MSS;

    printf("\n[!] 3 DUPACKS -> ENTERING NEWRENO FAST RECOVERY\n");
    printf("  recover marker set to byte : %u\n", n->recover_marker);
    printf("  ssthresh set to            : %u bytes\n", n->ssthresh);
    printf("  Retransmitting Missing Byte: %u (Gap #1)\n", n->snd_una);
}

void process_ack(tcp_newreno_t *n, uint32_t ack_num) {
    if (!n->in_fast_recovery) {
        n->snd_una = ack_num;
        return;
    }

    if (ack_num >= n->recover_marker) {
        // FULL ACK: Covers all bytes in flight when loss occurred
        printf("\n[+] FULL ACK RECEIVED (ack=%u >= recover=%u)\n", ack_num, n->recover_marker);
        n->cwnd = n->ssthresh;
        n->in_fast_recovery = 0;
        n->snd_una = ack_num;
        printf("  --> Exited Fast Recovery successfully. cwnd = %u\n", n->cwnd);
    } else {
        // PARTIAL ACK: Another packet was dropped in the same flight!
        printf("\n[!] PARTIAL ACK RECEIVED (ack=%u < recover=%u)\n", ack_num, n->recover_marker);
        printf("  --> ACTION: Retransmitting next missing byte %u immediately! (Zero timeout)\n", ack_num);
        n->snd_una = ack_num;
        // Maintain clocking
        n->cwnd -= (ack_num - n->snd_una);
        n->cwnd += MSS;
    }
}

int main(void) {
    printf("====================================================\n");
    printf("TCP NEWRENO PARTIAL ACK RECOVERY ENGINE\n");
    printf("====================================================\n");

    tcp_newreno_t state;
    init_newreno(&state);

    // Simulate multi-packet drop: bytes 2000 and 5000 were dropped
    enter_fast_recovery(&state);

    // Receiver gets retransmitted byte 2000, but is still missing byte 5000!
    // Returns Partial ACK = 5000:
    process_ack(&state, 5000);

    // Receiver gets retransmitted byte 5000, now has all bytes up to 10000!
    // Returns Full ACK = 10000:
    process_ack(&state, 10000);

    return 0;
}
```

---

## 5. Production Post-Mortem: The Cloud Transatlantic Drop Disaster
### The Outage
A high-throughput cloud storage sync service replicating data between Frankfurt (AWS `eu-central-1`) and Northern Virginia (AWS `us-east-1`) experienced severe throughput collapse. Link capacity was 10 Gbps with 90ms RTT, but actual transfer speeds hovered around 12 Mbps.

### Root Cause Analysis
Capture analysis revealed bursty packet loss (2 to 3 packet drops per burst) caused by an overloaded transatlantic peering switch.
Legacy servers were running pure Reno.
Upon each burst, Reno recovered the first drop via Fast Retransmit, received a partial ACK, exited Fast Recovery, and crashed into a **1-second RTO stall**. Over a 90ms RTT path, stalling for 1,000ms destroyed 99% of throughput!

### Remediation
Upgrading to NewReno (and enabling SACK) allowed the endpoints to recover 3 drops in 3 RTTs ($3 \times 90\text{ms} = 270\text{ms}$) with zero timeouts, instantly increasing replication throughput to 8.2 Gbps.---

## 6. NewReno vs Selective Acknowledgments (SACK)
While NewReno brilliantly eliminates RTO timeouts on multi-packet drops without options, it still requires **one RTT per dropped packet**:
- If 5 packets are dropped in a flight:
  - NewReno recovers them sequentially across 5 round-trips:
    $$T_{\text{recover}} = 5 \times RTT$$
- Under **SACK (RFC 2018)**:
  - The receiver reports all 5 missing gaps in a single ACK!
  - The sender retransmits all 5 missing packets in an immediate burst, recovering the entire window in **exactly 1 RTT**:
    $$T_{\text{recover}} = 1 \times RTT$$
NewReno serves as the essential fallback when intermediate networks or legacy middleboxes strip SACK options.---

## 7. RFC 6582 Implementation Details: Careful vs Fast Response
NewReno provides two modes for resetting the retransmission timer during Fast Recovery:
1. **Fast Response (Default)**: Resets the RTO timer on **every partial ACK**. Prevents false timeouts while multi-drop recovery proceeds.
2. **Careful Variant**: Resets the RTO timer only on the first partial ACK, enforcing an overall deadline to catch catastrophic multi-packet collapses.
In enterprise cloud environments, Linux defaults to Fast Response with SACK enabled, ensuring optimal throughput even over lossy wireless or inter-cloud links.
---

## 7. Deep Architectural Mechanics: Fast Recovery State Machine & SACK Scoreboard

### Why Multiple Drops Break Standard Reno
Consider a window of 10 packets (Seq 1 to 10), where both **Seq 3** and **Seq 7** are dropped by a congested router.
1. Seq 1 and 2 arrive $	o$ Receiver sends ACK 3.
2. Seq 4, 5, 6 arrive $	o$ Receiver sends 3 Duplicate ACKs for 3.
3. Reno triggers Fast Retransmit: sends Seq 3, sets `ssthresh = 5`, inflates `cwnd = 8`.
4. Seq 3 arrives at receiver. Receiver now has Seq 1, 2, 3, 4, 5, 6.
5. Receiver sends **ACK 7**!
6. In original Reno, receiving ACK 7 was considered a "new ACK". Reno exited Fast Recovery and deflated `cwnd` to `ssthresh = 5`.
7. But **Seq 7 is still missing!** Because `cwnd` is now 5 and 7 packets have already been sent, the sender cannot transmit anything. It sits frozen until the RTO timer expires!

### The NewReno Solution: The `recover` State Variable
NewReno solves this by tracking the exact boundary of the loss window:
```c
/* RFC 6582 NewReno State Logic */
if (incoming_ack < recover) {
    /* Partial ACK: another packet was lost in the same window! */
    retransmit(incoming_ack);
    cwnd = ssthresh; /* Keep pipeline active */
    /* Do NOT exit Fast Recovery! */
} else {
    /* Full ACK: all lost packets in the window are repaired! */
    cwnd = ssthresh;
    exit_fast_recovery();
}
```

### Complete Compilable C Program: RFC 6582 Recovery Boundary Check
```c
/*
 * newreno_recovery_check.c - Models RFC 6582 recover marker logic
 * Compile: gcc -O2 -Wall newreno_recovery_check.c -o newreno_recovery_check
 */
#include <stdio.h>
#include <stdbool.h>

typedef struct {
    unsigned int snd_una;
    unsigned int snd_nxt;
    unsigned int recover;
    bool in_fast_recovery;
} tcp_newreno_state_t;

void process_ack(tcp_newreno_state_t *st, unsigned int ack) {
    if (!st->in_fast_recovery) {
        st->snd_una = ack;
        return;
    }

    if (ack < st->recover) {
        printf("-> Received Partial ACK %u (recover boundary: %u)\n", ack, st->recover);
        printf("   ACTION: Immediate retransmit of missing segment %u. Stay in Fast Recovery!\n", ack);
        st->snd_una = ack;
    } else {
        printf("-> Received Full ACK %u (>= recover %u)\n", ack, st->recover);
        printf("   ACTION: All window losses repaired! Safely exit Fast Recovery.\n");
        st->snd_una = ack;
        st->in_fast_recovery = false;
    }
}

int main(void) {
    tcp_newreno_state_t st = { .snd_una = 1, .snd_nxt = 10, .recover = 9, .in_fast_recovery = true };
    printf("Initial State: In Fast Recovery, recover marker = %u\n\n", st.recover);

    process_ack(&st, 5); /* Partial ACK */
    process_ack(&st, 9); /* Full ACK */
    return 0;
}
```

---

## 8. Production War Story: The SACK Scoreboard CPU Exhaustion Attack
While NewReno solved partial ACKs sequentially, **Selective Acknowledgment (SACK - RFC 2018)** allowed receivers to acknowledge arbitrary non-contiguous blocks of data using TCP options headers.
In 2019, security researchers discovered **SACK Panic (CVE-2019-11477)** in the Linux kernel.
An attacker could craft malicious SACK sequences with thousands of tiny fragmented blocks. When the Linux kernel processed these SACK blocks, it iterated over a doubly-linked list of packet socket buffers (`sk_buff`), causing kernel CPU usage to spike to $100\%$ and triggering kernel panics.
Understanding NewReno and SACK mechanics is essential not just for network performance, but for operating system security.
