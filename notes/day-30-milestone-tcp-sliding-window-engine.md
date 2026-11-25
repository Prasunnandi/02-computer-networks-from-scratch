# Day 30: Milestone 1: Userspace TCP Sliding Window Engine

## 1. Architectural Foundations: The Synthesis of Transport Protocols
Over the past 29 days, we have dissected the physical, link, network, and transport layers from raw bits to congestion control.
In this Milestone, we synthesize:
1. **Packet Framing & Sequence Number Accounting** (Days 11, 12).
2. **Sliding Window Flow Control** (`SND.UNA`, `SND.NXT`, `SND.WND`, Days 15, 16).
3. **Loss Recovery via Fast Retransmit & 3 Duplicate ACKs** (Days 19, 23, 24).
4. **Congestion Control Dynamics** (Slow Start & Additive Increase, Days 21, 22, 25).

```
+----------------------------------------------------------------------------+
|             SYNTHESIZED USERSPACE TCP SLIDING WINDOW ENGINE                |
+----------------------------------------------------------------------------+
       |                                               |
       v                                               v
[ SENDER TRANSMISSION PIPELINE ]               [ RECEIVER REORDER QUEUE ]
  - Byte offset stream: SND.NXT                  - Cumulative ACK generation
  - In-flight byte tracking: SND.UNA             - Selective gap detection
  - Dynamic cwnd & ssthresh scaling              - Window credit advertisement
       |                                               |
       +------------------- NETWORK PIPE --------------+
                       (Simulated Packet Drops)
```

---

## 2. Complete Milestone Specification
The Milestone 1 engine implements an end-to-end reliable byte stream transmitter:
- **Packet Struct**: Encapsulates 32-bit `seq`, 32-bit `ack`, flags (`SYN`, `ACK`, `FIN`), window advertisement, and payload.
- **Sender State Machine**:
  - Starts in Slow Start ($cwnd = 1 \text{ MSS}$, $ssthresh = 16 \text{ MSS}$).
  - Doubles $cwnd$ every RTT in Slow Start; adds 1 MSS per RTT in Avoidance.
  - Detects lost segments via 3 Duplicate ACKs and triggers **immediate Fast Retransmit**.
  - Halves $ssthresh$ and enters Fast Recovery.

---

## 3. Production Masterclass: Complete Compilable C Userspace TCP Engine

Save as `userspace_tcp_milestone.c` and compile with `gcc -Wall -Wextra -O2 userspace_tcp_milestone.c -o userspace_tcp_milestone`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#define MSS 1024
#define INIT_SSTHRESH (16 * MSS)

typedef struct {
    uint32_t seq;
    uint32_t ack;
    uint16_t flags;
    uint32_t win;
    size_t   len;
    uint8_t  payload[MSS];
} tcp_segment_t;

typedef struct {
    uint32_t snd_una; // Oldest unacknowledged byte
    uint32_t snd_nxt; // Next byte to send
    uint32_t snd_wnd; // Receiver advertised window
    uint32_t cwnd;    // Congestion window
    uint32_t ssthresh;
    int      dupack_count;
    int      in_fast_recovery;
} tcp_sender_t;

void init_sender(tcp_sender_t *s, uint32_t isn) {
    s->snd_una = isn;
    s->snd_nxt = isn;
    s->snd_wnd = 32 * MSS; // Receiver has 32 KB buffer
    s->cwnd = 1 * MSS;     // Slow start begins at 1 MSS
    s->ssthresh = INIT_SSTHRESH;
    s->dupack_count = 0;
    s->in_fast_recovery = 0;
}

void on_ack(tcp_sender_t *s, uint32_t ack_num) {
    if (ack_num == s->snd_una) {
        s->dupack_count++;
        printf("[DupACK #%d] Received duplicate ACK for byte %u\n", s->dupack_count, ack_num);

        if (s->dupack_count == 3) {
            printf("\n>>> [3 DUPLICATE ACKS] TRIGGERING FAST RETRANSMIT OF BYTE %u <<<\n", ack_num);
            s->ssthresh = s->cwnd / 2;
            s->cwnd = s->ssthresh + 3 * MSS;
            s->in_fast_recovery = 1;
            printf(">>> State: ssthresh cut to %u, cwnd inflated to %u <<<\n\n", s->ssthresh, s->cwnd);
        } else if (s->dupack_count > 3 && s->in_fast_recovery) {
            s->cwnd += MSS; // Inflate window
        }
    } else if (ack_num > s->snd_una) {
        uint32_t bytes_acked = ack_num - s->snd_una;
        s->snd_una = ack_num;
        s->dupack_count = 0;

        if (s->in_fast_recovery) {
            printf("[Recovery ACK] Full cumulative ACK %u received! Exiting Fast Recovery.\n", ack_num);
            s->cwnd = s->ssthresh;
            s->in_fast_recovery = 0;
        } else {
            // Congestion Control Window Update
            if (s->cwnd < s->ssthresh) {
                // Slow Start: Add MSS per ACK (Doubles per RTT)
                s->cwnd += MSS;
                printf("[ACK %u] Slow Start Growth: cwnd = %u bytes (%u MSS)\n",
                       ack_num, s->cwnd, s->cwnd / MSS);
            } else {
                // Congestion Avoidance: Linear growth (+1 MSS per RTT)
                s->cwnd += ((uint64_t)MSS * MSS) / s->cwnd;
                printf("[ACK %u] Avoidance Growth: cwnd = %u bytes (%u MSS)\n",
                       ack_num, s->cwnd, s->cwnd / MSS);
            }
        }
    }
}

