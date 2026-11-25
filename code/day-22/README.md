# Hands-On Lab: Day 22 - TCP Slow Start & Congestion Avoidance (`slow_start_sim.py`)

## 1. What Are We Building & Why Does It Matter?
When a computer opens a brand new TCP connection, it has zero knowledge of the network path's capacity. Is the destination a fiber-optic data center across town, or a satellite phone in the Sahara desert?

If the sender immediately blasted 10,000 packets into the pipe, it could choke routers and drop everything. To safely probe the network, TCP uses **Slow Start** (RFC 5681).
- Counterintuitively, Slow Start is NOT slow! It starts with a tiny window (e.g. 1 packet) and **doubles every single Round-Trip Time (RTT)** (exponential growth: $1 \to 2 \to 4 \to 8 \to 16$).
- Once the window reaches a safety boundary called the **Slow Start Threshold (`ssthresh`)**, TCP switches to **Congestion Avoidance**, carefully growing at a gentle **linear** rate of $+1$ packet per RTT.
- If a packet times out, TCP halves `ssthresh` and collapses `cwnd` back to 1.

In this lab, we build `slow_start_sim.py` to simulate this fundamental dual-phase state machine.

---

## 2. Python Concepts for Beginners
1. **Floating-Point vs Integer Division**:
   - `1.0 / self.state.cwnd` produces a float. When in congestion avoidance with a window of 16 packets, receiving one ACK increases `cwnd` by $1/16 = 0.0625$. When all 16 ACKs arrive, the total increase is $16 \times 0.0625 = 1.0$ full packet!
2. **Conditional (Ternary) Expressions**:
   - `note = 'TIMEOUT' if loss else 'Linear'` evaluates to `'TIMEOUT'` if `loss` is True, otherwise `'Linear'`.
3. **The `max()` Function**:
   - `max(2.0, self.state.cwnd / 2.0)` ensures `ssthresh` never drops below 2 segments, matching RFC requirements.

---

## 3. Step-by-Step Code Walkthrough

```python
def on_ack_received(self):
    if self.state.cwnd < self.state.ssthresh:
        self.state.phase = 'SLOW_START'
        self.state.cwnd += 1.0
    else:
        self.state.phase = 'CONGESTION_AVOIDANCE'
        self.state.cwnd += 1.0 / self.state.cwnd
```
- In Slow Start, every ACK adds 1 full MSS. Because 1 packet generates 1 ACK, sending $N$ packets generates $N$ ACKs, each adding 1 to `cwnd`. Thus `cwnd` becomes $N + N = 2N$ (doubles every RTT!).
- In Congestion Avoidance, each ACK adds only $1 / cwnd$. Across an entire window of $W$ packets, the sum of increments is $W \times (1 / W) = 1$ packet per RTT.

```python
def on_timeout(self):
    self.state.ssthresh = max(2.0, self.state.cwnd / 2.0)
    self.state.cwnd = 1.0
    self.state.phase = 'SLOW_START'
```
- A timeout indicates severe congestion. The sender remembers half of its current capacity as the new ceiling (`ssthresh`), resets `cwnd` to 1, and restarts Slow Start.

---

## 4. How to Run the Script

```bash
cd code/day-22
python slow_start_sim.py
```

### Expected Output
```
====================================================
DAY 22: TCP SLOW START & CONGESTION AVOIDANCE SIM
====================================================
Initial State: cwnd=1.0 MSS, ssthresh=16.0 MSS

RTT    | Phase                  | cwnd (MSS)   | ssthresh (MSS) | Growth Rate
----------------------------------------------------------------------
1      | SLOW_START             | 2.00         | 16.00          | Exponential (+100%/RTT)
2      | SLOW_START             | 4.00         | 16.00          | Exponential (+100%/RTT)
3      | SLOW_START             | 8.00         | 16.00          | Exponential (+100%/RTT)
4      | SLOW_START             | 16.00        | 16.00          | Exponential (+100%/RTT)
5      | CONGESTION_AVOIDANCE   | 17.00        | 16.00          | Linear (+1 MSS/RTT)
6      | CONGESTION_AVOIDANCE   | 18.00        | 16.00          | Linear (+1 MSS/RTT)
7      | CONGESTION_AVOIDANCE   | 19.00        | 16.00          | Linear (+1 MSS/RTT)
8      | CONGESTION_AVOIDANCE   | 20.00        | 16.00          | Linear (+1 MSS/RTT)
9      | SLOW_START             | 1.00         | 10.00          | *** PACKET TIMEOUT (RTO) ***
10     | SLOW_START             | 2.00         | 10.00          | Exponential (+100%/RTT)
...
----------------------------------------------------------------------

[VERIFIED] TCP Slow Start exponential expansion and linear avoidance verified!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`TypeError: unsupported operand type(s) for /: 'float' and 'str'`**:
   - Ensure `cwnd` is stored as a `float` or `int`, not a string like `'1.0'`.
2. **Infinite Slow Start Loop**:
   - If `ssthresh` is set to infinity or a very large number, TCP never transitions to Congestion Avoidance and will violently overshoot router capacity.

---

## 6. Beginner Exercises & Challenges
1. **Initial Window of 10 MSS**: Modern Linux kernels (since RFC 6928) use `init_cwnd = 10` instead of `1`. Change `init_cwnd = 10.0` and observe how much faster the sender reaches saturation!
2. **Track Total Bytes Sent**: Add a variable `total_packets_sent` that accumulates `int(self.state.cwnd)` every RTT. Calculate how many total packets were transferred over 14 RTTs.
