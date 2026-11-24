# Hands-On Lab: Day 17 - Nagle's Algorithm & Delayed ACK Simulator (`nagle_delayed_ack_sim.py`)

## 1. What Are We Building & Why Does It Matter?
Nagle's Algorithm buffers outgoing small packets until previous packets are acknowledged.
Delayed ACKs delay sending acknowledgments for up to 40ms to piggyback on reverse data.
When combined, sending two small packets in a row triggers a **40ms deadlock**!

In this lab, we build `nagle_delayed_ack_sim.py` to simulate what happens when two writes occur with and without the `TCP_NODELAY` socket option.

---

## 2. Python Concepts for Beginners
1. **Simulating Latency Clocks**:
   - We track elapsed time in a float variable `total_latency_ms`.
2. **Boolean Flags**:
   - `tcp_nodelay = True` bypasses the Nagle buffering check.

---

## 3. Step-by-Step Code Walkthrough

```python
def simulate_nagle_delayed_ack(payload1_bytes: int, payload2_bytes: int,
                              tcp_nodelay: bool = False, mss: int = 1460) -> dict:
    if tcp_nodelay:
        # Both packets transmitted immediately!
        return {"delayed_ack_stall": False, "latency_ms": 0.2}

    # If Nagle is active and packet 1 < MSS:
    if payload1_bytes < mss:
        # Packet 2 is stalled until ACK arrives!
        # Receiver holds ACK for 40ms delayed ACK timer
        return {"delayed_ack_stall": True, "latency_ms": 40.2}
```
- Demonstrates how a missing `TCP_NODELAY` flag causes a 200x latency spike!

---

## 4. How to Run the Script

```bash
cd code/day-17
python nagle_delayed_ack_sim.py
```

### Expected Output
```
Scenario A: Default TCP (Nagle Enabled, Delayed ACK Enabled)
  Write 1 (100 bytes) + Write 2 (500 bytes)
  Result: STALLED! 40ms Deadlock Triggered. Total Latency: 40.20 ms

Scenario B: Low-Latency Mode (TCP_NODELAY Enabled)
  Write 1 (100 bytes) + Write 2 (500 bytes)
  Result: NO DELAY. Total Latency: 0.20 ms
```

---

## 5. Beginner Exercises to Try
1. Change `payload1_bytes` to `1500` (exceeding MSS). Notice that Nagle does not buffer full MSS packets!
2. Add a simulation of `writev()` sending both chunks in a single packet.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

