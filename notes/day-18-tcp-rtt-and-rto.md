# Day 18: TCP RTT Estimation (Jacobson) & RTO Timers

## 1. Architectural Foundations: Retransmission Timeout (RTO)

If a TCP segment or its acknowledging ACK is dropped by a congested router, how does the sender detect the loss?
The sender arms a **Retransmission Timer (RTO Timer)** for each unacknowledged segment. If the timer expires before an ACK arrives, the sender assumes the segment was lost and retransmits it.

Setting the RTO is a delicate balancing act:
- **RTO Too Short**: Spurious retransmissions waste network bandwidth and trigger unnecessary congestion window collapse.
- **RTO Too Long**: Recovery from lost packets is sluggish, devastating throughput.

Because internet latency fluctuates dynamically, **the RTO must adapt dynamically to measured Round Trip Times (RTT)**.

---

## 2. Van Jacobson's 1988 Algorithm (RFC 6298)

In 1988, Van Jacobson showed that tracking only mean RTT failed under heavy network load because variance spiked dramatically. He introduced the algorithm used in all modern operating systems:

### Mathematical Formulations:
1. **Measured Sample**: $R$ (measured RTT for an un-retransmitted segment).
2. **Smoothed RTT ($SRTT$)**: An Exponentially Weighted Moving Average (EWMA) with smoothing factor $\alpha = 1/8 = 0.125$:

$$SRTT_{new} = (1 - \alpha) \times SRTT_{old} + \alpha \times R$$

3. **RTT Variation ($RTTVAR$)**: Mean absolute deviation with smoothing factor $\beta = 1/4 = 0.25$:

$$RTTVAR_{new} = (1 - \beta) \times RTTVAR_{old} + \beta \times |SRTT_{old} - R|$$

4. **Retransmission Timeout ($RTO$)**:

$$RTO = \max\left(RTO_{min},\; SRTT + 4 \times RTTVAR\right)$$

In Linux, $RTO_{min}$ is clamped to **200 milliseconds** (`TCP_RTO_MIN`), and $RTO_{max}$ is **120 seconds** (`TCP_RTO_MAX`).

---

## 3. Phil Karn's Algorithm (RFC 6298)

Suppose a segment is sent at $t=0$. At $t=1.0\text{s}$, RTO expires and the segment is retransmitted. At $t=1.1\text{s}$, an ACK arrives.
**Did this ACK acknowledge the FIRST transmission ($RTT = 1.1\text{s}$) or the SECOND transmission ($RTT = 0.1\text{s}$)?**

This is **Karn's Ambiguity Problem**.
**Karn's Rule 1**: Do NOT update $SRTT$ or $RTTVAR$ from retransmitted segments!
**Karn's Rule 2**: When an RTO timeout occurs, apply **Exponential Backoff**:

$$RTO_{new} = 2 \times RTO_{old}$$
