# Day 16: Zero Window, Probes & Silly Window Syndrome

## 1. Architectural Foundations: Flow Control Boundary Conditions
In the TCP sliding window model, the receiver advertises available socket buffer space via the 16-bit Window Size field. Under heavy application load, the receiver process may read data slower than the network stack receives it.

When the receiver's socket buffer fills to capacity, the receiver advertises an explicit **Zero Window** (`win = 0`). This command instructs the sender to **halt all data transmission immediately**.

```
RECEIVER BUFFER FILLING TO ZERO:
[ Kernel Socket Receive Buffer (e.g. 64 KB total) ]
+-------------------------------------------------------+
| In-Order Data Awaiting App read()      | Free Space   | -> Advertises win = 16384
+-------------------------------------------------------+
                                  |
                                  v  (App does not call read(); more packets arrive)
+-------------------------------------------------------+
| In-Order Data Awaiting App read()                     | -> Advertises win = 0 (HALT!)
+-------------------------------------------------------+
```

---

## 2. The Persist Timer & Zero Window Probes (ZWP)

### The Deadlock Hazard
Suppose Receiver sends a segment with `win = 0`. Sender halts.
Later, the receiver application reads 32 KB from the socket buffer. Receiver emits a window update segment: `ACK=5000, win=32768`.
**What happens if this single ACK packet is dropped by an intermediate router?**
- Receiver is waiting for data (believes it opened the window).
- Sender is waiting for a window update (believes window is still zero).
- Neither side has in-flight data, so **no retransmission timer is running**!
Both endpoints will remain deadlocked forever.

### The RFC 1122 Solution: The Persist Timer
To break this deadlock, when the sender receives `win = 0`, it starts a **Persist Timer**:
1. When the persist timer expires, the sender transmits a **Zero Window Probe (ZWP)**: a segment containing exactly **1 byte of payload** (or a segment with no data and `seq = SND.NXT - 1`).
2. The receiver is forced to respond with an ACK indicating its current sequence number and its latest available window size.
3. If the window is still zero, the sender restarts the persist timer with **exponential backoff** (e.g., 5s, 10s, 20s, up to a maximum clamp of 60 seconds) and continues probing indefinitely until the window re-opens.

---

## 3. Silly Window Syndrome (SWS): Mathematical Catastrophe
Silly Window Syndrome occurs when either:
1. The receiver advertises tiny window increments (e.g., 1 byte as soon as the app reads 1 byte).
2. The sender immediately transmits tiny segments as soon as any window opens.

```
THE OVERHEAD OF A 1-BYTE SEGMENT:
+-------------------+-------------------+-------------------+
| IPv4 Header (20B) | TCP Header (20B)  | Payload (1 Byte)  | -> 41 Bytes Wire Total
+-------------------+-------------------+-------------------+
```
### Mathematical Protocol Efficiency
$$\text{Efficiency} = \frac{\text{Payload Bytes}}{\text{Total Bytes Transmitted}} = \frac{1}{20 + 20 + 1} = \frac{1}{41} \approx 2.44\%$$
**Protocol Overhead is 97.56%!** Sending a 1 MB file 1 byte at a time requires 41 MB of network bandwidth and generates over 2,000,000 packet interrupts across all intermediate routers, triggering catastrophic network congestion collapse.

### SWS Avoidance Algorithms
1. **Clark's Solution (Receiver-Side)**:
   The receiver must not advertise any window opening until it can open the window by either:
   $$\text{Advertised Window} \ge \min(\text{MSS}, \frac{\text{Total Buffer Size}}{2})$$
   Until this threshold is satisfied, the receiver continues to advertise `win = 0`.
