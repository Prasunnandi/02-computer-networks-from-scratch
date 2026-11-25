# Day 26: Google BBR: Delay vs Bandwidth Optimization

## 1. Architectural Foundations: Model-Based Congestion Control
For three decades, TCP congestion control algorithms (Tahoe, Reno, NewReno, Cubic) were strictly **loss-based**: they treated packet loss as the sole indicator of network congestion.

In 2016, Neal Cardwell, Yuchung Cheng, C. Stephen Gunn, Soheil Hassas Yeganeh, and Van Jacobson at Google introduced **BBR (Bottleneck Bandwidth and Round-trip propagation time)**.
BBR fundamentally rejects the loss-based paradigm:
1. Packet loss does **NOT** equal congestion (e.g. Wi-Fi frame errors drop packets without network queues).
2. Large router buffers do **NOT** prevent loss; they create massive queuing latency (**Bufferbloat**).

```
        Delivery Rate ^
                      |            MAXIMUM BOTTLENECK BANDWIDTH (BtlBw)
                      |                   +----------------------------------
                      |                  /| (Queue builds up! High delay!)
                      |                 / |
                      |                /  |
                      |               /   |
                      |              /    |
                      +-------------+-----+----------------------------------> In-Flight Data
                                    |     |
                                    v     v
                            OPTIMAL POINT  BUFFER FULL (Packet Loss!)
                            (BDP = BtlBw * RTprop)
                            - Max Throughput
                            - Min Delay
                            - Zero Queue!
```

---

## 2. The Kleinrock Optimal Operating Point
In 1979, Leonard Kleinrock proved that the optimal operating point for any packet-switched communication system occurs at the inflection point where:
$$\text{Delivery Rate} = \text{Maximum Bottleneck Bandwidth } (BtlBw)$$
$$\text{Round-Trip Time} = \text{Minimum Physical Propagation Delay } (RTprop)$$

At this point:
- The amount of data in flight matches the link capacity exactly: $\text{FlightSize} = BtlBw \times RTprop = \text{BDP}$.
- Router queues are **completely empty** ($\text{Queue Delay} = 0$).
- Transmission throughput is at physical **100% line rate**.

### The Uncertainty Principle of Networks
A sender cannot measure $BtlBw$ and $RTprop$ simultaneously!
- To measure $BtlBw$, the sender must send faster to fill the pipe, which creates a queue and inflates RTT.
- To measure $RTprop$, the sender must drain the queue, which reduces sending rate and starves the pipe.
BBR overcomes this by **alternating state phases over time**.

---

## 3. The Four Phases of the BBR State Machine

```
+----------------------------------------------------------------------------+
| BBR STATE PHASES:                                                          |
|                                                                            |
| 1. STARTUP: Exponentially doubles sending rate (Pacing Gain 2.89) until    |
|             delivery rate plateaus (discovers BtlBw).                      |
|                                                                            |
| 2. DRAIN: Slows sending rate (Pacing Gain 0.35) to drain the queue created |
|           during Startup.                                                  |
|                                                                            |
| 3. PROBE_BW: Cycles through an 8-phase gain cycle:                         |
|              [1.25, 0.75, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]                    |
|              - 1.25 probes for higher bandwidth.                           |
|              - 0.75 drains any created queue.                              |
|              - 1.0 runs at pure equilibrium line rate.                     |
|                                                                            |
| 4. PROBE_RTT: Every 10 seconds, cuts in-flight data to 4 packets for 200ms |
|               to completely drain queues and refresh RTprop.               |
+----------------------------------------------------------------------------+
```

---

## 4. Production Masterclass: Compilable C BBR Bandwidth & Delay Estimator

Save as `bbr_engine.c` and compile with `gcc -Wall -Wextra -O2 bbr_engine.c -o bbr_engine`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <float.h>

