# Hands-On Lab: Day 25 - TCP CUBIC Polynomial Growth (`cubic_window_sim.py`)

## 1. What Are We Building & Why Does It Matter?
For decades, standard TCP Reno grew its congestion window by adding exactly 1 packet per Round-Trip Time ($+1$ MSS/RTT). On a 10 Mbps home DSL line with 20ms ping, this worked fine.

However, on modern high-speed long-distance fiber networks (such as 10 Gbps transatlantic links with 100ms latency), the **Bandwidth-Delay Product (BDP)** can be thousands of packets! If Reno suffers a single packet loss on a 10,000 packet window, it drops to 5,000 packets. To crawl back from 5,000 to 10,000 packets at $+1$ packet per 100ms RTT takes:
$$\frac{5000 \text{ packets}}{10 \text{ RTT/sec}} = 500 \text{ seconds (over 8 minutes!)}$$

To fix this fatal scalability defect, Linux adopted **TCP CUBIC** (RFC 8312) as its default congestion control algorithm.
CUBIC replaces linear RTT-dependent growth with a **cubic polynomial function of real wall-clock time $t$**:
$$W_{\text{cubic}}(t) = C(t - K)^3 + W_{\max}$$

CUBIC has three distinct phases:
1. **Concave Growth**: Rapidly accelerates window back towards the pre-loss capacity $W_{\max}$.
2. **Plateau**: Flattens out near $W_{\max}$ to ensure link stability.
3. **Convex Probing**: If no packet loss occurs, it curves upwards aggressively to discover newly available network capacity!

---

## 2. Python Concepts for Beginners
1. **Calculating Cube Roots in Python**:
   - Python does not have a built-in `cbrt` function in basic operators, but you can raise any number to the power of one third: `x ** (1.0 / 3.0)`.
   - Note: Be careful with negative bases! `(-8) ** (1/3)` in Python produces a complex number. That's why we compute $(t - K)^3$ directly.
2. **Absolute Value (`abs()`)**:
   - `abs(t - self.K) <= 0.2` checks whether `t` is within 0.2 seconds of `K`.
3. **The `while` Loop with Floating Steps**:
   - `while t <= duration_seconds:` advances `t += step` to generate time-series sample points.

---

## 3. Step-by-Step Code Walkthrough

### Calculating the Inflection Point $K$
```python
def compute_k(self) -> float:
    return ((self.w_max * self.beta) / self.C) ** (1.0 / 3.0)
```
- For $W_{\max} = 100$, $\beta = 0.2$, and $C = 0.4$:
  $$\frac{100 \times 0.2}{0.4} = \frac{20}{0.4} = 50$$
  $$K = \sqrt[3]{50} \approx 3.684 \text{ seconds}$$
- This means regardless of whether your ping is 10ms or 200ms, CUBIC will smoothly recover to $W_{\max}$ in exactly $3.684$ seconds!

### Evaluating the Cubic Function
```python
def window_at_time(self, t: float) -> float:
    diff = t - self.K
    return self.C * (diff ** 3) + self.w_max
```
- At $t = 0$: $\text{diff} = -3.684$. $(-3.684)^3 = -50$. $0.4 \times (-50) + 100 = -20 + 100 = 80$ MSS.
- At $t = K \approx 3.684$: $\text{diff} = 0$. Window is exactly $W_{\max} = 100$ MSS!
- At $t > K$: $\text{diff} > 0$. The cube of a positive number grows rapidly, shooting up to explore new bandwidth!

---

## 4. How to Run the Script

```bash
cd code/day-25
python cubic_window_sim.py
```

### Expected Output
```
====================================================
DAY 25: TCP CUBIC POLYNOMIAL WINDOW GROWTH (RFC 8312)
====================================================
W_max (Pre-loss window) : 100.0 MSS
CUBIC K (Recovery time) : 3.684 seconds

Time (s) | CUBIC cwnd   | CUBIC Region     | Reno cwnd   
-------------------------------------------------------
0.0      | 80.00        | Concave Growth   | 50.00       
1.0      | 92.29        | Concave Growth   | 60.00       
2.0      | 98.10        | Concave Growth   | 70.00       
3.0      | 99.87        | Concave Growth   | 80.00       
3.5      | 99.99        | Plateau (Stable) | 85.00       
4.0      | 100.01       | Plateau (Stable) | 90.00       
5.0      | 100.92       | Convex Probing   | 100.00      
6.0      | 105.00       | Convex Probing   | 110.00      
-------------------------------------------------------
Initial CUBIC Window (t=0s) : 80.00 MSS (Retained 80% capacity)
Final CUBIC Window (t=6s)   : 105.00 MSS (Convex bandwidth probing)

[VERIFIED] CUBIC polynomial concave/plateau/convex growth confirmed!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`ValueError: negative number cannot be raised to a fractional power`**:
   - If you ever compute `(-50) ** (1/3)`, Python either gives an error or a complex float like `(1.84 + 3.19j)`. Always keep fractional power bases positive!
2. **Wrong Multiplicative Decrease**:
   - In Reno, $\beta = 0.5$ (50% cut). In CUBIC, $\beta = 0.2$ (only a 20% cut, retaining 80% of window). Don't mix up the two!

---

## 6. Beginner Exercises & Challenges
1. **Transatlantic 10 Gbps Challenge**: Change $W_{\max} = 10000.0$ MSS. Calculate $K$. How long does CUBIC take to recover versus Reno's 500 seconds?
2. **Plot with Matplotlib (Optional)**: If you have `matplotlib` installed (`pip install matplotlib`), plot `c_w` and `r_w` over time to see the beautiful S-curve of CUBIC!
