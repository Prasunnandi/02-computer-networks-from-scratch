# Day 15: TCP Sliding Window & Flow Control

## 1. Architectural Foundations: Flow Control vs Congestion Control

It is critical to distinguish between two completely different rate-limiting systems in TCP:
1. **Flow Control (End-to-End)**: Prevents a fast sender from overwhelming a **slow receiver's buffer**. Advertised via the **Receive Window (`RCV.WND`)** in the TCP header.
2. **Congestion Control (Network-Wide)**: Prevents senders from overwhelming the **intermediate network routers and switches**. Governed by the **Congestion Window (`CWND`)** calculated internally by the sender.

The effective window of allowed unacknowledged inflight data is strictly:

$$\text{Effective Transmission Window} = \min(\text{CWND}, \text{RCV.WND})$$

---

## 2. Mechanics of the Sliding Window

TCP uses byte-oriented sequence numbers. The sender's sliding window is divided into four logical zones:

```
+-------------------------------------------------------------------------+
|                        Sender Sliding Window State                      |
+-------------------------------------------------------------------------+
| [Zone 1: Sent & Acked] | [Zone 2: Sent, Unacked] | [Zone 3: Usable] | [Zone 4: Not Allowed] |
+------------------------+-------------------------+------------------+-----------------------+
                         ^                         ^                  ^
                         |                         |                  |
                      SND.UNA                   SND.NXT          SND.UNA + SND.WND
```

1. **`SND.UNA` (Send Unacknowledged)**: Sequence number of the oldest unacknowledged byte.
2. **`SND.NXT` (Send Next)**: Sequence number of the next byte to be transmitted.
3. **`SND.WND` (Send Window Size)**: Advertised window size received from receiver.
4. **Usable Window**: Bytes that can be sent immediately without waiting:

$$\text{Usable Window} = \text{SND.WND} - (\text{SND.NXT} - \text{SND.UNA})$$

As cumulative ACKs arrive from the receiver, `SND.UNA` advances to the right, sliding the window forward and unlocking new data transmission.

---

## 3. Bandwidth-Delay Product (BDP) & The Window Scale Option

The capacity of a network pipe is defined by the **Bandwidth-Delay Product (BDP)**:

$$\text{BDP (Bytes)} = \text{Bandwidth (Bytes/sec)} \times \text{Round Trip Time (sec)}$$

### Example Calculation:
For a $10\text{ Gbps}$ link across a transatlantic fiber cable ($RTT = 80\text{ ms} = 0.08\text{ s}$):

$$\text{BDP} = \frac{10 \times 10^9\text{ bits/s}}{8\text{ bits/byte}} \times 0.08\text{ s} = 1.25 \times 10^9 \times 0.08 = 100,000,000\text{ bytes} = 100\text{ MB}$$

To keep this $10\text{ Gbps}$ network pipe $100\%$ saturated, the sender must keep **$100\text{ MB}$ of data in flight** before stalling for an ACK.

### The 16-Bit Window Limit:
The standard TCP header allocates only **16 bits** for the Window Size field:
$$\text{Max Window} = 2^{16} - 1 = 65,535\text{ bytes} \approx 64\text{ KB}$$

Without window scaling, maximum achievable throughput on this 80ms link is capped at:
$$\text{Max Throughput} = \frac{65,535\text{ bytes}}{0.08\text{ s}} = 819,187\text{ B/s} \approx 6.55\text{ Mbps}$$
A $10\text{ Gbps}$ fiber link would be choked to a pathetic **$0.065\%$ capacity**!

### The Window Scale Option (RFC 7323)
During the 3-way handshake, endpoints negotiate a **Window Scale Factor** $S$ ($0 \le S \le 14$). The real window size is computed as:

$$\text{True Window Size} = \text{Header Window Value} \times 2^S$$

With $S = 14$:
$$\text{Max Window} = 65,535 \times 2^{14} = 1,073,725,440\text{ bytes} \approx 1\text{ GB}$$
This enables full saturation of multi-gigabit transcontinental links.
