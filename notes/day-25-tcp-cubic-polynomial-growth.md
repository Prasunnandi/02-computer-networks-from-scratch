# Day 25: TCP Cubic: Polynomial Growth on High BDP

## 1. Architectural Foundations: The High-BDP Wall of Standard TCP
In high-speed, long-distance networks known as **Long Fat Networks (LFNs)**, standard TCP Reno's linear growth model ($+1 \text{ MSS}$ per RTT) encounters a catastrophic mathematical limitation.

Consider an enterprise 100 Gbps cross-continental link with a Round-Trip Time of 80 milliseconds:
$$\text{BDP} = \frac{100 \times 10^9 \text{ bits/sec} \times 0.080 \text{ sec}}{8 \text{ bits/byte}} = 1,000,000,000 \text{ bytes (1 GB)}$$
$$\text{Window in 1460-Byte Packets} = \frac{10^9}{1460} \approx 685,000 \text{ packets}$$

If a single packet drop occurs, standard Reno cuts the window by 50% ($ssthresh = 342,500\text{ packets}$).
To recover that lost 50% using Reno's $+1$ packet per RTT linear growth:
$$\text{Time to Recover} = 342,500 \text{ RTTs} \times 0.080\text{ sec} = 27,400\text{ seconds} \approx \mathbf{7.6 \text{ HOURS}}!$$
A single lost packet requires **7.6 hours of zero-loss transmission** to reclaim full 100 Gbps speed! If another packet drops during those 7 hours, throughput collapses permanently.

---

## 2. The TCP Cubic Architecture (RFC 8312)
Designed by Injong Rhee and Lisong Xu, **TCP Cubic** has been the **default congestion control algorithm in the Linux kernel since version 2.6.19**.

Instead of increasing window size as a function of RTT counts, Cubic replaces the linear sawtooth with a **Cubic Polynomial Function of real elapsed wall-clock time ($t$)** since the last congestion event:

$$W_{\text{cubic}}(t) = C \times (t - K)^3 + W_{\max}$$

