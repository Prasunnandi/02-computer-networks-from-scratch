# Day 23: TCP Tahoe vs Reno: Fast Recovery Divergence

## 1. Architectural Foundations: Evolution of Loss Recovery
When a packet is dropped by an intermediate network buffer, how should the TCP congestion control state machine respond?
The historical evolution of TCP loss recovery is defined by the transition from **TCP Tahoe (1988)** to **TCP Reno (1990)**.

```
       cwnd ^
            |                               TAHOE: COLLAPSES TO 1 MSS
            |                                           |
            |                         *                 v
            |                     *   |   *            |*| (Re-enters Slow Start from 1)
            |                 *       |       *       * |
            |             *           |           *     |
            |         *               |                 |
            |     *                   |                 |
            | *                       |                 |
            +-------------------------+-----------------+---------------------> Time
                                 (Packet Loss)

       cwnd ^
            |                               RENO: HALVES TO ssthresh (FAST RECOVERY)
            |                                           |
            |                         *                 v
            |                     *   |   *           * * * * (Maintains in-flight pipe!)
            |                 *       |       *     *
            |             *           |           *
            |         *               |
            |     *                   |
            | *                       |
            +-------------------------+---------------------------------------> Time
                                 (Packet Loss)
```

---

## 2. TCP Tahoe (1988): The Hard Reset
Under TCP Tahoe (RFC 1122), whenever loss is detected—whether via **Retransmission Timeout (RTO)** OR via **3 Duplicate ACKs**:
1. Save half the window: $ssthresh \leftarrow \max(\frac{cwnd}{2}, 2 \times \text{MSS})$.
2. Retransmit the missing segment.
3. **Hard Reset**: $cwnd \leftarrow 1 \text{ MSS}$!
4. Re-enter **Slow Start** from scratch until $cwnd$ reaches the new $ssthresh$.

### The Tahoe Pathology
Resetting $cwnd$ to 1 MSS on 3 Duplicate ACKs is completely unnecessary! The arrival of duplicate ACKs proves that **packets are still successfully reaching the receiver** and clearing the network bottleneck.
Collapsing the pipeline forces the sender to go idle, causing severe sawtooth throughput oscillations.

---

## 3. TCP Reno (1990): Fast Recovery
TCP Reno introduced **Fast Recovery** (RFC 2001, RFC 5681) to keep the pipeline full when loss occurs without RTO timeouts.

### The Reno Fast Recovery Protocol
When the 3rd Duplicate ACK arrives:
1. Set $ssthresh \leftarrow \max(\frac{\text{FlightSize}}{2}, 2 \times \text{MSS})$.
2. Retransmit the missing segment (Fast Retransmit).
3. **Inflate the Congestion Window**:
   $$cwnd \leftarrow ssthresh + 3 \times \text{MSS}$$
   (Why $+3$? Because 3 packets have successfully cleared the network to generate the 3 duplicate ACKs!).
4. For each **additional Duplicate ACK** received:
   $$cwnd \leftarrow cwnd + 1 \text{ MSS}$$
   (If permitted by the new inflated $cwnd$, transmit a new data packet).
5. When the **Full Cumulative ACK** arrives (acknowledging the retransmitted data):
   - **Deflate the Window**: $cwnd \leftarrow ssthresh$.
   - Exit Fast Recovery and resume **Congestion Avoidance**.

---

## 4. Mathematical Comparison of Average Throughput
Let $W_{\max}$ be the maximum window size before loss occurs, and let RTT be constant.

### 1. TCP Tahoe Average Throughput
Tahoe drops from $W_{\max}$ to 1, then spends $k_1$ RTTs in Slow Start and $k_2$ RTTs in Congestion Avoidance:
$$\text{Average Window}_{\text{Tahoe}} \approx 0.5 \times W_{\max}$$

### 2. TCP Reno Average Throughput
Reno oscillates strictly between $\frac{W_{\max}}{2}$ and $W_{\max}$ in a continuous linear sawtooth:
$$\text{Average Window}_{\text{Reno}} = \frac{\frac{W_{\max}}{2} + W_{\max}}{2} = \frac{3}{4} W_{\max} = 0.75 \times W_{\max}$$
**TCP Reno achieves 50% higher average throughput than TCP Tahoe on identical network links!**

