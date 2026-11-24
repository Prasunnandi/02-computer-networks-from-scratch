# Day 18: TCP RTT Estimation (Jacobson) & RTO Timers

## 1. Architectural Foundations: Retransmission Timeout (RTO)
When a TCP segment is lost in transit, the sender must detect the loss and retransmit. If no duplicate ACKs arrive (e.g., the only segment in flight was dropped), the sender relies on the **Retransmission Timeout (RTO)** timer.

- If RTO is too small: the sender triggers **spurious retransmissions** of packets that were merely delayed, wasting bandwidth.
- If RTO is too large: the connection stalls for seconds upon loss, destroying application throughput.

---

## 2. Jacobson's 1988 Algorithm (RFC 6298)
The classical RFC 793 algorithm used a simple Exponential Weighted Moving Average (EWMA):
$$SRTT \leftarrow (1 - \alpha) \times SRTT + \alpha \times R' \quad (\alpha = 0.1 \dots 0.2)$$
$$RTO = \beta \times SRTT \quad (\beta = 2)$$
This formula fails catastrophically under high packet delay variance, because variance grows faster than the mean.

In 1988, Van Jacobson introduced tracking the **Mean Deviation** (variance approximation):

```
For each measured RTT sample R':
1. Compute estimation error:
   Err = R' - SRTT

2. Update Smoothed Round Trip Time (SRTT):
   SRTT <- SRTT + (alpha * Err)             [alpha = 1/8 = 0.125]

3. Update Round Trip Time Variation (RTTVAR):
   RTTVAR <- RTTVAR + beta * (|Err| - RTTVAR) [beta = 1/4 = 0.25]

4. Compute Retransmission Timeout (RTO):
   RTO = SRTT + max(G, 4 * RTTVAR)          [G = clock granularity]
```

### Linux RTO Bounds
Linux enforces strict clamps:
$$RTO = \text{clamp}(RTO, \text{TCP\_RTO\_MIN}=200\text{ms}, \text{TCP\_RTO\_MAX}=120\text{s})$$

---

## 3. Karn's Algorithm & Retransmission Ambiguity
Suppose a packet with `seq = 100` is sent at $t_1$. No ACK arrives before RTO expires.
The sender retransmits `seq = 100` at $t_2$.
At $t_3$, an ACK arrives.
**Did this ACK acknowledge the first transmission or the second transmission?**
- If the first: $RTT = t_3 - t_1$.
- If the second: $RTT = t_3 - t_2$.

### The Two Rules of Karn's Algorithm
1. **Never update SRTT or RTTVAR using RTT samples from retransmitted segments**.
2. **Exponential Backoff**: When a timeout occurs, double the RTO value for each subsequent retransmission:
   $$RTO \leftarrow \min(2 \times RTO, RTO_{\max})$$
   Only reset RTO to the calculated Jacobson value once a segment sent without retransmission is successfully acknowledged.

---

## 4. Production Masterclass: Compilable C Jacobson RTO Engine

Save as `jacobson_rto.c` and compile with `gcc -Wall -Wextra -O2 jacobson_rto.c -o jacobson_rto`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#define TCP_RTO_MIN 200  // 200 ms
#define TCP_RTO_MAX 120000 // 120 seconds

typedef struct {
    double srtt;   // Smoothed RTT (ms)
    double rttvar; // RTT Variation (ms)
    double rto;    // Current RTO (ms)
    int    initialized;
} tcp_rto_tracker_t;

void init_rto_tracker(tcp_rto_tracker_t *t) {
    t->srtt = 0;
    t->rttvar = 0;
    t->rto = 1000; // RFC 6298 recommends initial RTO = 1.0 second
    t->initialized = 0;
}

void update_rtt_sample(tcp_rto_tracker_t *t, double rtt_sample_ms) {
    if (!t->initialized) {
        // First measurement
        t->srtt = rtt_sample_ms;
        t->rttvar = rtt_sample_ms / 2.0;
        t->rto = t->srtt + 4.0 * t->rttvar;
        t->initialized = 1;
    } else {
        // Jacobson 1988 formulation
        double alpha = 0.125; // 1/8
        double beta  = 0.25;  // 1/4

        double err = rtt_sample_ms - t->srtt;
        t->srtt += alpha * err;
        t->rttvar += beta * (fabs(err) - t->rttvar);
        t->rto = t->srtt + 4.0 * t->rttvar;
    }

    // Clamp RTO
    if (t->rto < TCP_RTO_MIN) t->rto = TCP_RTO_MIN;
    if (t->rto > TCP_RTO_MAX) t->rto = TCP_RTO_MAX;

    printf("[RTT Sample: %6.1f ms] -> SRTT = %6.1f ms | RTTVAR = %5.1f ms | Calculated RTO = %6.1f ms\n",
           rtt_sample_ms, t->srtt, t->rttvar, t->rto);
}

