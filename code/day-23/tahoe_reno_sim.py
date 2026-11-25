#!/usr/bin/env python3
"""
Day 23 Lab: TCP Tahoe vs Reno Congestion Control Simulator
Side-by-side comparison of Tahoe (Fast Retransmit with Slow Start collapse)
versus Reno (Fast Retransmit with Fast Recovery window inflation).
"""

from dataclasses import dataclass
from typing import List


@dataclass
class FlowResult:
    algorithm: str
    cwnd_history: List[float]
    total_packets_delivered: int


def simulate_tcp(algorithm: str, rounds: int = 20, loss_round: int = 8) -> FlowResult:
    """
    Simulates TCP Tahoe or TCP Reno over a sequence of RTT rounds.
    """
    cwnd = 1.0
    ssthresh = 32.0
    phase = 'SLOW_START'
    cwnd_history = []
    delivered = 0

    for r in range(1, rounds + 1):
        cwnd_history.append(cwnd)
        delivered += int(cwnd)

        if r == loss_round:
            # 3 Duplicate ACKs received! (Packet loss detected without timeout)
            ssthresh = max(2.0, cwnd / 2.0)
            if algorithm == 'Tahoe':
                # Tahoe treats 3 Dup ACKs identically to a timeout: collapse to 1 MSS!
                cwnd = 1.0
                phase = 'SLOW_START'
            elif algorithm == 'Reno':
                # Reno enters Fast Recovery: inflate window by 3 MSS for dup ACKs in flight
                cwnd = ssthresh + 3.0
                phase = 'FAST_RECOVERY'
        else:
            if phase == 'FAST_RECOVERY':
                # New ACK arrives acknowledging lost packet: exit Fast Recovery to Congestion Avoidance
                cwnd = ssthresh
                phase = 'CONGESTION_AVOIDANCE'
            elif cwnd < ssthresh:
                # Slow start: double cwnd
                cwnd *= 2.0
            else:
                # Congestion avoidance: linear increase
                cwnd += 1.0

    return FlowResult(algorithm, cwnd_history, delivered)


def main():
    print('====================================================')
    print('DAY 23: TCP TAHOE VS RENO FAST RECOVERY COMPARISON')
    print('====================================================')

    tahoe = simulate_tcp('Tahoe', rounds=16, loss_round=7)
    reno = simulate_tcp('Reno', rounds=16, loss_round=7)

    print(f'{"Round":<6} | {"Tahoe cwnd":<12} | {"Reno cwnd":<12} | {"Difference (Reno Advantage)"}')
    print('-' * 60)

    for r in range(16):
        t_w = tahoe.cwnd_history[r]
        r_w = reno.cwnd_history[r]
        diff = r_w - t_w
        tag = ' <--- 3 DUP ACKS LOSS DETECTED' if r == 6 else ''
        print(f'{r+1:<6} | {t_w:<12.1f} | {r_w:<12.1f} | +{diff:<6.1f} MSS{tag}')

    print('-' * 60)
    print(f'Total Packets Delivered (Tahoe) : {tahoe.total_packets_delivered}')
    print(f'Total Packets Delivered (Reno)  : {reno.total_packets_delivered}')
    advantage = ((reno.total_packets_delivered - tahoe.total_packets_delivered) / tahoe.total_packets_delivered) * 100.0
    print(f'Reno Throughput Advantage       : +{advantage:.1f}%')

    assert reno.total_packets_delivered > tahoe.total_packets_delivered, 'Reno must deliver more packets than Tahoe'
    print('\n[VERIFIED] TCP Reno Fast Recovery avoids Tahoe throughput cliff!')


if __name__ == '__main__':
    main()
