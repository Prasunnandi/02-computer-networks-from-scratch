# Day 19: Fast Retransmit & 3 Duplicate ACKs

## 1. Architectural Foundations: Fast Retransmit (RFC 5681)

Waiting for the Retransmission Timer (RTO) to expire (minimum $200\text{ ms}$) causes prolonged pipeline stalls. The **Fast Retransmit** algorithm enables the sender to detect and repair packet loss **long before the RTO timer expires**, relying purely on stream acknowledgment patterns.

---

## 2. Duplicate ACKs & The Out-of-Order Rule

In TCP, when a receiver receives an **out-of-order segment** (e.g. segment 3 arrives, but segment 2 is missing), RFC 5681 mandates:
**The receiver MUST immediately send a duplicate ACK repeating the exact sequence number it is still waiting for!**

```
Sender                                                  Receiver
  |                                                        |
  | ----- Segment 1 (seq=1 to 1000) ---------------------> | (Received -> ACK 1001)
  |                                                        |
  | ----- Segment 2 (seq=1001 to 2000) --- [LOST IN NET] -X
  |                                                        |
  | ----- Segment 3 (seq=2001 to 3000) ------------------> | (Out of order! -> DUP ACK 1001)
  |                                                        |
  | ----- Segment 4 (seq=3001 to 4000) ------------------> | (Out of order! -> DUP ACK 1001)
  |                                                        |
  | ----- Segment 5 (seq=4001 to 5000) ------------------> | (Out of order! -> DUP ACK 1001)
  |                                                        |
  | <==== 3 DUPLICATE ACKS RECEIVED! =====                 |
  | [FAST RETRANSMIT: Immediately re-send Segment 2!]      |
  | ----- Segment 2 (seq=1001 to 2000) ------------------> | (Cumulative ACK 5001 returned!)
```

---

## 3. Why Exactly 3 Duplicate ACKs?

Why does TCP wait for **3** duplicate ACKs rather than retransmitting on the 1st or 2nd duplicate?

In packet-switched IP networks, packets frequently take parallel paths across ECMP router links, causing minor **packet reordering** (e.g. Packet 2 arrives $1\text{ ms}$ after Packet 3).
- If TCP retransmitted on the 1st duplicate ACK, routine packet reordering would trigger false retransmissions and slash throughput.
- If TCP waited for 10 duplicate ACKs, window limits would be reached, stalling transmission.
Empirical mathematical studies proved that **3 duplicate ACKs** provides the optimal balance: $99\%$ probability that the missing segment was genuinely lost rather than merely reordered.

---

## 4. Fast Recovery

When Fast Retransmit triggers:
1. Congestion threshold is halved: $ssthresh = \max(FlightSize / 2, 2 \times MSS)$.
2. Retransmit the missing segment immediately.
3. Enter **Fast Recovery**: inflate $cwnd$ by $1 \times MSS$ for each additional duplicate ACK received (reflecting that out-of-order packets have safely left the network pipe).
4. When the new cumulative ACK arrives, deflate $cwnd = ssthresh$ and resume Congestion Avoidance.