void handle_retransmit_timeout(tcp_rto_tracker_t *t) {
    // Karn's exponential timer backoff
    t->rto *= 2.0;
    if (t->rto > TCP_RTO_MAX) t->rto = TCP_RTO_MAX;
    printf("[!] TIMEOUT OCCURRED! Karn's Exponential Backoff -> New RTO = %6.1f ms\n", t->rto);
}

int main(void) {
    printf("====================================================\n");
    printf("JACOBSON 1988 TCP RTT & RTO ESTIMATION ENGINE\n");
    printf("====================================================\n");

    tcp_rto_tracker_t tracker;
    init_rto_tracker(&tracker);

    // Feed a sequence of realistic RTT samples
    double samples[] = { 50.0, 52.0, 48.0, 120.0, 180.0, 55.0, 49.0 };

    for (size_t i = 0; i < sizeof(samples)/sizeof(samples[0]); i++) {
        update_rtt_sample(&tracker, samples[i]);
    }

    printf("\n[!] Simulating packet loss...\n");
    handle_retransmit_timeout(&tracker);
    handle_retransmit_timeout(&tracker);

    return 0;
}
```

---

## 5. Production Post-Mortem: Tail Latency Spikes from Datacenter RTO Floor
### The Outage
A distributed real-time recommendation engine running across 2,000 servers in the same datacenter experienced p99.9 latency spikes of 1,000 milliseconds, violating its 10ms SLA.

### Root Cause Analysis
- Intracenter RTT was less than **0.5 milliseconds** ($500\mu\text{s}$).
- Under occasional microburst incast congestion, a single packet was dropped.
- The legacy Linux kernel had a hardcoded `TCP_RTO_MIN` of **1,000 milliseconds** (1.0 second).
- When a packet was lost without generating 3 duplicate ACKs, the sender waited an entire 1.0 second before retransmitting!

### Remediation
Modern kernels support setting route-specific `rto_min`:
```bash
ip route change 10.0.0.0/8 dev eth0 proto kernel scope link src 10.0.1.5 rto_min 5ms
```
This lowered RTO recovery from 1,000ms to 5ms, completely eliminating the SLA violation.---

## 6. High-Precision RTT Sampling with TCP Timestamps (RFC 7323)
Prior to RFC 7323, a sender could measure at most **one RTT sample per flight of packets**, because tracking timestamps for individual bytes required massive memory overhead.

With the TCP Timestamps Option (Kind 8):
1. The sender puts its current high-resolution clock (`jiffies` or nanoseconds) into `TSval` (4 bytes).
2. The receiver reflects that exact value back in the `TSecr` (Echo Reply) field of its ACK.
3. When the ACK returns, the sender calculates:
   $$RTT = \text{CurrentClock} - \text{TSecr}$$
This allows the sender to compute an accurate RTT sample for **every single ACK received**, vastly increasing the precision and responsiveness of the Jacobson EWMA algorithm on high-speed networks.

---

## 7. Modern BBR Congestion Control vs Loss-Based RTO
Traditional loss-based congestion control algorithms (Reno, Cubic) increase sending rate until packets are dropped, filling router buffers and triggering high RTOs (**Bufferbloat**).

Google's **BBR (Bottleneck Bandwidth and RTT)** algorithm operates fundamentally differently:
- BBR does not interpret packet loss as congestion.
- It continuously tracks two physical properties:
  1. $RTprop$: The minimum round-trip time observed over a 10-second window.
  2. $BtlBw$: The maximum delivery rate observed over the link.
- BBR paces transmissions at exactly $BtlBw$, keeping in-flight data equal to $BDP = BtlBw \times RTprop$. Because router queues never fill, queuing delay drops to zero and RTO timers are almost never triggered.