---

## 5. Production Masterclass: Compilable C Tahoe vs Reno Loss Engine

Save as `tahoe_vs_reno.c` and compile with `gcc -Wall -Wextra -O2 tahoe_vs_reno.c -o tahoe_vs_reno`:

```c
#include <stdio.h>
#include <stdlib.h>

#define MSS 1460

void simulate_loss_reaction(const char *flavor, int is_reno, uint32_t cwnd_at_loss) {
    printf("====================================================\n");
    printf("SIMULATING 3-DUPACK LOSS REACTION: %s\n", flavor);
    printf("cwnd at moment of loss: %u bytes (%u packets)\n", cwnd_at_loss, cwnd_at_loss / MSS);
    printf("====================================================\n");

    uint32_t ssthresh = cwnd_at_loss / 2;
    uint32_t cwnd;

    if (!is_reno) {
        // TAHOE: Hard reset to 1 MSS
        cwnd = 1 * MSS;
        printf("[Tahoe Action] Reset cwnd = 1 MSS (%u bytes) -> Re-entering Slow Start!\n", cwnd);
    } else {
        // RENO: Fast Recovery with inflation
        cwnd = ssthresh + 3 * MSS;
        printf("[Reno Action] Fast Recovery entered!\n");
        printf("  ssthresh set to : %u bytes\n", ssthresh);
        printf("  cwnd inflated to: %u bytes (ssthresh + 3*MSS)\n", cwnd);

        // Simulate receiving 2 more duplicate ACKs
        cwnd += MSS;
        printf("  Additional DupACK 4 -> cwnd = %u bytes\n", cwnd);
        cwnd += MSS;
        printf("  Additional DupACK 5 -> cwnd = %u bytes\n", cwnd);

        // Cumulative ACK arrives
        cwnd = ssthresh;
        printf("[Reno Action] Cumulative ACK received -> Deflated cwnd to %u bytes -> Resuming Linear Avoidance!\n", cwnd);
    }
}

int main(void) {
    uint32_t cwnd_loss = 40 * MSS; // Loss occurs at 40 packets (58.4 KB)
    simulate_loss_reaction("TCP Tahoe", 0, cwnd_loss);
    printf("\n");
    simulate_loss_reaction("TCP Reno", 1, cwnd_loss);
    return 0;
}
```

---

## 6. Production Post-Mortem: The Reno Multi-Drop Stall
### The Flaw
While Reno is vastly superior to Tahoe for single packet drops, it exhibits a fatal architectural flaw when **multiple packets are dropped within the same window**:
If packets 5 and 7 are dropped:
1. Fast Retransmit recovers packet 5.
2. When the ACK for packet 5 returns, it only acknowledges up to packet 6 (because packet 7 is still missing).
3. Under original Reno, this partial ACK **exits Fast Recovery**.
4. The sender stalls because it has no duplicate ACKs left to trigger a second Fast Retransmit!
5. The connection sits idle until the **Retransmission Timeout (RTO)** fires, collapsing $cwnd$ back to 1 MSS.
This critical limitation led directly to the development of **TCP NewReno** and **SACK**.---

## 7. The Mathis Formula: Theoretical Throughput Limit of TCP Reno
In 1997, Matthew Mathis, Jeffrey Semke, and Jamshid Mahdavi published the definitive mathematical model describing TCP Reno's throughput under periodic packet loss $p$:

$$\text{Throughput} \le \frac{\text{MSS}}{\text{RTT}} \times \frac{C}{\sqrt{p}}$$

where:
- $\text{MSS}$: Maximum Segment Size in bytes.
- $\text{RTT}$: Round-Trip Time in seconds.
- $p$: Fraction of packets lost ($0 < p < 1$).
- $C$: Constant derived from AIMD geometry:
  $$C = \sqrt{\frac{3}{2}} \approx 1.22$$

