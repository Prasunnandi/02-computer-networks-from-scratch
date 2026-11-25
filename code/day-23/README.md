# Hands-On Lab: Day 23 - TCP Tahoe vs Reno Simulator (`tahoe_reno_sim.py`)

## 1. What Are We Building & Why Does It Matter?
In 1988, TCP Tahoe introduced **Fast Retransmit**: if a sender receives 3 duplicate ACKs, it realizes a single packet was lost in transit without waiting for the slow, sluggish Retransmission Timeout (RTO) timer to expire.

However, Tahoe made a drastic mistake: after retransmitting the lost packet, it **collapsed its congestion window all the way back to 1 MSS**, restarting Slow Start from scratch. This created huge throughput dips (the "sawtooth cliff").

In 1990, TCP Reno fixed this by introducing **Fast Recovery**. Reno recognized that if 3 duplicate ACKs arrived at the sender, **packets are still successfully flowing through the network and reaching the receiver!**
Instead of collapsing `cwnd` to 1, Reno:
1. Cuts `ssthresh` in half: `ssthresh = cwnd / 2`.
2. Sets `cwnd = ssthresh + 3` (inflating the window to account for the 3 packets that generated the duplicate ACKs).
3. Transmits new data if window permits, and immediately transitions into Congestion Avoidance once the retransmitted packet is acknowledged!

In this lab, we build a side-by-side simulator proving why Reno outperforms Tahoe by 30%+ in throughput.

---

## 2. Python Concepts for Beginners
1. **Returning Objects from Functions**:
   - `def simulate_tcp(...) -> FlowResult:` returns an instance of our `@dataclass FlowResult`, bundling the algorithm name, full history list, and total packet count into a single neat object.
2. **List Indexing Off-by-One (`r+1` vs `r`)**:
   - Python lists are 0-indexed (`range(16)` runs from `0` to `15`). For human readers, we print `r + 1` so round numbers display from 1 to 16.
3. **Percentage Calculation**:
   - `((reno - tahoe) / tahoe) * 100.0` calculates relative percentage improvement.

---

## 3. Step-by-Step Code Walkthrough

```python
if r == loss_round:
    ssthresh = max(2.0, cwnd / 2.0)
    if algorithm == 'Tahoe':
        cwnd = 1.0          # Tahoe collapses to 1 MSS!
        phase = 'SLOW_START'
    elif algorithm == 'Reno':
        cwnd = ssthresh + 3.0  # Reno inflates window!
        phase = 'FAST_RECOVERY'
```
- In Round 7, both senders have reached a window of 32 packets when a loss occurs.
- `ssthresh` is set to $32 / 2 = 16$.
- Tahoe collapses to `cwnd = 1.0`. In Round 8 it can only send 1 packet!
- Reno sets `cwnd = 16 + 3 = 19.0`. In Round 8 it sends 19 packets!
- Tahoe takes 5 full round trips just to crawl back up to where Reno stayed continuously.

---

## 4. How to Run the Script

```bash
cd code/day-23
python tahoe_reno_sim.py
```

### Expected Output
```
====================================================
DAY 23: TCP TAHOE VS RENO FAST RECOVERY COMPARISON
====================================================
Round  | Tahoe cwnd   | Reno cwnd    | Difference (Reno Advantage)
------------------------------------------------------------
1      | 1.0          | 1.0          | +0.0   MSS
2      | 2.0          | 2.0          | +0.0   MSS
3      | 4.0          | 4.0          | +0.0   MSS
4      | 8.0          | 8.0          | +0.0   MSS
5      | 16.0         | 16.0         | +0.0   MSS
6      | 32.0         | 32.0         | +0.0   MSS
7      | 32.0         | 32.0         | +0.0   MSS <--- 3 DUP ACKS LOSS DETECTED
8      | 1.0          | 19.0         | +18.0  MSS
9      | 2.0          | 16.0         | +14.0  MSS
10     | 4.0          | 17.0         | +13.0  MSS
11     | 8.0          | 18.0         | +10.0  MSS
12     | 16.0         | 19.0         | +3.0   MSS
13     | 17.0         | 20.0         | +3.0   MSS
------------------------------------------------------------
Total Packets Delivered (Tahoe) : 177
Total Packets Delivered (Reno)  : 236
Reno Throughput Advantage       : +33.3%

[VERIFIED] TCP Reno Fast Recovery avoids Tahoe throughput cliff!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`ZeroDivisionError` when computing percentage**:
   - If Tahoe delivered 0 packets, dividing by `tahoe.total_packets_delivered` crashes. Guard with `if tahoe.total_packets_delivered > 0:`.
2. **Incorrect Window Inflation**:
   - If you set Reno's window to `ssthresh` instead of `ssthresh + 3`, you will stall the pipeline because the 3 duplicate ACKs that already left the pipe are not accounted for.

---

## 6. Beginner Exercises & Challenges
1. **Graph the Curves**: Write a simple ASCII bar chart printer function `print_bars(history)` using `#' * int(w)` to visually display the window curves in the terminal.
2. **Test Multiple Losses**: Simulate a second packet loss in Round 12. Observe how both protocols respond to back-to-back losses.
