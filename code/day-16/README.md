# Hands-On Lab: Day 16 - Zero Window & Persist Timer Simulator (`zero_window_probe_sim.py`)

## 1. What Are We Building & Why Does It Matter?
When a receiver's socket buffer fills up completely, it advertises `Window Size = 0` (Zero Window). This tells the sender to stop transmitting data.

If the subsequent window update ACK packet is lost in the network, both computers will deadlock forever.
To prevent this, the sender engages the **Persist Timer**:
- Sends periodic 1-byte **Zero Window Probes (ZWP)**.
- Uses **Exponential Backoff** (1s, 2s, 4s, 8s, up to 60s).

In this lab, we build `zero_window_probe_sim.py` to simulate the persist timer exponential backoff sequence.

---

## 2. Python Concepts for Beginners
1. **Exponential Multiplication (`timeout *= 2`)**:
   - Doubling a value each iteration.
2. **Capping Values (`min()`)**:
   - `min(timeout, 60.0)` ensures the timer never grows past 60 seconds.

---

## 3. Step-by-Step Code Walkthrough

```python
def simulate_persist_timer(initial_timeout_sec: float = 1.0, max_probes: int = 5) -> list:
    log = []
    timeout = initial_timeout_sec
    for probe_num in range(1, max_probes + 1):
        log.append({"probe": probe_num, "timeout_sec": timeout, "action": "Emit 1-Byte Zero Window Probe"})
        timeout = min(timeout * 2.0, 60.0)
    return log
```
- Each probe doubles the waiting time until the maximum clamp is reached.

---

## 4. How to Run the Script

```bash
cd code/day-16
python zero_window_probe_sim.py
```

### Expected Output
```
Persist Timer Exponential Backoff Schedule:
  Probe 1: After 1.0s -> Emit 1-Byte Zero Window Probe
  Probe 2: After 2.0s -> Emit 1-Byte Zero Window Probe
  Probe 3: After 4.0s -> Emit 1-Byte Zero Window Probe
  Probe 4: After 8.0s -> Emit 1-Byte Zero Window Probe
  Probe 5: After 16.0s -> Emit 1-Byte Zero Window Probe
```

---

## 5. Beginner Exercises to Try
1. Increase `max_probes` to `10` and observe how the timer clamps at `60.0s`.
2. Add a simulated response: on probe 4, the receiver re-opens the window (`win=4096`).
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

