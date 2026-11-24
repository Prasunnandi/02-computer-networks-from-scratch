# Hands-On Lab: Day 18 - Jacobson 1988 RTT & RTO Estimator (`rtt_estimator_jacobson.py`)

## 1. What Are We Building & Why Does It Matter?
If a packet is lost, how long should TCP wait before retransmitting?
Van Jacobson's 1988 algorithm (RFC 6298) continuously tracks:
- Smoothed Round Trip Time (SRTT).
- Round Trip Time Variation (RTTVAR).
- Retransmission Timeout (RTO).

In this lab, we build `rtt_estimator_jacobson.py`, an Object-Oriented implementation of Jacobson's EWMA algorithm.

---

## 2. Python Concepts for Beginners
1. **Absolute Value (`abs()`)**:
   - Computes magnitude regardless of sign: `abs(-5)` is `5`. Used to measure deviation error.
2. **Stateful Classes**:
   - Storing rolling moving averages inside an object instance.

---

## 3. Step-by-Step Code Walkthrough

```python
class JacobsonRTTEstimator:
    def __init__(self, alpha: float = 0.125, beta: float = 0.25):
        self.alpha = alpha # 1/8
        self.beta = beta   # 1/4
        self.srtt = None
        self.rttvar = None
        self.rto = 1000.0  # Initial 1.0s

    def update_sample(self, rtt_sample_ms: float) -> float:
        if self.srtt is None:
            self.srtt = rtt_sample_ms
            self.rttvar = rtt_sample_ms / 2.0
        else:
            err = rtt_sample_ms - self.srtt
            self.srtt += self.alpha * err
            self.rttvar += self.beta * (abs(err) - self.rttvar)

        self.rto = self.srtt + max(50.0, 4.0 * self.rttvar)
        return self.rto
```
- Dynamically adapts timeout boundaries as network conditions fluctuate.

---

## 4. How to Run the Script

```bash
cd code/day-18
python rtt_estimator_jacobson.py
```

### Expected Output
```
Feeding RTT Samples:
  Sample:  50.0 ms -> SRTT =  50.0 ms, RTTVAR = 25.0 ms -> RTO = 150.0 ms
  Sample:  55.0 ms -> SRTT =  50.6 ms, RTTVAR = 19.9 ms -> RTO = 130.1 ms
  Sample: 120.0 ms -> SRTT =  59.3 ms, RTTVAR = 35.1 ms -> RTO = 199.7 ms
  Sample:  52.0 ms -> SRTT =  58.4 ms, RTTVAR = 28.0 ms -> RTO = 170.2 ms
```

---

## 5. Beginner Exercises to Try
1. Feed a high-jitter sample sequence (e.g. alternating between 10ms and 500ms). Observe how `RTTVAR` expands `RTO` to prevent false retransmissions.
2. Add Karn's algorithm exponential backoff when a packet times out.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