where:
- $t$: Elapsed wall-clock time since the last packet loss.
- $W_{\max}$: Congestion window size at the moment loss occurred.
- $C$: Scaling constant (standardized at **$0.4$**).
- $\beta$: Multiplicative decrease factor (set to **$0.7$**, less aggressive than Reno's $0.5$).
- $K$: Time period required to grow the window back to $W_{\max}$ without loss:
  $$K = \sqrt[3]{\frac{W_{\max} \times (1 - \beta)}{C}} = \sqrt[3]{\frac{W_{\max} \times 0.3}{0.4}}$$

```
       W(t) ^
            |                                           (Convex Probing: Fast discovery)
            |                                                      *
            |                                                 *
            |                 W_max --------------------*-------------------- (Inflection Point t = K)
            |                                      *  *  (Plateau: Stability around W_max)
            |                                 *
            |                           *
            |                     *  (Concave Growth: Fast recovery)
            |            *
            |   * (Loss: W_max * 0.7)
            +---+-----------------------------------+------------------------> Time (t)
                0                                   K
```

---

## 3. The Three Distinct Phases of the Cubic Curve

### 1. Concave Growth Phase ($t < K$)
Immediately after loss, $cwnd$ is at $\beta \times W_{\max}$.
Because $(t - K)$ is negative, $(t - K)^3$ is negative but rapidly approaches zero.
The window accelerates aggressively to reclaim lost bandwidth quickly!

### 2. Plateau Stability Phase ($t \approx K$)
Near the inflection point $t = K$, the derivative $\frac{dW}{dt} = 3C(t - K)^2 \approx 0$.
The growth rate slows to near zero. The sender lingers deliberately around $W_{\max}$, providing maximum throughput stability at the link's known capacity.

### 3. Convex Probing Phase ($t > K$)
If no loss occurs at $t = K$, the network has acquired more capacity.
For $t > K$, $(t - K)^3$ turns positive and grows with increasing acceleration, aggressively hunting for new available bandwidth.

---

## 4. Mathematical Proof of RTT Fairness
Under standard Reno, flows with short RTTs (e.g. 5ms) increase their window 20x faster than flows with long RTTs (e.g. 100ms), starving long-distance connections.
Because Cubic's formula depends **strictly on wall-clock time $t$ in seconds**, two competing flows with completely different RTTs follow the exact same growth curve, **achieving RTT fairness across heterogeneous internet paths**!

---

## 5. Production Masterclass: Compilable C TCP Cubic Window Generator

Save as `cubic_engine.c` and compile with `gcc -Wall -Wextra -O2 cubic_engine.c -lm -o cubic_engine`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define C_PARAM 0.4
#define BETA    0.7
#define MSS     1460

double calculate_K(double w_max) {
    return cbrt((w_max * (1.0 - BETA)) / C_PARAM);
}

double calculate_cubic_window(double t, double K, double w_max) {
    double time_diff = t - K;
    return C_PARAM * (time_diff * time_diff * time_diff) + w_max;
}

int main(void) {
    printf("====================================================\n");
    printf("TCP CUBIC POLYNOMIAL WINDOW GENERATOR (RFC 8312)\n");
    printf("====================================================\n");

    double w_max = 1000.0; // Window at loss: 1000 packets (~1.46 MB)
    double K = calculate_K(w_max);

    printf("Baseline: W_max = %.0f packets | K (Time to recover) = %.2f seconds\n\n", w_max, K);
    printf(" Time (s) | Cubic Window (pkts) | Bandwidth (MB) | Region / Dynamics\n");
    printf("----------+---------------------+----------------+-----------------------------\n");

    for (double t = 0.0; t <= K * 2.0; t += (K / 5.0)) {
        double w = calculate_cubic_window(t, K, w_max);
        const char *phase = "Concave (Fast Recovery)";
        if (fabs(t - K) < (K / 10.0)) phase = "Plateau (Stability @ W_max)";
        else if (t > K) phase = "Convex (Probing New Capacity)";

        printf("%8.2f  | %17.1f   | %12.2f   | %s\n",
               t, w, (w * MSS) / (1024.0 * 1024.0), phase);
    }

    return 0;
}
```

---

## 6. Production Post-Mortem: The Cloud Database Sync Stagnation
### The Outage
A multi-region Cassandra cluster replicating between US-East and AP-Southeast (Singapore, 180ms RTT) experienced replication lag falling 48 hours behind schedule over a 10 Gbps link.

### Root Cause Analysis
The OS image on the Singapore database nodes was pinned to a legacy operating system default (`net.ipv4.tcp_congestion_control = reno`).
Over the 180ms RTT link, minor 0.01% packet loss caused Reno to collapse its window and take hours to recover, achieving an average throughput of only **34 Mbps on a 10,000 Mbps line**!

### Remediation
Switched the congestion algorithm to Cubic:
```bash
sysctl -w net.ipv4.tcp_congestion_control=cubic
```
Replication throughput immediately surged from 34 Mbps to **9,100 Mbps**, eliminating the 48-hour backlog in 25 minutes.---

## 7. The Reno-Friendly Mode of TCP Cubic
When the network bottleneck is small (e.g. low bandwidth or short RTT), Cubic's polynomial curve might grow slower than standard Reno ($+1 \text{ MSS}$ per RTT).
To ensure Cubic never underperforms standard TCP, RFC 8312 specifies **Reno-Friendly Mode**:

At each ACK arrival, the kernel calculates:
1. The Cubic window: $W_{\text{cubic}}(t)$.
2. The standard Reno window estimate: $W_{\text{reno}}(t) = W_{\max} \times \beta + \frac{3 \times (1 - \beta)}{1 + \beta} \times \frac{t}{RTT}$.
3. The kernel selects the maximum:
   $$W_{\text{actual}} = \max(W_{\text{cubic}}(t), W_{\text{reno}}(t))$$

This mathematical hybrid ensures Cubic achieves maximum aggressiveness on high BDP pipes while retaining 100% competitive fairness on low-latency local networks.---

## 8. Tuning TCP Cubic via Linux sysctl
System administrators can fine-tune Cubic's aggressiveness and responsiveness:

```bash
# Verify currently active algorithm:
sysctl net.ipv4.tcp_congestion_control
# Output: net.ipv4.tcp_congestion_control = cubic

# View all available kernel algorithms:
sysctl net.ipv4.tcp_available_congestion_control
# Output: reno bbr cubic

# Dynamically set TCP window clamping and buffer allocation:
sysctl -w net.ipv4.tcp_rmem="4096 87380 33554432"
sysctl -w net.ipv4.tcp_wmem="4096 65536 33554432"
```
Setting maximum buffer sizes to 32 MB allows Cubic's polynomial growth to saturate 10 Gbps links effortlessly.
---

## 7. Deep Architectural Mechanics: Linux Kernel `tcp_cubic.c` Implementation

### The Linux Kernel CUBIC Data Structure
In the Linux kernel source tree (`net/ipv4/tcp_cubic.c`), CUBIC maintains a per-socket context structure:
```c
struct bictcp {
    u32 cnt;          /* Increase cwnd by 1 after cnt ACKs */
    u32 last_max_cwnd;/* Window size before last reduction */
    u32 loss_cwnd;    /* Maximal cwnd before current loss */
    u32 last_cwnd;    /* Window at last update */
    u32 bic_K;        /* Time period to reach last_max_cwnd (scaled) */
    u32 delay_min;    /* Minimum observed RTT */
    u32 epoch_start;  /* Beginning of current epoch in jiffies */
};
```

### The TCP-Friendly Region
CUBIC recognizes that on small networks with low BDP (e.g. 5ms ping on a local Wi-Fi router), traditional TCP Reno might actually grow faster than CUBIC's cubic polynomial during the plateau phase!
To ensure CUBIC never underperforms standard TCP Reno on traditional links, CUBIC implements a **TCP-Friendly Region**:
In every RTT, CUBIC calculates:
1. $W_{	ext{cubic}}(t) = C(t - K)^3 + W_{\max}$
2. $W_{	ext{reno}}(t) = W_{\max} eta + rac{3(1 - eta)}{1 + eta} 	imes rac{t}{	ext{RTT}}$
3. The actual window used is:
$$	ext{cwnd} = \max(W_{	ext{cubic}}(t), W_{	ext{reno}}(t))$$
This guarantees that CUBIC is strictly as fast as Reno on low-latency connections, and hundreds of times faster on high-speed long-distance fiber!

### Complete Compilable C Program: CUBIC Window Calculation Simulator
```c
/*
 * cubic_math_verify.c - Verifies RFC 8312 CUBIC window formula
 * Compile: gcc -O2 -Wall cubic_math_verify.c -lm -o cubic_math_verify
 */
#include <stdio.h>
#include <math.h>

int main(void) {
    double w_max = 1000.0; /* 1000 MSS pre-loss window */
    double beta = 0.2;     /* 20% multiplicative decrease */
    double C = 0.4;        /* CUBIC constant */

    /* Compute K = cbrt((w_max * beta) / C) */
    double K = cbrt((w_max * beta) / C);
    printf("=========================================\n");
    printf("CUBIC POLYNOMIAL MATHEMATICAL VERIFICATION\n");
    printf("=========================================\n");
    printf("Pre-loss Window (W_max) : %.1f MSS\n", w_max);
    printf("Post-loss Window (t=0)  : %.1f MSS\n", w_max * (1.0 - beta));
    printf("Recovery Time (K)       : %.3f seconds\n\n", K);

    printf("%-8s | %-14s | %-16s\n", "Time (s)", "CUBIC cwnd", "Trajectory");
    printf("-----------------------------------------\n");
    for (double t = 0.0; t <= K * 1.5; t += 1.0) {
        double diff = t - K;
        double w_cubic = C * (diff * diff * diff) + w_max;
        const char *traj = (t < K) ? "Concave Growth" : "Convex Probing";
        printf("%-8.1f | %-14.2f | %-16s\n", t, w_cubic, traj);
    }
    printf("=========================================\n");
    return 0;
}
```

---

## 8. Production War Story: The Fast-Convergence Intra-Data Center Cliff
In 2018, a distributed storage cluster running thousands of internal microservices experienced unexplained throughput collapse during cross-rack replication.
Traffic traces showed that when multiple parallel CUBIC flows competed, older flows that had reached large windows would violently throttle down whenever a newer flow caused packet drops.
CUBIC has a feature called **Fast Convergence**:
When a loss occurs, if the current $W_{\max} < 	ext{previous } W_{\max}$, CUBIC assumes link capacity has shrunk (due to competing traffic) and cuts $W_{\max}$ by an extra factor of $0.8$!
Inside low-latency data centers with deep-buffer switches, this triggered a cascade of over-reductions. Modern data centers often deploy DCTCP (Data Center TCP with ECN) or Google BBR to avoid CUBIC's loss-based backoff inside internal clusters.
