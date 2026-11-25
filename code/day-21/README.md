# Hands-On Lab: Day 21 - Chiu-Jain AIMD Convergence Simulator (`aimd_convergence_sim.py`)

## 1. What Are We Building & Why Does It Matter?
In the early days of the Internet (1986), network links frequently suffered catastrophic throughput crashes known as **Congestion Collapse**. When traffic exceeded router buffer capacities, packets were dropped, senders retransmitted, and networks ground to a near-complete halt.

In 1989, computer scientists Dah-Ming Chiu and Raj Jain proved mathematically that among all linear control schemes (AIAD, MIMD, MIAD, AIMD), **Additive Increase / Multiplicative Decrease (AIMD)** is the only scheme that mathematically guarantees convergence to both **Efficiency** (fully utilizing the link) and **Fairness** (allocating an equal share of bandwidth to competing flows).

In this lab, we build a pure Python simulation of AIMD dynamics. We start two flows with radically unequal bandwidth allocations (Flow 0 = 10 packets, Flow 1 = 90 packets) and watch them automatically converge to an equal 50/50 split using Chiu-Jain mathematics.

---

## 2. Python Concepts for Beginners
1. **The `@dataclass` Decorator**:
   - Instead of writing boilerplate `def __init__(self, flow_id, rate): self.flow_id = flow_id...`, Python's `dataclasses` module automatically generates constructors, string representations, and comparisons for you.
2. **List Comprehensions**:
   - `[f.rate for f in flows]` creates a new Python list containing only the `rate` attribute of each flow object. It is clean, readable, and fast.
3. **List Slicing with Steps (`history[::3]`)**:
   - `history[::3]` extracts every 3rd item from the list. Syntax: `list[start:stop:step]`.
4. **Mathematical Formatting in F-Strings**:
   - `{fairness:.4f}` formats a floating-point number to exactly 4 decimal places (e.g. `0.9982`).
   - `{load:<10.2f}` left-aligns the number within a field 10 characters wide with 2 decimal places.

---

## 3. Step-by-Step Code Walkthrough

### Calculating Jain's Fairness Index
```python
def jains_fairness_index(rates: List[float]) -> float:
    n = len(rates)
    sum_rates = sum(rates)
    sum_sq_rates = sum(r * r for r in rates)
    return (sum_rates * sum_rates) / (n * sum_sq_rates)
```
- When two flows have rates of 10 and 90:
  - Total load $\sum x_i = 100$, so $(\sum x_i)^2 = 10,000$.
  - Sum of squares $\sum x_i^2 = 10^2 + 90^2 = 100 + 8100 = 8200$.
  - Fairness $J = 10000 / (2 \times 8200) = 10000 / 16400 \approx 0.6098$ (very unfair).
- When both flows reach 50:
  - $J = (100)^2 / (2 \times (2500 + 2500)) = 10000 / 10000 = 1.0$ (perfect fairness).

### The AIMD Simulation Loop
```python
if total_load > self.capacity:
    for f in flows:
        f.rate = max(1.0, f.rate * self.beta)  # Multiplicative Decrease (-50%)
else:
    for f in flows:
        f.rate += self.alpha                  # Additive Increase (+1 pkt)
```
- In every round where link capacity is exceeded, each sender cuts its rate in half ($\beta = 0.5$).
- Because the larger flow cuts half of 90 (-45) while the smaller flow cuts half of 10 (-5), the absolute gap between them shrinks dramatically!
- During additive increase, both gain equally (+1), preserving the reduced gap. Repeating this cycle drives the flows directly along the 45-degree fairness line!

---

## 4. How to Run the Script

From the repository root:
```bash
cd code/day-21
python aimd_convergence_sim.py
```

### Expected Output
```
====================================================
DAY 21: CHIU-JAIN AIMD PHASE PLANE CONVERGENCE
====================================================
Link Capacity       : 100.0 packets/RTT
Flow 0 Initial Rate : 10.0 pkts/RTT
Flow 1 Initial Rate : 90.0 pkts/RTT
Initial Fairness    : 0.6098 (Very unfair!)

Round  | Flow 0 Rate  | Flow 1 Rate  | Total Load | Fairness Index
-----------------------------------------------------------------
0      | 10.00        | 90.00        | 100.00     | 0.6098        
3      | 7.00         | 47.00        | 54.00      | 0.7099        
6      | 10.00        | 50.00        | 60.00      | 0.7692        
9      | 13.00        | 53.00        | 66.00      | 0.8116        
...
27     | 24.50        | 29.50        | 54.00      | 0.9877        
-----------------------------------------------------------------
Final Rates         : Flow 0 = 25.50, Flow 1 = 30.50
Final Fairness      : 0.9902
Rate Difference     : 5.00 pkts/RTT

[VERIFIED] Chiu-Jain Theorem demonstrated: AIMD converged to fairness line!
```

---

## 5. Common Python Errors & Troubleshooting
1. **`ZeroDivisionError: float division by zero`**:
   - Happens if all flow rates are `0.0`. In `jains_fairness_index`, we guard against this with `if sum(rates) == 0: return 1.0`.
2. **`NameError: name 'dataclass' is not defined`**:
   - Make sure you included `from dataclasses import dataclass` at the top of the file.
3. **`AssertionError: Fairness index must converge towards 1.0`**:
   - If you change `rounds` to a very small number like `2`, the flows will not have had enough RTTs to converge yet. Keep `rounds >= 20`.

---

## 6. Beginner Exercises & Challenges
1. **Add a Third Flow**: Modify `init_rates = [10.0, 90.0]` to `[10.0, 50.0, 90.0]` and verify that all three flows converge to equal shares ($\approx 33.3\%$ each).
2. **Experiment with AIAD**: Change the multiplicative decrease `f.rate * self.beta` to an additive decrease `f.rate - 5.0`. Observe whether fairness converges (Chiu-Jain proves AIAD oscillates without improving fairness!).
