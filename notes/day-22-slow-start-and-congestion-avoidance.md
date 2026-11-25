# Day 22: Slow Start & Congestion Avoidance Math

## 1. Architectural Foundations: Congestion Window Mechanics
To implement Van Jacobson's packet conservation principle, TCP maintains a private state variable called the **Congestion Window (`cwnd`)**.
While the Advertised Window (`RCV.WND`) reflects the receiver's buffer space, `cwnd` reflects the **inferred capacity of the network pipe**.

The sender's effective transmission window is strictly bounded:
$$W_{\text{eff}} = \min(cwnd, RCV.WND)$$

TCP transmission operates across two alternating mathematical phases:
1. **Slow Start**: Rapid exponential capacity discovery.
2. **Congestion Avoidance**: Cautious linear probing.

```
       cwnd ^
            |                                           (Loss Detected! Cut ssthresh=cwnd/2)
            |                                                      *
            |                                                  *
            |                                              *  (Linear Growth: +1 MSS / RTT)
            |                                          *
            |                        ssthresh ------*---------------------------------
            |                                      *
            |                                  *  (Slow Start: Exponential Growth x2 / RTT)
            |                              *
            |                        *
            |                 *
            |         *
            |    *
            +-------------------------------------------------------------> Time
```

---

## 2. Slow Start: Exponential Capacity Discovery
When a TCP connection begins, the sender has zero knowledge of the bottleneck link capacity. Transmitting an immediate full-speed burst would instantly overwhelm router buffers.

### The Initial Window ($IW$)
- RFC 793 (Historical): $IW = 1 \text{ MSS}$ (536 - 1460 bytes).
- RFC 2581 (1999): $IW = 2 \dots 4 \text{ MSS}$.
- RFC 6928 (2013 - Modern Linux Default): **$IW = 10 \text{ MSS}$** (~14.6 KB).
  - Google research proved that $IW = 10$ reduces HTTP page load times by over 10% worldwide by fitting typical web assets into a single RTT burst.

### The Slow Start Equation
In Slow Start, for **every individual ACK received**, $cwnd$ is incremented by 1 MSS:
$$cwnd \leftarrow cwnd + 1 \text{ MSS}$$
If the sender transmits a window of $W$ packets, the receiver returns $W$ acknowledgments.
Because each ACK increments $cwnd$ by 1:
$$W_{\text{next}} = W + W = 2 \times W$$
The congestion window **doubles every single Round-Trip Time (RTT)**:
$$cwnd(k) = IW \times 2^k \quad (\text{where } k \text{ is the RTT index})$$

---

## 3. Congestion Avoidance: Linear Probing
When $cwnd$ reaches the **Slow Start Threshold (`ssthresh`)**, exponential growth halts to prevent router buffer overflow. The connection enters **Congestion Avoidance**.

### The Congestion Avoidance Equation
In Congestion Avoidance, the window increases by **at most 1 MSS per RTT**, regardless of how many ACKs return:
For each incoming ACK:
$$cwnd \leftarrow cwnd + \frac{MSS \times MSS}{cwnd}$$
After an entire window of $N = \frac{cwnd}{MSS}$ ACKs returns:
$$\Delta cwnd = N \times \frac{MSS^2}{cwnd} = \frac{cwnd}{MSS} \times \frac{MSS^2}{cwnd} = 1 \text{ MSS per RTT}$$

### Mathematical Proof of Time to Saturate Pipe
Let the bottleneck capacity be $C$ bytes.
The time $T_{\text{ss}}$ required to reach $C$ during Slow Start is logarithmic:
$$C = IW \times 2^{k} \implies k = \log_2\left(\frac{C}{IW}\right) \implies T_{\text{ss}} = RTT \times \log_2\left(\frac{C}{IW}\right)$$
For a 100 MB link ($C = 10^8\text{ B}$, $IW = 14,600\text{ B}$, $RTT = 50\text{ms}$):
$$k = \log_2\left(\frac{100,000,000}{14,600}\right) \approx \log_2(6849) \approx 12.74 \text{ RTTs}$$
$$T_{\text{ss}} = 12.74 \times 50\text{ ms} \approx 637\text{ ms}$$
Slow Start saturates high-speed pipes in less than one second!

---

## 4. Production Masterclass: Compilable C Slow Start & Avoidance Simulator

Save as `slow_start_sim.c` and compile with `gcc -Wall -Wextra -O2 slow_start_sim.c -o slow_start_sim`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define MSS 1460

