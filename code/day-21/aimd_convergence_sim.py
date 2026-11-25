#!/usr/bin/env python3
"""
Day 21 Lab: Chiu-Jain AIMD Convergence Simulator
Demonstrates mathematical convergence to fairness and efficiency
under Additive Increase / Multiplicative Decrease (AIMD) dynamics.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Flow:
    flow_id: int
    rate: float  # Packets per RTT


def jains_fairness_index(rates: List[float]) -> float:
    """
    Computes Jain's Fairness Index:
    J(x_1, ..., x_n) = (sum(x_i))^2 / (n * sum(x_i^2))
    Returns 1.0 when perfectly fair, and 1/n in worst case.
    """
    n = len(rates)
    if n == 0 or sum(rates) == 0:
        return 1.0
    sum_rates = sum(rates)
    sum_sq_rates = sum(r * r for r in rates)
    return (sum_rates * sum_rates) / (n * sum_sq_rates)


class AIMDSimulator:
    def __init__(self, capacity: float, alpha: float = 1.0, beta: float = 0.5):
        self.capacity = capacity
        self.alpha = alpha  # Additive increase (packets per RTT)
        self.beta = beta    # Multiplicative decrease factor (0.5 = 50% cut)

    def run(self, initial_rates: List[float], rounds: int = 120) -> List[Tuple[int, List[float], float]]:
        flows = [Flow(i, rate) for i, rate in enumerate(initial_rates)]
        history = []

        for r in range(rounds):
            rates = [f.rate for f in flows]
            total_load = sum(rates)
            fairness = jains_fairness_index(rates)
            history.append((r, rates.copy(), fairness))

            if total_load > self.capacity:
                # Congestion detected! Multiplicative Decrease
                for f in flows:
                    f.rate = max(1.0, f.rate * self.beta)
            else:
                # Pipe has room: Additive Increase
                for f in flows:
                    f.rate += self.alpha

        return history


def main():
    print('====================================================')
    print('DAY 21: CHIU-JAIN AIMD PHASE PLANE CONVERGENCE')
    print('====================================================')
    
    capacity = 100.0  # Bottleneck link bandwidth
    sim = AIMDSimulator(capacity=capacity, alpha=1.0, beta=0.5)

    # Heavily unfair starting point: Flow 0 has 10 pkts, Flow 1 has 90 pkts
    init_rates = [10.0, 90.0]
    init_fairness = jains_fairness_index(init_rates)
    print(f'Link Capacity       : {capacity} packets/RTT')
    print(f'Flow 0 Initial Rate : {init_rates[0]} pkts/RTT')
    print(f'Flow 1 Initial Rate : {init_rates[1]} pkts/RTT')
    print(f'Initial Fairness    : {init_fairness:.4f} (Very unfair!)\n')

    history = sim.run(init_rates, rounds=120)
    print(f'{"Round":<6} | {"Flow 0 Rate":<12} | {"Flow 1 Rate":<12} | {"Total Load":<10} | {"Fairness Index":<14}')
    print('-' * 65)

    for r, rates, fairness in history[::12]:  # Sample every 12 rounds
        load = sum(rates)
        print(f'{r:<6} | {rates[0]:<12.2f} | {rates[1]:<12.2f} | {load:<10.2f} | {fairness:<14.4f}')

    final_rates = history[-1][1]
    final_fairness = history[-1][2]
    rate_diff = abs(final_rates[0] - final_rates[1])

    print('-' * 65)
    print(f'Final Rates         : Flow 0 = {final_rates[0]:.2f}, Flow 1 = {final_rates[1]:.2f}')
    print(f'Final Fairness      : {final_fairness:.4f}')
    print(f'Rate Difference     : {rate_diff:.2f} pkts/RTT')

    assert final_fairness > 0.98, 'Fairness index must converge towards 1.0'
    assert rate_diff < 5.0, 'Flow rates must converge within epsilon of fair share'
    print('\n[VERIFIED] Chiu-Jain Theorem demonstrated: AIMD converged to fairness line!')


if __name__ == '__main__':
    main()