### The Mathis Scaling Implication
Because throughput scales with $\frac{1}{\sqrt{p}}$:
- To achieve a **10x increase in throughput**, packet loss must drop by a factor of **100x**!
- On a 10 Gbps 100ms link, maintaining line rate requires a packet loss rate of less than:
  $$p < 10^{-11} \quad (\text{one lost packet per 100 billion packets sent!})$$
This mathematical ceiling proved that standard Reno AIMD cannot scale to multi-gigabit speeds, driving the creation of Cubic and BBR.---

## 8. The Fast Recovery State Machine in the Linux Kernel
In `net/ipv4/tcp_input.c`, the Linux kernel tracks five distinct Congestion Avoidance states:
1. **`TCP_CA_Open`**: Normal operational state. No duplicate ACKs; window grows per Slow Start or Avoidance.
2. **`TCP_CA_Disorder`**: Receiving 1 or 2 duplicate ACKs. Suspects minor packet reordering.
3. **`TCP_CA_Recovery`**: 3 Duplicate ACKs received. Reno Fast Recovery engaged. $cwnd$ is inflated, missing packet retransmitted.
4. **`TCP_CA_Loss`**: Retransmission timeout (RTO) expired. $cwnd$ collapsed to 1 MSS, Slow Start restarted.
5. **`TCP_CA_CWR`**: Congestion Window Reduced (triggered by ECN CE mark).
---

## 7. Mathematical Proof: The Mathis Formula & Throughput Upper Bound

In 1997, Matthew Mathis, Jeffrey Semke, and Jamshid Mahdavi published a seminal paper establishing the fundamental physical throughput bound for any AIMD congestion control algorithm (like TCP Reno).

Let:
- $W$ = Maximum congestion window in packets
- $p$ = Packet loss probability
- $	ext{RTT}$ = Round-trip time in seconds
- $	ext{MSS}$ = Maximum segment size in bytes

In Reno, the window cycles between $W/2$ and $W$.
The average window size is $rac{3}{4}W$.
The duration of each sawtooth cycle is $rac{W}{2}$ round trips.
The number of packets delivered in one sawtooth cycle is the area under the curve:
$$	ext{Packets} = rac{1}{2} \left( rac{W}{2} + W ight) 	imes rac{W}{2} = rac{3}{8} W^2$$
Because one packet drop terminates each cycle, the loss probability is:
$$p = rac{1}{	ext{Packets}} = rac{8}{3 W^2} \implies W = \sqrt{rac{8}{3p}}$$

Substituting $W$ into average bandwidth gives the famous **Mathis Formula**:
$$	ext{Throughput} = rac{	ext{MSS}}{	ext{RTT}} 	imes rac{C}{\sqrt{p}} \quad 	ext{where } C = \sqrt{rac{3}{2}} pprox 1.22$$

### Architectural Consequence of Mathis Formula
Look at the formula: **Throughput is inversely proportional to RTT and $\sqrt{p}$**!
If you have a 10 Gbps transatlantic link (100ms RTT), to achieve full 10 Gbps throughput with standard TCP Reno, the required packet loss rate must be:
$$p < 2 	imes 10^{-11}$$
That means the network can drop at most **1 packet every 50 billion packets**! In the real world, optical fiber and router switches cannot sustain such low loss rates. This mathematical wall proved that TCP Reno is physically incapable of scaling to high-speed broadband networks, directly motivating the creation of TCP CUBIC and BBR.

---

## 8. Production War Story: The 3-Duplicate ACK Race Condition
In 2019, a cloud database replication pipeline suffered high tail latencies.
Engineers observed that whenever a single packet was dropped, instead of entering Fast Retransmit, connections consistently stalled for 200ms in an RTO timeout.
Investigation revealed that the database synchronization process was sending batches of only **3 packets** at a time!
If Packet 1 was delivered and Packet 2 was lost, Packet 3 generated only **1 duplicate ACK**.
Because Fast Retransmit strictly requires **3 duplicate ACKs** before triggering, the sender never entered Fast Recovery and had to wait for the sluggish RTO timer to expire!
Fix: The Linux kernel now implements **Limited Transmit** (RFC 3042) and **Early Retransmit** (RFC 5827), which dynamically lower the duplicate ACK threshold when the congestion window is small.
