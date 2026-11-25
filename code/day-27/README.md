# Hands-On Lab: Day 27 - CoDel Active Queue Management (`codel_aqm_sim.py`)

## 1. What Are We Building & Why Does It Matter?
Home routers and enterprise switches often have huge packet buffers. When you upload a large file or run a speed test, your connection buffers fill completely. This causes **Bufferbloat**: your web browsing becomes sluggish and video calls freeze with 1,000ms ping, even though bandwidth is high!

Old queue algorithms like Drop-Tail wait until the physical memory is 100% full before dropping packets. By then, latency is already ruined.
Older AQMs like RED (Random Early Detection) tried to drop packets based on queue length, but required complex manual tuning for every link speed.

In 2012, Kathleen Nichols and Van Jacobson invented **CoDel (Controlled Delay)** (RFC 8290).
CoDel makes a brilliant conceptual breakthrough:
- It does **not** care how many bytes are in the queue.
- It only measures **Sojourn Time**: how long a packet sat waiting in the buffer from arrival to departure.
- If the minimum sojourn time stays above `TARGET = 5ms` for more than `INTERVAL = 100ms`, CoDel knows there is "bad standing queue".
- It enters dropping mode, dropping packets on an inverse square root schedule ($INTERVAL / \sqrt{\text{count}}$) to force senders to back off!

In this lab, we build a working CoDel queue simulator.

---

## 2. Python Concepts for Beginners
1. **The `math.sqrt()` Function**:
   - Computes the square root of a number.
   - Used in the CoDel schedule formula `self.INTERVAL / math.sqrt(self.count)`. As `count` increases, the interval between drops shrinks, rapidly signaling stubborn senders.
2. **First-In, First-Out (FIFO) with Lists**:
   - `self.queue.append(...)` adds a packet to the back of the queue.
   - `self.queue.pop(0)` removes and returns the packet at the very front of the queue.
3. **Simulating Virtual Time**:
   - Instead of using `time.sleep()`, we track virtual time `now = 0.025` and advance it manually. This makes tests instantaneous, repeatable, and deterministic!

---

## 3. Step-by-Step Code Walkthrough

```python
sojourn_time = now - pkt.arrival_time
if sojourn_time < self.TARGET:
    self.first_above_time = 0.0
    return pkt, False
```
- When a packet is dequeued, we calculate its dwell time. If it waited less than 5ms, the buffer is healthy and no action is taken.

```python
if self.first_above_time == 0.0:
    self.first_above_time = now + self.INTERVAL
elif now >= self.first_above_time:
    self.dropping = True
    self.count += 1
    self.drop_next = now + (self.INTERVAL / math.sqrt(self.count))
    return pkt, True
```
- If packets consistently wait longer than 5ms for an entire 100ms interval, CoDel triggers a drop.
- Because TCP interprets packet loss as congestion, dropping just 1 or 2 packets forces the sender's congestion window down, clearing the bufferbloat immediately!

---

## 4. How to Run the Script

```bash
cd code/day-27
python codel_aqm_sim.py
```

### Expected Output
```
====================================================
DAY 27: CODEL ACTIVE QUEUE MANAGEMENT (RFC 8290)
====================================================
CoDel Target Delay   : 5.0 ms
CoDel Interval       : 100.0 ms

Packet   | Dequeue Time   | Sojourn Time   | CoDel Action
------------------------------------------------------------
1        | 25.0 ms        | 25.0 ms        | DELIVERED
2        | 50.0 ms        | 50.0 ms        | DELIVERED
3        | 75.0 ms        | 75.0 ms        | DELIVERED
4        | 100.0 ms       | 100.0 ms       | DELIVERED
5        | 125.0 ms       | 125.0 ms       | *** DROPPED (CoDel Signal) ***
6        | 150.0 ms       | 150.0 ms       | DELIVERED
7        | 175.0 ms       | 175.0 ms       | DELIVERED
8        | 200.0 ms       | 200.0 ms       | *** DROPPED (CoDel Signal) ***
9        | 225.0 ms       | 225.0 ms       | DELIVERED
10       | 250.0 ms       | 250.0 ms       | DELIVERED
------------------------------------------------------------
Packets Dropped by CoDel : 2 (IDs: [5, 8])
Packets Delivered Safely : 8

[VERIFIED] CoDel successfully identified bufferbloat and triggered drops!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`ValueError: math domain error`**:
   - `math.sqrt()` crashes if passed a negative number. Ensure `self.count >= 1`.
2. **Dropping Transient Bursts**:
   - If you trigger drops before waiting for `self.INTERVAL`, you will harm normal traffic bursts (like opening a webpage). Always require delay to persist for `100ms` before dropping.

---

## 6. Beginner Exercises & Challenges
1. **Transient Burst Test**: Enqueue 3 packets that wait 15ms each, then enqueue packets that wait only 2ms. Verify that CoDel does NOT drop anything, proving it tolerates short bursts!
2. **FQ-CoDel (Fair Queueing + CoDel)**: Research how modern Linux routers combine CoDel with per-flow hashing (FQ-CoDel) so video games and voice calls bypass file downloads completely.