typedef struct {
    double btl_bw;   // Max delivery rate (MB/s)
    double rt_prop;  // Min physical RTT (ms)
    double bdp;      // Bandwidth-Delay Product (MB)
    const char *state;
} bbr_state_t;

void update_bbr(bbr_state_t *bbr, double sample_delivery_rate_mb, double sample_rtt_ms) {
    // 1. Update max filter for Bottleneck Bandwidth
    if (sample_delivery_rate_mb > bbr->btl_bw) {
        bbr->btl_bw = sample_delivery_rate_mb;
    }

    // 2. Update min filter for RTprop
    if (sample_rtt_ms < bbr->rt_prop) {
        bbr->rt_prop = sample_rtt_ms;
    }

    // 3. Compute Kleinrock Optimal BDP
    // BDP (MB) = Bandwidth (MB/s) * Delay (seconds)
    bbr->bdp = bbr->btl_bw * (bbr->rt_prop / 1000.0);
}

int main(void) {
    printf("====================================================\n");
    printf("GOOGLE BBR CONGESTION CONTROL MODEL ENGINE\n");
    printf("====================================================\n");

    bbr_state_t bbr = { .btl_bw = 0.0, .rt_prop = DBL_MAX, .bdp = 0.0, .state = "STARTUP" };

    // Simulate varying network conditions:
    // Packet samples: { delivery_rate (MB/s), RTT (ms) }
    double samples[][2] = {
        { 50.0,  45.0 }, // Probe 1
        { 120.0, 42.0 }, // Probe 2: Discovers higher bandwidth!
        { 180.0, 40.0 }, // Probe 3: Discovers lower latency!
        { 180.0, 75.0 }, // Probe 4: Queue build up (ignored by RTprop min-filter)
        { 185.0, 41.0 }  // Probe 5: Peak bandwidth discovered
    };

    for (int i = 0; i < 5; i++) {
        update_bbr(&bbr, samples[i][0], samples[i][1]);
        printf("[Round %d] Sample: %5.1f MB/s, %4.1f ms -> BtlBw: %5.1f MB/s | RTprop: %4.1f ms | Target BDP: %.2f MB\n",
               i + 1, samples[i][0], samples[i][1], bbr.btl_bw, bbr.rt_prop, bbr.bdp);
    }

    printf("\n[SUCCESS] BBR target in-flight data set to exactly %.2f MB (Zero queue!)\n", bbr.bdp);
    return 0;
}
```

---

## 5. Production Post-Mortem: YouTube Global Throughput Acceleration
### The Deployment
When Google rolled out BBR across YouTube edge server clusters worldwide:
- **Throughput Gains**: Global network throughput increased by an average of **4%**, and by over **14% in developing countries** where wireless links suffer non-congestion random packet loss.
- **Latency Collapse**: Median round-trip time dropped by **33%** across all client connections, completely eliminating the 100ms - 500ms buffering queues generated by Cubic on cellular networks.---

## 6. The BBR Pacing Rate & Window Formulations
Unlike standard TCP which transmits data in bursts whenever ACKs arrive, BBR enforces strict **inter-packet pacing**:

$$\text{Pacing Rate} = BtlBw \times \text{Pacing Gain}$$
$$\text{Target Congestion Window } (cwnd) = BDP \times \text{Cwnd Gain} = (BtlBw \times RTprop) \times \text{Cwnd Gain}$$

### The 8-Phase Pacing Gain Cycle in PROBE_BW
In the steady-state `PROBE_BW` mode, BBR cycles through 8 distinct phases, each lasting for 1 round trip:
$$\text{Pacing Gain Vector} = [1.25, 0.75, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]$$
1. **Gain 1.25**: Sends 25% faster than the measured bottleneck rate to check if link capacity has increased.
2. **Gain 0.75**: Sends 25% slower than the measured rate to deliberately drain the queue created by phase 1.
3. **Gain 1.0 (x6)**: Operates at the exact estimated bottleneck bandwidth for 6 round trips.
This cycle guarantees periodic bandwidth discovery while ensuring long-term average queue length remains at zero.
---

## 7. Deep Architectural Mechanics: BBR State Machine & Pacing Engine

### The 4 Phases of Google BBR
Unlike loss-based algorithms that react after packet drops occur, BBR continuously operates a 4-state engine:
1. **`STARTUP`**:
   - Paces data with a gain of $2 / \ln(2) pprox 2.885$ (doubles sending rate every RTT).
   - Once 3 consecutive rounds fail to increase estimated `BtlBw` by more than $25\%$, BBR knows the physical bottleneck bandwidth has been discovered.
2. **`DRAIN`**:
   - Paces data with a gain of $1 / 2.885 pprox 0.347$.
   - Intentionally sends data slower than the bottleneck capacity to bleed off any packet queue that formed in the router during `STARTUP`!
3. **`PROBE_BW`**:
   - The primary steady state. Cycles through an 8-phase gain cycle: `[1.25, 0.75, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]`.
   - The $1.25$ gain gently tests if more bandwidth became available; the $0.75$ gain immediately drains any excess queue.
4. **`PROBE_RTT`**:
   - Every 10 seconds, if `RTprop` has not been updated, BBR drops `cwnd` to **4 packets** for 200ms.
   - This drains all queues along the path to accurately measure the true physical wire propagation delay.

```
       +---------------------------------------------+
       |                  STARTUP                    |
       |  (Exponential probe: pacing_gain = 2.885)   |
       +---------------------------------------------+
                              |
                     [Pipe saturated]
                              v
       +---------------------------------------------+
       |                   DRAIN                     |
       |  (Bleed router queues: pacing_gain = 0.347) |
       +---------------------------------------------+
                              |
                      [Queue drained]
                              v
       +---------------------------------------------+
       |                 PROBE_BW                    | <----+
       |  (8-phase pacing cycle: 1.25 -> 0.75 -> 1.0)|      |
       +---------------------------------------------+      |
                              |                             |
                [10 seconds without min RTT]                |
                              v                             |
       +---------------------------------------------+      |
       |                 PROBE_RTT                   |      |
       |   (Drop cwnd to 4 packets to drain queue)   | -----+
       +---------------------------------------------+