2. **Sender-Side Avoidance**:
   The sender must not send a segment unless:
   - A full Maximum Segment Size (MSS) segment can be transmitted, OR
   - The segment contains at least half the receiver's maximum advertised window, OR
   - Data can be sent and all previously sent data has been acknowledged (Nagle's rule).

---

## 4. Production Masterclass: Compilable C SWS & Persist Timer Simulator

Save as `sws_simulator.c` and compile with `gcc -Wall -Wextra -O2 sws_simulator.c -o sws_simulator`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>

#define MSS 1460
#define TOTAL_BUFFER_SIZE 4096

typedef struct {
    uint32_t buffer_used;
    uint32_t buffer_total;
} receiver_buffer_t;

// Clark's Algorithm implementation at the receiver
uint32_t clark_advertise_window(receiver_buffer_t *rcv) {
    uint32_t free_space = rcv->buffer_total - rcv->buffer_used;
    uint32_t threshold = MSS;
    if (rcv->buffer_total / 2 < threshold) {
        threshold = rcv->buffer_total / 2;
    }

    // If free space is less than threshold, advertise ZERO to prevent SWS!
    if (free_space < threshold) {
        return 0;
    }
    return free_space;
}

int main(void) {
    printf("====================================================\n");
    printf("SILLY WINDOW SYNDROME & CLARK'S AVOIDANCE SIMULATOR\n");
    printf("Receiver Buffer: %d bytes | MSS: %d bytes\n", TOTAL_BUFFER_SIZE, MSS);
    printf("====================================================\n");

    receiver_buffer_t rcv = { .buffer_used = 4090, .buffer_total = TOTAL_BUFFER_SIZE };

    printf("[+] Initial State: Buffer Used = %u / %u bytes (Free: %u bytes)\n",
           rcv.buffer_used, rcv.buffer_total, rcv.buffer_total - rcv.buffer_used);

    printf("\n--- SCENARIO A: NAIVE RECEIVER (Vulnerable to SWS) ---\n");
    for (int i = 0; i < 3; i++) {
        uint32_t naive_win = rcv.buffer_total - rcv.buffer_used;
        printf("  [Naive] Advertised Window = %u bytes. (Sender emits %u-byte TCP segment: 97%% overhead!)\n",
               naive_win, naive_win);
        rcv.buffer_used -= 2; // App reads 2 bytes
    }

    printf("\n--- SCENARIO B: CLARK'S ALGORITHM (SWS Immune) ---\n");
    rcv.buffer_used = 4090; // Reset to 6 bytes free
    for (int i = 0; i < 5; i++) {
        uint32_t smart_win = clark_advertise_window(&rcv);
        printf("  [Clark] Free Space = %4u bytes -> Advertised Window = %4u bytes (%s)\n",
               rcv.buffer_total - rcv.buffer_used, smart_win,
               smart_win == 0 ? "SUPPRESSED ZERO WINDOW to prevent SWS" : "OPENED WINDOW");
        rcv.buffer_used -= 512; // App consumes 512 bytes per iteration
    }

    return 0;
}
```

---

## 5. Production Post-Mortem: The IoT Telemetry Throughput Collapse
### The Outage
A fleet of 50,000 smart utility meters communicating over cellular CAT-M networks reported data collection delays exceeding 18 hours. Cloud ingestion servers were overwhelmed by 120,000 packets/sec despite total incoming data bandwidth measuring less than 1.5 MB/sec!

### Root Cause Analysis
The embedded firmware engineers wrote the sensor reporting loop in C:
```c
// Catastrophic unbuffered socket writes:
for (int i = 0; i < num_sensors; i++) {
    uint8_t byte = read_sensor(i);
    write(sock_fd, &byte, 1); // 1-byte write per loop iteration!
}
```
Because `TCP_NODELAY` was enabled on the embedded device, the TCP stack immediately framed every single 1-byte sensor reading into a full 40-byte TCP/IP packet. Cellular carriers billed for packet framing overhead, and intermediate firewall NAT tables filled to capacity with millions of micro-packets.

### Remediation
1. Buffering: Batch sensor telemetry into 1024-byte chunks before calling `write()`.
2. Disable `TCP_NODELAY` and enable `TCP_CORK` during batch generation. Network throughput increased by **3,800%**, and cellular data charges dropped by 96%.---

## 6. TCP Zero Window Probes vs TCP Keepalives
Engineers frequently confuse Zero Window Probes with TCP Keepalive probes:

| Dimension | Zero Window Probe (ZWP) | TCP Keepalive Probe |
| :--- | :--- | :--- |
| **Trigger** | Receiver advertises `win = 0`. | Connection is completely idle for `tcp_keepalive_time` (e.g. 7200s). |
| **Payload** | Exactly 1 byte of payload (or 0 bytes with `seq = SND.NXT - 1`). | 0 bytes of payload with `seq = SND.NXT - 1`. |
| **Purpose** | Force receiver to re-advertise available window buffer space. | Detect whether dead peer host crashed or rebooted. |
| **Timer** | Persist Timer (exponential backoff: 5s, 10s, 20s... max 60s). | Keepalive Timer (e.g. 7200s idle, then 9 probes every 75s). |
| **Termination** | Runs indefinitely until window opens or process aborted. | Terminates connection after unacknowledged probe threshold. |

---

## 7. The TCP_USER_TIMEOUT Socket Option (RFC 5482)
When a zero-window deadlock or network partition occurs, how long will a sender wait before giving up?
By default, Linux retries zero window probes indefinitely, or retries unacknowledged data for 15 retries (`net.ipv4.tcp_retries2 = 15`), which can take up to **13 to 30 minutes**!

To prevent threads from hanging for 30 minutes, modern applications configure `TCP_USER_TIMEOUT`:
```c
// Force connection abort if unacknowledged data or zero-window persists for > 15 seconds
unsigned int timeout_ms = 15000;
setsockopt(sock_fd, IPPROTO_TCP, TCP_USER_TIMEOUT, &timeout_ms, sizeof(timeout_ms));
```
If the peer stays in zero-window or becomes unreachable for 15,000 ms, the kernel immediately aborts the connection, delivering `ETIMEDOUT` to the calling application.