typedef struct {
    uint32_t cwnd;
    uint32_t ssthresh;
    int      in_slow_start;
} tcp_congestion_state_t;

void init_connection(tcp_congestion_state_t *s, uint32_t init_cwnd, uint32_t init_ssthresh) {
    s->cwnd = init_cwnd;
    s->ssthresh = init_ssthresh;
    s->in_slow_start = (s->cwnd < s->ssthresh);
}

void on_ack_received(tcp_congestion_state_t *s) {
    if (s->cwnd < s->ssthresh) {
        // SLOW START: Add 1 MSS per ACK (Doubles per RTT)
        s->cwnd += MSS;
        s->in_slow_start = 1;
    } else {
        // CONGESTION AVOIDANCE: Linear growth (+1 MSS per RTT)
        s->in_slow_start = 0;
        // Integer fixed-point math: add (MSS * MSS) / cwnd
        uint32_t inc = ((uint64_t)MSS * MSS) / s->cwnd;
        if (inc == 0) inc = 1; // Prevent integer division underflow
        s->cwnd += inc;
    }
}

int main(void) {
    printf("====================================================\n");
    printf("TCP SLOW START & CONGESTION AVOIDANCE SIMULATOR\n");
    printf("MSS = %d bytes | Initial cwnd = %d bytes (10 MSS)\n", MSS, 10 * MSS);
    printf("====================================================\n");

    tcp_congestion_state_t state;
    init_connection(&state, 10 * MSS, 64 * 1024); // ssthresh at 64 KB

    printf("Starting ssthresh = %u bytes (%.1f KB)\n\n",
           state.ssthresh, (double)state.ssthresh / 1024.0);

    // Simulate RTT rounds
    for (int rtt = 1; rtt <= 10; rtt++) {
        uint32_t window_at_start = state.cwnd;
        uint32_t packets_in_flight = window_at_start / MSS;

        // Process ACKs for all packets sent in this RTT
        for (uint32_t i = 0; i < packets_in_flight; i++) {
            on_ack_received(&state);
        }

        printf("RTT %2d: cwnd = %6u bytes (%3u pkts) | Phase: %s\n",
               rtt, state.cwnd, state.cwnd / MSS,
               state.in_slow_start ? "SLOW START (Exponential)" : "CONGESTION AVOIDANCE (Linear)");
    }

    return 0;
}
```

---

## 5. Production Post-Mortem: The tcp_slow_start_after_idle Latency Stall
### The Outage
A high-throughput financial trading API reported that HTTP/1.1 keep-alive connections exhibited severe 150ms latency spikes if requests were spaced more than 2 seconds apart. Active continuous requests were processed in 5ms.

### Root Cause Analysis
The Linux kernel possessed the legacy sysctl parameter:
`net.ipv4.tcp_slow_start_after_idle = 1` (default enabled).
When an established connection remains idle for longer than 1 RTO, Linux destroys the accumulated congestion window and **forces the connection back into Slow Start ($cwnd \leftarrow 10 \text{ MSS}$)**!
When a subsequent large request arrived, the sender stalled waiting for Slow Start round-trips to rebuild the window.

### Remediation
Disable idle slow-start reset across all production application servers:
```bash
sysctl -w net.ipv4.tcp_slow_start_after_idle=0
```
This preserves the negotiated congestion window across idle periods on keepalive connections, collapsing p99 latencies back to 5ms.---

## 6. Hybrid Slow Start (HyStart) in Modern Linux
Standard Slow Start continues doubling $cwnd$ until a **packet is dropped**. In modern high-speed networks, dropping packets when $cwnd$ is huge creates massive line stalls.

Linux implements **HyStart (Hybrid Slow Start)** to exit Slow Start **BEFORE** packets drop:
1. **Delay Increase Detection**:
   - Tracks the minimum RTT ($RTT_{\min}$) in the first round.
   - In subsequent rounds, if the observed RTT exceeds $RTT_{\min}$ by a threshold:
     $$\Delta RTT \ge \min\left(\frac{RTT_{\min}}{8}, 16\text{ ms}\right)$$
   - The kernel detects that queue buffers are beginning to fill!
2. **Action**:
   - Linux exits Slow Start early, transitions immediately to Congestion Avoidance, and begins linear growth, **preventing a single packet from being dropped**!---

## 7. TCP Pacing & `SO_MAX_PACING_RATE`
In high-speed networks, Slow Start doubling can cause microbursts: sending 100 packets back-to-back at 100 Gbps line rate can overwhelm a 1 Gbps access switch buffer in 10 microseconds.

To prevent microburst queue buildup, modern Linux uses **Fair Queueing (FQ) Pacing** (`qdisc fq`):
- Packets are scheduled across time rather than dumped onto the wire all at once.
- Applications can enforce maximum bandwidth pacing per socket:
  ```c
  unsigned long rate_bytes_per_sec = 100 * 1024 * 1024; // 100 MB/s
  setsockopt(sock_fd, SOL_SOCKET, SO_MAX_PACING_RATE, &rate_bytes_per_sec, sizeof(rate_bytes_per_sec));
  ```
Pacing smooths packet departures into a continuous, uniform stream, eliminating router queue spikes.
---

## 7. Deep Architectural Mechanics: ACK Clocking & Initial Window Evolution

### The Self-Clocking Engine (Self-Pacing)
TCP's greatest strength is that the sender does not need an explicit timer for every packet. Instead, the arrival of ACKs forms an **ACK Clock**:
1. When a packet passes through the slowest router on the path (the bottleneck), the router transmits packets one by one with a time spacing $\Delta t = \text{Packet Size} / \text{Bandwidth}$.
2. The receiver receives packets separated by $\Delta t$ and emits ACKs separated by $\Delta t$.
3. When these ACKs arrive at the sender, each ACK triggers the transmission of a new packet.
4. Result: The sender automatically paces its output to match the exact physical bandwidth of the bottleneck link!

```
Sender blasters packets ---> [Router Bottleneck Buffer] ---> Receiver
                                     |
                                  Spacing: delta_t
                                     |