```

### Complete Compilable C Program: Enabling BBR via Socket Options
```c
/*
 * enable_bbr_demo.c - Programmatically sets TCP_CONGESTION to BBR
 * Compile: gcc -O2 -Wall enable_bbr_demo.c -o enable_bbr_demo
 */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/tcp.h>
#include <netinet/in.h>

int main(void) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return 1;
    }

    char ca[16] = "bbr";
    if (setsockopt(sock, IPPROTO_TCP, TCP_CONGESTION, ca, strlen(ca)) == 0) {
        printf("Successfully set TCP Congestion Control algorithm to BBR!\n");
    } else {
        perror("setsockopt TCP_CONGESTION (Requires kernel module tcp_bbr)");
    }

    char current_ca[16] = {0};
    socklen_t len = sizeof(current_ca);
    getsockopt(sock, IPPROTO_TCP, TCP_CONGESTION, current_ca, &len);
    printf("Current Socket Congestion Algorithm: %s\n", current_ca);

    close(sock);
    return 0;
}
```

---

## 8. Production War Story: YouTube's Global Throughput Revolution
When Google deployed BBR to YouTube's global CDN in 2016, the results were astounding:
- On developing-world networks with high wireless packet loss (e.g. India and Brazil), video buffering delays dropped by **$33\%$**.
- In transatlantic and transpacific paths, throughput increased by **$200\% 	ext{ to } 2400\%$**!
Why such a massive improvement? In transcontinental wireless links, random Wi-Fi packet drops (0.5% loss) were constantly resetting CUBIC and Reno congestion windows to minimums. BBR ignored random packet drops and maintained maximum wire delivery rate, revolutionizing internet media delivery.
