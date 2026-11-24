# Day 20: TCP Selective ACKs (SACK) & ECN Flags

## 1. Architectural Foundations: Selective Acknowledgment (SACK - RFC 2018)

Standard TCP cumulative ACKs can only report the highest contiguous sequence number received.
**The Problem with Cumulative ACKs:**
If a sender transmits segments 1, 2, 3, 4, 5, and segments 2 and 4 are lost:
- The receiver only ACKs segment 1.
- The sender doesn't know whether segment 3 and 5 arrived safely!
- Standard TCP Tahoe retransmits everything from segment 2 onward, wasting bandwidth. TCP Reno only retransmits segment 2, requiring another full RTT to discover that segment 4 was also lost!

### 1.1 The SACK Option Format
With **Selective Acknowledgments (SACK)** enabled (Kind 5), the receiver includes up to **4 SACK blocks** inside the TCP Options field:

```
+---------------+---------------+
|  Option 5     |  Length (N)   |
+---------------+---------------+
|      Left Edge of 1st Block (32-bit Seq)      |
+-----------------------------------------------+
|      Right Edge of 1st Block (32-bit Seq)     |
+-----------------------------------------------+
|                      ...                      |
+-----------------------------------------------+
```
The receiver reports:
- Cumulative ACK = `1001` (waiting for Segment 2)
- SACK Block 1: `2001 - 3001` (Segment 3 received)
- SACK Block 2: `4001 - 5001` (Segment 5 received)
The sender inspects the SACK blocks and retransmits **only the missing isolated segments (Segments 2 and 4)**!

---

## 2. Explicit Congestion Notification (ECN - RFC 3168)

Historically, TCP could only infer network congestion by **dropping packets** (Tail-Drop at router queues). Dropping packets causes latency spikes, head-of-line blocking, and retransmission overhead.

**Explicit Congestion Notification (ECN)** allows intermediate routers to signal impending buffer congestion **without dropping packets**.

```
+-------------------------------------------------------------------------+
|                  IP Header (2-bit ECN) & TCP Flags (ECE, CWR)           |
+-------------------------------------------------------------------------+
| 1. IP Header 2-Bit ECN Field:                                           |
|    - 00: Non-ECT (Not ECN Capable)                                      |
|    - 01: ECT(1) (ECN Capable Transport)                                 |
|    - 10: ECT(0) (ECN Capable Transport)                                 |
|    - 11: CE (Congestion Experienced - Set by Router when queue fills)   |
+-------------------------------------------------------------------------+
| 2. TCP Header Flags:                                                    |
|    - ECE (ECN-Echo): Set by Receiver to echo back router congestion     |
|    - CWR (Congestion Window Reduced): Set by Sender confirming slowdown |
+-------------------------------------------------------------------------+
```

### The ECN Feedback Loop:
1. Sender transmits packet with IP bits `ECT(0) = 10`.
2. A router experiencing buffer queue buildup flips the bits to **`CE = 11` (Congestion Experienced)** and forwards the packet intact.
3. Receiver receives packet with `CE=11`. In its next ACK, it sets the **`ECE` flag** in the TCP header.
4. Sender receives `ECE=1`, reduces its congestion window (`cwnd`) as if a packet loss had occurred, and marks its next packet with **`CWR=1`**.
5. Receiver sees `CWR=1` and stops asserting `ECE`.

**Result: Zero packet loss, minimum router bufferbloat, and zero retransmission latency.**