Sender <--- ACKs spaced by delta_t <--- Receiver
```

### The Evolution of TCP Initial Window (`initcwnd`)
How many packets should a TCP connection send in its very first round trip before receiving any ACKs?
1. **RFC 1122 (1989)**: `initcwnd = 1 MSS` (typically 1460 bytes). Extreme safety, but terrible for web browsing. A simple 10 KB web page required 4 sequential round trips!
2. **RFC 3390 (2002)**: `initcwnd = 4 MSS` ($pprox 5.8$ KB). Allowed small HTTP responses to complete in 2 RTTs.
3. **RFC 6928 (2013 - Google Proposal)**: `initcwnd = 10 MSS` ($pprox 14.6$ KB).
   - In 2010, Google measured billions of search and web queries and proved that `initcwnd = 10` reduced average web page latency by $10\%$ globally with negligible packet drop impact.
   - Modern Linux kernels default to `initcwnd 10`.

### Complete Compilable C Program: Inspecting Socket `initcwnd` and TCP Info
```c
/*
 * tcp_info_inspector.c - Reads kernel TCP state metrics via getsockopt
 * Compile: gcc -O2 -Wall tcp_info_inspector.c -o tcp_info_inspector
 */
#include <stdio.h>
#include <stdlib.h>
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

    struct tcp_info info;
    socklen_t len = sizeof(info);
    if (getsockopt(sock, IPPROTO_TCP, TCP_INFO, &info, &len) == 0) {
        printf("=========================================\n");
        printf("LINUX KERNEL TCP_INFO SOCKET AUDIT\n");
        printf("=========================================\n");
        printf("Sender cwnd        : %u MSS\n", info.tcpi_snd_cwnd);
        printf("Sender ssthresh    : %u MSS\n", info.tcpi_snd_ssthresh);
        printf("Smooth RTT (SRTT)  : %u us\n", info.tcpi_rtt);
        printf("RTT Variance       : %u us\n", info.tcpi_rttvar);
        printf("=========================================\n");
    }

    close(sock);
    return 0;
}
```

---

## 8. Production War Story: The Slow Start Restart (SSR) Performance Mystery
In 2017, a media streaming startup noticed that video segments experienced erratic 300ms buffering stalls every 15 seconds, despite clients having 100 Mbps fiber internet.
Wireshark packet captures revealed that after downloading a 2 MB video chunk, the connection sat idle for 5 seconds while the client played video.
When the next chunk was requested, the server reset its congestion window from 80 MSS back to 1 MSS!
The culprit was Linux's legacy sysctl:
```bash
net.ipv4.tcp_slow_start_after_idle = 1
```
When enabled, Linux resets `cwnd` to the initial window whenever a connection is idle for longer than 1 RTO.
In modern web applications with persistent HTTP/2 and keep-alive connections, this causes severe throughput penalty. Setting `net.ipv4.tcp_slow_start_after_idle = 0` eliminated the buffering pauses completely.
