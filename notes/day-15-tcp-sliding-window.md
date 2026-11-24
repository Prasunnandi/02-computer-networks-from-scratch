# Day 15: TCP Sliding Window & Flow Control

## 1. Architectural Foundations: Flow Control vs Congestion Control
A fundamental requirement of any reliable transport protocol is preventing a fast sender from overwhelming a slow receiver. This mechanism is **Flow Control**, and in TCP it is realized via the **Sliding Window Protocol**.

```
+----------------------------------------------------------------------------+
| FLOW CONTROL (Advertised Window: RCV.WND)                                  |
|   Protects the RECEIVER's socket buffer from overflowing.                  |
|   Direct point-to-point signaling in the TCP header Window field.          |
+----------------------------------------------------------------------------+
| CONGESTION CONTROL (Congestion Window: cwnd)                               |
|   Protects the INTERMEDIATE NETWORK links from bufferbloat and packet drops.|
|   Inferred dynamically by sender based on loss and delay.                  |
+----------------------------------------------------------------------------+
| EFFECTIVE TRANSMISSION WINDOW:                                             |
|   W_eff = min(cwnd, RCV.WND)                                               |
+----------------------------------------------------------------------------+
```

---

## 2. Sender and Receiver Window Pointers

```
SENDER PERSPECTIVE:
                SND.UNA               SND.NXT
                   |                     |
                   v                     v
+------------------+---------------------+---------------------+------------------+
| 1. Sent & ACKed  | 2. Sent, Unacked    | 3. Usable Window    | 4. Cannot Send   |
| (Cleaned up)     | (In-flight bytes)   | (Can send right now)| (Outside window) |
+------------------+---------------------+---------------------+------------------+
                   \_____________________/\____________________/
                                      \             /
                                   Advertised Window (SND.WND)
```

### The Three Sender Pointers
1. **`SND.UNA` (Send Unacknowledged)**: The lowest byte number that has been sent but not yet acknowledged.
2. **`SND.NXT` (Send Next)**: The byte number of the next byte to be transmitted.
3. **`SND.WND` (Send Window)**: The window size advertised by the receiver.

$$\text{Bytes In Flight} = \text{SND.NXT} - \text{SND.UNA}$$
$$\text{Usable Window} = \text{SND.UNA} + \text{SND.WND} - \text{SND.NXT}$$

---

## 3. The Bandwidth-Delay Product (BDP) & Window Scaling
The **Bandwidth-Delay Product (BDP)** dictates the maximum amount of unacknowledged data that must be in transit to fully saturate a network pipe:
$$\text{BDP (bits)} = \text{Bandwidth (bits/sec)} \times \text{RTT (seconds)}$$
$$\text{BDP (bytes)} = \frac{\text{Bandwidth} \times \text{RTT}}{8}$$

### Example: High-Speed Transcontinental Link
- Bandwidth: $10\text{ Gbps}$
- RTT: $80\text{ ms} = 0.08\text{ s}$
$$\text{BDP} = \frac{10 \times 10^9 \times 0.08}{8} = 100,000,000 \text{ bytes (100 MB)!}$$

### The 16-Bit Header Limitation & RFC 7323
The raw TCP header allocates only 16 bits for the Window Size field:
$$\text{Max 16-bit Window} = 2^{16} - 1 = 65,535 \text{ bytes (64 KB)}$$
If window size is capped at 64 KB on a 10 Gbps 80ms link:
$$\text{Max Achievable Throughput} = \frac{\text{Window Size}}{\text{RTT}} = \frac{65,535 \times 8}{0.08} \approx 6.55 \text{ Mbps!}$$
A 10-gigabit fiber link is throttled down to **0.065%** of its capacity!

**The Window Scale Option (RFC 7323)**:
Negotiated during the initial SYN handshake (Option Kind 3). It specifies a shift count $S \in [0, 14]$.
$$\text{Actual Window} = \text{Header Window} \times 2^S$$
With $S = 14$:
$$\text{Max Scaled Window} = 65,535 \times 2^{14} = 65,535 \times 16,384 \approx 1,073,725,440 \text{ bytes (1 GiB)!}$$

---

## 4. Production Masterclass: Compilable C Sliding Window State Engine

Save as `sliding_window_engine.c` and compile with `gcc -Wall -Wextra -O2 sliding_window_engine.c -o sliding_window_engine`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <assert.h>

typedef struct {
    uint32_t snd_una; // Oldest unacknowledged byte
    uint32_t snd_nxt; // Next byte to send
    uint32_t snd_wnd; // Receiver advertised window size
} tcp_sender_window_t;

void init_sender(tcp_sender_window_t *s, uint32_t isn, uint32_t init_wnd) {
    s->snd_una = isn;
    s->snd_nxt = isn;
    s->snd_wnd = init_wnd;
}

uint32_t get_usable_window(const tcp_sender_window_t *s) {
    uint32_t in_flight = s->snd_nxt - s->snd_una;
    if (in_flight >= s->snd_wnd) {
        return 0; // Window is full!
    }
    return s->snd_wnd - in_flight;
}

int send_bytes(tcp_sender_window_t *s, uint32_t num_bytes) {
    uint32_t usable = get_usable_window(s);
    if (num_bytes > usable) {
        printf("[-] Cannot send %u bytes. Usable window is only %u bytes!\\n", num_bytes, usable);
        return -1;
    }
    s->snd_nxt += num_bytes;
    printf("[+] Sent %u bytes. SND.NXT is now %u (In flight: %u bytes)\\n",
           num_bytes, s->snd_nxt, s->snd_nxt - s->snd_una);
    return 0;
}

