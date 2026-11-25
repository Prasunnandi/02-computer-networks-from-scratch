# Hands-On Lab: Day 24 - TCP NewReno Partial ACK Recovery (`newreno_partial_ack_sim.py`)

## 1. What Are We Building & Why Does It Matter?
Standard TCP Reno worked well when a single packet was lost from a window. But what happens if **two or more packets** in the same window are dropped (for example, Packet 3 and Packet 5)?

In original Reno:
1. Sender retransmits Packet 3.
2. Receiver gets Packet 3, but is still missing Packet 5, so it sends an ACK for 5.
3. This is called a **Partial ACK** (it acknowledges some data, but not all data up to the loss event).
4. Original Reno **exited Fast Recovery immediately** upon the partial ACK, collapsed its window, and then suffered a complete **Retransmission Timeout (RTO) freeze** (lasting 200ms to 1 second!) waiting for Packet 5.

In 1999, RFC 2582 (updated in RFC 6582) introduced **TCP NewReno**.
NewReno records a special marker called `recover = highest sequence transmitted`.
When a Partial ACK arrives ($ACK < recover$), NewReno knows another packet from that same window is missing! Instead of stalling or exiting Fast Recovery, it **immediately retransmits the next missing packet**.

In this lab, we build a simulator executing this exact RFC 6582 state machine.

---

## 2. Python Concepts for Beginners
1. **Python Sets (`set()`)**:
   - `self.retransmitted = set()` stores a collection of unique items.
   - Adding an item is `self.retransmitted.add(seq)`.
   - Checking existence is instant: `if 5 in sender.retransmitted:`.
2. **Boolean Flags**:
   - `self.in_fast_recovery` is a boolean flag (`True` or `False`) that keeps track of the protocol's operating mode.
3. **State Machine Transitions**:
   - Methods like `on_ack_received()` inspect incoming parameters and current state, update internal attributes, and return human-readable status strings.

---

## 3. Step-by-Step Code Walkthrough

```python
def on_three_dup_acks(self, ack_num: int):
    self.ssthresh = max(2.0, self.cwnd / 2.0)
    self.cwnd = self.ssthresh + 3.0
    self.recover = self.snd_nxt - 1   # Mark the boundary of the loss window
    self.in_fast_recovery = True
    self.retransmitted.add(ack_num)
```
- When duplicate ACKs trigger Fast Recovery, `self.recover` records the highest sequence number already transmitted (e.g. Seq 8).

```python
if ack_num < self.recover:
    # PARTIAL ACK
    self.snd_una = ack_num
    self.retransmitted.add(ack_num)  # Retransmit Seq 5 right away!
    self.cwnd = self.ssthresh
    return f'PARTIAL_ACK (Immediate Retransmit Seq {ack_num})'
```
- When ACK 5 arrives, because $5 < 8$, NewReno recognizes this is a Partial ACK.
- Instead of crashing into an RTO timeout, it retransmits Seq 5 on the spot!
- Once ACK 9 arrives ($9 \ge 8$), all lost packets have been safely recovered, and NewReno exits Fast Recovery.

---

## 4. How to Run the Script

```bash
cd code/day-24
python newreno_partial_ack_sim.py
```

### Expected Output
```
====================================================
DAY 24: TCP NEWRENO MULTI-PACKET DROP RECOVERY (RFC 6582)
====================================================
Sending initial window of 8 packets (Seq 1 to 8)...
Transmitted packets: [1, 2, 3, 4, 5, 6, 7, 8]

[NETWORK EVENT] Packets 3 and 5 dropped by router!
Packets 1 and 2 arrive -> Receiver sends ACK 3
Packets 4, 6, 7, 8 arrive -> Receiver sends 4 Duplicate ACKs for 3!

-> Entered Fast Recovery! recover marker set to Seq 8
-> Retransmitted Seq 3: {3}

--- Receiving ACK 5 ---
Sender Action : PARTIAL_ACK (Immediate Retransmit Seq 5)
Still in Fast Recovery: True (NewReno does NOT stall!)

--- Receiving ACK 9 ---
Sender Action : FULL_ACK (Exit Fast Recovery)
In Fast Recovery: False

[VERIFIED] NewReno successfully recovered multiple packet drops without RTO stall!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`TypeError: unhashable type: 'list'`**:
   - If you try to add a list into a set `set.add([1, 2])`, Python will throw this error because lists are mutable. Add single integers `set.add(1)`.
2. **Infinite Retransmission**:
   - If `self.snd_una` is not updated to `ack_num`, the sender will keep retransmitting the same sequence repeatedly.

---

## 6. Beginner Exercises & Challenges
1. **Triple Drop Scenario**: Modify the simulation so that packets 2, 4, and 6 are all dropped from a 12-packet window. Verify that NewReno issues two partial ACK retransmissions before the final full ACK.
2. **Compare Against SACK**: Read RFC 2018 (Selective ACKs). How does SACK improve upon NewReno when 5+ packets are dropped?
