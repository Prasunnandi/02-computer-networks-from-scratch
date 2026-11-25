#!/usr/bin/env python3
"""
Day 25 Lab: TCP CUBIC Polynomial Growth Window Simulator (RFC 8312)
Simulates CUBIC window growth W_cubic(t) = C*(t - K)^3 + W_max
and contrasts it with traditional TCP Reno linear growth over high-BDP links.
"""

import math
from typing import List, Tuple


class TCPCubic:
    def __init__(self, c_param: float = 0.4, beta: float = 0.2):
        self.C = c_param          # CUBIC scaling constant (typically 0.4)
        self.beta = beta          # Multiplicative decrease factor (0.2 means reduction by 20%, or cwnd * 0.8)
        self.w_max = 100.0        # Window size right before last loss event (MSS)
        self.K = self.compute_k() # Time duration for window to reach w_max without loss

    def compute_k(self) -> float:
        """
        Computes K = ((w_max * beta) / C) ** (1/3)
        The time elapsed from loss event until window recovers back to w_max.
        """
        return ( (self.w_max * self.beta) / self.C ) ** (1.0 / 3.0)

    def window_at_time(self, t: float) -> float:
        """
        RFC 8312 Equation (1):
        W_cubic(t) = C * (t - K)^3 + W_max
        """
        diff = t - self.K
        return self.C * (diff ** 3) + self.w_max


def simulate_cubic_vs_reno(w_max: float = 100.0, duration_seconds: float = 6.0, step: float = 0.5):
    cubic = TCPCubic(c_param=0.4, beta=0.2)
    cubic.w_max = w_max
    cubic.K = cubic.compute_k()

    reno_start = w_max * 0.5
    reno_growth_per_sec = 10.0  # 1 MSS per 100ms RTT

    print(f'W_max (Pre-loss window) : {w_max} MSS')
    print(f'CUBIC K (Recovery time) : {cubic.K:.3f} seconds\n')
    print(f'{"Time (s)":<8} | {"CUBIC cwnd":<12} | {"CUBIC Region":<16} | {"Reno cwnd":<12}')
    print('-' * 55)

    results = []
    t = 0.0
    while t <= duration_seconds:
        c_w = cubic.window_at_time(t)
        r_w = reno_start + (t * reno_growth_per_sec)

        if t < (cubic.K - 0.2):
            region = 'Concave Growth'
        elif abs(t - cubic.K) <= 0.2:
            region = 'Plateau (Stable)'
        else:
            region = 'Convex Probing'

        print(f'{t:<8.1f} | {c_w:<12.2f} | {region:<16} | {r_w:<12.2f}')
        results.append((t, c_w, r_w))
        t += step

    return results


def main():
    print('====================================================')
    print('DAY 25: TCP CUBIC POLYNOMIAL WINDOW GROWTH (RFC 8312)')
    print('====================================================')

    results = simulate_cubic_vs_reno(w_max=100.0, duration_seconds=6.0, step=0.5)

    w_0 = results[0][1]
    assert abs(w_0 - 80.0) < 0.5, f'Expected initial cwnd near 80, got {w_0}'

    w_final = results[-1][1]
    assert w_final > 100.0, f'CUBIC must probe higher bandwidth, got {w_final}'

    print('-' * 55)
    print(f'Initial CUBIC Window (t=0s) : {w_0:.2f} MSS (Retained 80% capacity)')
    print(f'Final CUBIC Window (t=6s)   : {w_final:.2f} MSS (Convex bandwidth probing)')
    print('\n[VERIFIED] CUBIC polynomial concave/plateau/convex growth confirmed!')


if __name__ == '__main__':
    main()