void process_ack(tcp_sender_window_t *s, uint32_t ack_num, uint32_t new_wnd) {
    if (ack_num < s->snd_una) {
        printf("[!] Duplicate or old ACK %u ignored.\\n", ack_num);
        return;
    }
    uint32_t bytes_acked = ack_num - s->snd_una;
    s->snd_una = ack_num;
    s->snd_wnd = new_wnd;
    printf("[ACK] Acknowledged %u bytes. New SND.UNA = %u, Advertised Window = %u\\n",
           bytes_acked, s->snd_una, s->snd_wnd);
}

int main(void) {
    printf("====================================================\\n");
    printf("TCP SLIDING WINDOW FLOW CONTROL ENGINE\\n");
    printf("====================================================\\n");

    tcp_sender_window_t sender;
    init_sender(&sender, 1000, 4096); // Starting at byte 1000 with 4KB window

    printf("[+] Initial State: SND.UNA = %u, SND.NXT = %u, SND.WND = %u, Usable = %u\\n",
           sender.snd_una, sender.snd_nxt, sender.snd_wnd, get_usable_window(&sender));

    send_bytes(&sender, 2048);
    printf("  Remaining Usable: %u bytes\\n", get_usable_window(&sender));

    send_bytes(&sender, 2048);
    printf("  Remaining Usable: %u bytes (Window now exhausted)\\n", get_usable_window(&sender));

    // Attempting to send when window is full
    send_bytes(&sender, 512);

    // Receiver acknowledges first 2048 bytes and shrinks advertised window to 1024
    process_ack(&sender, 3048, 1024);
    printf("  Remaining Usable: %u bytes\\n", get_usable_window(&sender));

    return 0;
}
```

---

## 5. Production Post-Mortem: The Middlebox Window Scale Stripping Bug
### The Outage
A global media streaming platform deployed multi-gigabit edge caches. Users connected via specific enterprise branch offices experienced video buffering and maximum download speeds locked at exactly 6.5 Mbps, despite having 1 Gbps fiber connections.

### Root Cause Analysis
Capture analysis with `tcpdump` revealed:
1. The client sent a `SYN` with TCP Option Kind 3 (Window Scale = 8).
2. An intermediate enterprise security appliance (firewall) inspected the packet. The appliance's firmware had a legacy TCP normalization engine that **stripped all unknown TCP options**, zeroing out Option Kind 3!
3. The server received the SYN without the Window Scale option and correctly adhered to RFC 7323: if the peer does not advertise Window Scale in SYN, Window Scale is disabled for the entire lifetime of the connection.
4. Window size was capped at 65,535 bytes, limiting throughput over the 80ms RTT path to $65,535 \times 8 / 0.080 \approx 6.55\text{ Mbps}$.

### Remediation
Upgraded middlebox firmware to support RFC 7323 option passthrough, instantly unlocking 800+ Mbps downloads across all affected branches.---

## 6. Protection Against Wrapped Sequences (PAWS, RFC 7323)
On high-speed networks, 32-bit sequence numbers wrap around with alarming rapidity.
At a transmission rate of 10 Gbps:
$$\text{Data Rate} = \frac{10 \times 10^9 \text{ bits/s}}{8} = 1.25 \times 10^9 \text{ bytes/s}$$
$$\text{Time to Wrap } 2^{32} \text{ Bytes} = \frac{4,294,967,296 \text{ bytes}}{1,250,000,000 \text{ bytes/s}} \approx 3.43 \text{ seconds}!$$
A sequence number cycles every 3.43 seconds! If a packet is delayed in a network buffer for just 4 seconds, its sequence number becomes indistinguishable from new data.

### The PAWS Mechanism
PAWS uses the **TCP Timestamps Option (TSopt)**:
1. Every segment carries a 32-bit timestamp (`TSval`) generated by the sender's clock.
2. The receiver tracks the latest timestamp received (`TS.Recent`).
3. An incoming segment is accepted only if:
   $$\text{SEG.TSval} \ge \text{TS.Recent}$$
4. If an old duplicate arrives with sequence numbers that happen to match the current window, but its `TSval < TS.Recent`, the receiver immediately drops the segment as a stale duplicate, guaranteeing data integrity at 100 Gbps speeds.

---

## 7. Linux Socket Buffer Tuning Parameters: tcp_wmem & tcp_rmem
The kernel dynamically sizes socket buffers using three-integer vectors configured via `/proc/sys/net/ipv4/`:

```bash
# /proc/sys/net/ipv4/tcp_rmem = min default max
# Minimum: 4096 bytes (4 KB)
# Default: 131072 bytes (128 KB)
# Maximum: 6291456 bytes (6 MB)
sysctl -w net.ipv4.tcp_rmem="4096 131072 16777216"

# /proc/sys/net/ipv4/tcp_wmem = min default max
sysctl -w net.ipv4.tcp_wmem="4096 16384 16777216"
```
To achieve line rate over a 100ms 10 Gbps path ($BDP = 125\text{ MB}$), administrators must set the maximum buffer parameters to at least the BDP, otherwise the TCP sliding window is artificially bottlenecked by kernel memory constraints.