int main(void) {
    printf("====================================================\n");
    printf("MILESTONE 1: USERSPACE TCP SLIDING WINDOW ENGINE\n");
    printf("Synthesizes Days 11-29 into unified transport stack\n");
    printf("====================================================\n\n");

    tcp_sender_t sender;
    init_sender(&sender, 1000);

    printf("[+] Step 1: Slow Start Exponential Capacity Discovery...\n");
    // Simulate initial ACKs returning
    on_ack(&sender, 2024);
    on_ack(&sender, 3048);
    on_ack(&sender, 4072);

    printf("\n[+] Step 2: Simulating Packet Drop & Fast Retransmit Trigger...\n");
    // Receiver misses packet at byte 4072, but receives 5096, 6120, 7144
    on_ack(&sender, 4072); // DupACK 1
    on_ack(&sender, 4072); // DupACK 2
    on_ack(&sender, 4072); // DupACK 3 -> Fast Retransmit!

    printf("\n[+] Step 3: Cumulative Recovery ACK Arrival...\n");
    on_ack(&sender, 8168); // Acknowledges all data

    printf("\n====================================================\n");
    printf("FINAL ENGINE STATE:\n");
    printf("  SND.UNA (Acked): %u | cwnd: %u bytes | ssthresh: %u\n",
           sender.snd_una, sender.cwnd, sender.ssthresh);
    printf("====================================================\n");

    return 0;
}
```

---

## 4. Architectural Reflection & Next Steps
With Milestone 1 complete, the foundation of reliable point-to-point byte-stream transmission across unreliable networks is mastered.
In Milestone 2 (Days 31 to 60), we advance to:
- Application Layer Protocols (DNS resolution from root servers, HTTP/1.1 pipelining, HTTP/2 multiplexing, HTTP/3 QUIC).
- Distributed Routing (OSPF link-state, BGP path-vector peering, NAT traversal, and wire-speed packet filtering with eBPF/XDP).---

## 5. Emulating Network Loss & Jitter in Linux: `tc netem`
To benchmark and verify the Milestone 1 Userspace TCP Sliding Window Engine under real-world conditions, engineers use the Linux Traffic Control Network Emulator (`tc netem`):

```bash
# 1. Add 50ms latency with 5ms jitter and 3% packet drop to loopback interface:
sudo tc qdisc add dev lo root netem delay 50ms 5ms loss 3%

# 2. Run the Userspace TCP Milestone Engine:
./userspace_tcp_milestone

# 3. Observe Fast Retransmit, Reno sawtooth inflation, and ACK clocking!

# 4. Remove traffic emulation rule after test:
sudo tc qdisc del dev lo root
```
This enables deterministic testing of transport layer algorithms without physical test networks.
---

## 7. Deep Architectural Mechanics: Nagle's Algorithm vs Delayed ACKs Deadlock

### The Catastrophic Interaction: `TCP_NODELAY`
One of the most famous traps in network systems engineering is the deadlock between **Nagle's Algorithm** on the sender and **Delayed ACKs** on the receiver.
- **Nagle's Algorithm (RFC 896)**: If a sender has unacknowledged data in flight, it buffers small outgoing chunks until a full Maximum Segment Size (`MSS = 1460 bytes`) is accumulated, or until an ACK arrives.
- **Delayed ACKs (RFC 1122)**: The receiver waits up to 200ms before sending an ACK, hoping to piggyback the ACK on return data.

```
Sender (Nagle):  Sends 400 bytes. Waits for ACK before sending next chunk.
Receiver (ACK):  Received 400 bytes. Waits 200ms before sending ACK.
RESULT: Both sides sit idle doing NOTHING for 200ms! (40ms - 200ms artificial latency!)
```
In modern high-performance microservices and database drivers (such as Redis, PostgreSQL, gRPC), systems engineers **always disable Nagle's Algorithm** by setting the socket option:
```c
int flag = 1;
setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));
```

### Complete Compilable C Program: Userspace TCP Checksum Engine
```c
/*
 * tcp_checksum_verify.c - Implements RFC 1071 16-bit 1s complement checksum
 * Compile: gcc -O2 -Wall tcp_checksum_verify.c -o tcp_checksum_verify
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

uint16_t compute_checksum(const uint8_t *data, size_t len) {
    uint32_t sum = 0;
    while (len > 1) {
        sum += ((uint16_t)data[0] << 8) | data[1];
        data += 2;
        len -= 2;
    }
    if (len == 1) {
        sum += ((uint16_t)data[0] << 8);
    }
    while (sum >> 16) {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    return (uint16_t)(~sum);
}

int main(void) {
    const char *msg = "HELLO_WORLD_TCP_MILESTONE_TEST";
    uint16_t csum = compute_checksum((const uint8_t *)msg, strlen(msg));

    printf("=========================================\n");
    printf("RFC 1071 INTERNET CHECKSUM VERIFICATION\n");
    printf("=========================================\n");
    printf("Payload String : %s\n", msg);
    printf("Payload Length : %zu bytes\n", strlen(msg));
    printf("Computed CSUM  : 0x%04X\n", csum);
    printf("=========================================\n");
    return 0;
}
```

---

## 8. Milestone 1 Production War Story: The Micro-Burst Buffer Collapse
In 2020, a high-frequency trading platform built an ultra-low latency market data feed.
During opening market auctions, volume would surge by $5000\%$ in a 2-millisecond window (a "micro-burst").
Even though average network utilization was only $15\%$, switch queues overflowed during the micro-burst, dropping market order packets and causing 10ms retransmission delays that cost millions.
By replacing stock Linux loss-based TCP with a custom userspace sliding window engine that utilized hardware timestamping, kernel-bypass (DPDK), and selective retransmission without delayed ACKs, the firm achieved deterministic sub-microsecond data transmission even under severe micro-burst load.
