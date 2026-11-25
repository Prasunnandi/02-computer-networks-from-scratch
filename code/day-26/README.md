# Hands-On Lab: Day 26 - Google BBR Simulator (`bbr_model_sim.py`)

## 1. What Are We Building & Why Does It Matter?
For 30 years, all major TCP implementations (Tahoe, Reno, NewReno, CUBIC) were **loss-based**: they assumed that packet loss equals network congestion.

However, modern networks suffer from two huge problems:
1. **Bufferbloat**: Routers are built with enormous multi-megabyte RAM buffers. Loss-based TCP fills these buffers completely, causing latency to balloon from 20ms to 2,000ms without dropping a single packet!
2. **Wireless / Wi-Fi Loss**: In wireless networks, radio interference frequently drops packets even when the link is 90% idle. Loss-based TCP mistakenly slashes throughput in half!

In 2016, Google engineers Van Jacobson, Neal Cardwell, and Yuchung Cheng published **BBR (Bottleneck Bandwidth and Round-trip propagation time)**.
Instead of looking at packet loss, BBR models the physical network by measuring:
- `BtlBw`: The maximum delivery rate observed over a window of time.
- `RTprop`: The minimum round-trip time observed (pure wire propagation time).

BBR then operates at **Kleinrock's optimal operating point**:
- Transmission Rate = `BtlBw` (pacing packets evenly so queues never build up).
- In-flight Data = `BtlBw * RTprop` (saturating the pipe with zero queue delay).

In this lab, we build `bbr_model_sim.py` to trace BBR's model updates and state transitions.

---

## 2. Python Concepts for Beginners
1. **Windowed Min/Max Filters**:
   - `self.bw_samples.append(...)` and `self.bw_samples.pop(0)` keep a fixed-size moving window of recent measurements.
   - `max(self.bw_samples)` finds the maximum delivery rate observed.
   - `min(self.rtt_samples)` finds the minimum latency (which represents the true wire transit time without queue delay).
2. **Tuple Unpacking in Loops**:
   - `for i, (bw, rtt) in enumerate(samples, 1):` iterates over a list of pairs `(bandwidth, latency)`, unpacking them into variables `bw` and `rtt`, while `enumerate(..., 1)` starts index `i` at 1.

---

## 3. Step-by-Step Code Walkthrough

```python
btl_bw = max(self.bw_samples)
rt_prop = min(self.rtt_samples)
```
- BBR isolates the two physical properties:
  - Bottleneck bandwidth is the *maximum* rate achieved when the pipe was clear.
  - Round-trip delay is the *minimum* latency recorded when buffers were empty.

```python
if self.mode == 'STARTUP':
    pacing_gain = 2.885  # Exponentially probe for bottleneck
    if delivered_bw >= self.physical_bw * 0.95:
        self.mode = 'DRAIN'
```
- During `STARTUP`, BBR accelerates like Slow Start.
- Once the bandwidth stops growing, it knows the pipe is full and transitions to `DRAIN`, intentionally pacing below 1.0 to bleed off any router queue that formed!
- Once queues empty, it enters `PROBE_BW`, continuously delivering at maximum bandwidth with minimal latency.

---

## 4. How to Run the Script

```bash
cd code/day-26
python bbr_model_sim.py
```

### Expected Output
```
====================================================
DAY 26: GOOGLE BBR CONGESTION CONTROL MODEL (CARDWELL ET AL.)
====================================================
Physical Bottleneck : 1,000 pkts/sec
Physical Min RTT    : 50.0 ms (0.050s)
Physical BDP        : 50 packets

Step  | Mode       | BtlBw (pkts/s)   | RTprop (ms)  | Pacing Rate    | Target cwnd
---------------------------------------------------------------------------
1     | STARTUP    | 100.0            | 50.0         | 288.5          | 14.4       pkts
2     | STARTUP    | 250.0            | 50.0         | 721.2          | 36.1       pkts
3     | STARTUP    | 600.0            | 50.0         | 1731.0         | 86.6       pkts
4     | DRAIN      | 980.0            | 50.0         | 339.7          | 141.4      pkts
5     | DRAIN      | 1000.0           | 50.0         | 346.6          | 144.2      pkts
6     | DRAIN      | 1000.0           | 50.0         | 346.6          | 144.2      pkts
7     | PROBE_BW   | 1000.0           | 50.0         | 1000.0         | 100.0      pkts
8     | PROBE_BW   | 1000.0           | 50.0         | 1000.0         | 100.0      pkts
---------------------------------------------------------------------------

[VERIFIED] Google BBR tracked physical bottleneck without loss-based collapse!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`IndexError: pop from empty list`**:
   - Calling `pop(0)` on an empty list crashes. Always verify `if len(list) > 0:` first.
2. **Units Confusion**:
   - Notice that `rt_prop` is in seconds, while printing displays `st.rt_prop * 1000` (milliseconds). Be careful not to multiply twice!

---

## 6. Beginner Exercises & Challenges
1. **Simulate a Bandwidth Drop**: In step 9, reduce delivered bandwidth to 500 pkts/s (simulating network congestion). Watch BBR's filter adjust to the new bottleneck.
2. **Explain PROBE_RTT**: Research why BBR occasionally drops its window to 4 packets for 200ms every 10 seconds. (Hint: to let queues drain and re-measure `RTprop`!).
