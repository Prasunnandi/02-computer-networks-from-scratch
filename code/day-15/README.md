# Hands-On Lab: Day 15 - TCP Sliding Window & Flow Control Simulator (`sliding_window_sim.py`)

## 1. What Are We Building & Why Does It Matter?
In TCP, a fast sender must not overwhelm a slow receiver. The receiver advertises its available buffer space in the **Window Size** field.
The sender maintains:
- `SND.UNA`: Lowest unacknowledged byte number.
- `SND.NXT`: Next byte number to be sent.
- `SND.WND`: Receiver's advertised window.

The **Usable Window** is the number of additional bytes the sender is allowed to transmit immediately:
$$	ext{Usable Window} = 	ext{SND.UNA} + 	ext{SND.WND} - 	ext{SND.NXT}$$

In this lab, we build `sliding_window_sim.py` to calculate usable window boundaries and compute the **Bandwidth-Delay Product (BDP)**.

---

## 2. Python Concepts for Beginners
1. **Scientific Notation (`1e9`)**:
   - In Python, `1e9` represents $10^9 = 1,000,000,000$ (one billion, used for gigabits).
2. **Custom Math Calculations**:
   - Converting bandwidth and round-trip time into total in-flight bytes.

---

## 3. Step-by-Step Code Walkthrough

```python
def calculate_bdp_bytes(bandwidth_gbps: float, rtt_ms: float) -> dict:
    bandwidth_bps = bandwidth_gbps * 1e9
    rtt_sec = rtt_ms / 1000.0
    bdp_bits = bandwidth_bps * rtt_sec
    bdp_bytes = int(bdp_bits / 8)
    return {"bdp_bytes": bdp_bytes, "needs_window_scale": bdp_bytes > 65535}
```
- If the required BDP exceeds 65,535 bytes, the connection **must** negotiate the Window Scale option (RFC 7323) to avoid throughput starvation!

---

## 4. How to Run the Script

```bash
cd code/day-15
python sliding_window_sim.py
```

### Expected Output
```
Sliding Window State:
  SND.UNA (Oldest Unacked): 1000
  SND.NXT (Next to Send)  : 3000
  SND.WND (Advertised Win): 4096
  In Flight Bytes         : 2000
  Usable Window           : 2096 bytes (Allowed to send immediately)

Bandwidth-Delay Product Calculation (10.0 Gbps link, 80.0 ms RTT):
  Required Pipe Capacity  : 100,000,000 bytes (95.37 MB)
  Standard 16-bit Window  : 65,535 bytes (0.065 MB)
  Window Scale Required?  : True (Shift count factor 12-14 needed!)
```

---

## 5. Beginner Exercises to Try
1. Calculate the maximum achievable speed without Window Scale on a 200ms satellite link.
2. Add a function that simulates the receiver sending an ACK that slides `SND.UNA` forward by 1000 bytes.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

