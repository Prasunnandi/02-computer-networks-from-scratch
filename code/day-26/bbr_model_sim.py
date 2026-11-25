#!/usr/bin/env python3
"""
Day 26 Lab: Google BBR Congestion Control Simulator
Models BBR's tracking of max Bottleneck Bandwidth (BtlBw) and min RTprop
to operate at the Kleinrock optimal operating point without queue buildup.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class BBRState:
    btl_bw: float     # Estimated Bottleneck Bandwidth (packets / sec)
    rt_prop: float    # Estimated Round-Trip Propagation Delay (seconds)
    pacing_rate: float
    target_cwnd: float
    state: str        # 'STARTUP', 'DRAIN', 'PROBE_BW', 'PROBE_RTT'


class BBRSimulator:
    def __init__(self, physical_bw: float = 1000.0, min_rtt: float = 0.050):
        self.physical_bw = physical_bw  # Physical link bottleneck (1000 pkts/s)
        self.physical_rtt = min_rtt    # Physical wire propagation delay (50ms)
        self.bw_samples: List[float] = []
        self.rtt_samples: List[float] = []
        self.mode = 'STARTUP'

    def update_model(self, delivered_bw: float, measured_rtt: float) -> BBRState:
        """
        Updates BtlBw (max filter over window) and RTprop (min filter over window).
        Calculates pacing rate and target cwnd.
        """
        self.bw_samples.append(delivered_bw)
        if len(self.bw_samples) > 10:
            self.bw_samples.pop(0)

        self.rtt_samples.append(measured_rtt)
        if len(self.rtt_samples) > 10:
            self.rtt_samples.pop(0)

        btl_bw = max(self.bw_samples)
        rt_prop = min(self.rtt_samples)

        # State transitions
        if self.mode == 'STARTUP':
            pacing_gain = 2.885  # 2 / ln(2)
            cw_gain = 2.885
            if len(self.bw_samples) >= 3 and delivered_bw >= self.physical_bw * 0.95:
                self.mode = 'DRAIN'
        elif self.mode == 'DRAIN':
            pacing_gain = 1.0 / 2.885
            cw_gain = 2.885
            if measured_rtt <= self.physical_rtt * 1.05:
                self.mode = 'PROBE_BW'
        else:
            self.mode = 'PROBE_BW'
            pacing_gain = 1.0
            cw_gain = 2.0

        pacing_rate = btl_bw * pacing_gain
        bdp = btl_bw * rt_prop
        target_cwnd = bdp * cw_gain

        return BBRState(btl_bw, rt_prop, pacing_rate, target_cwnd, self.mode)


def main():
    print('====================================================')
    print('DAY 26: GOOGLE BBR CONGESTION CONTROL MODEL (CARDWELL ET AL.)')
    print('====================================================')

    sim = BBRSimulator(physical_bw=1000.0, min_rtt=0.050)
    print('Physical Bottleneck : 1,000 pkts/sec')
    print('Physical Min RTT    : 50.0 ms (0.050s)')
    print('Physical BDP        : 50 packets\n')

    # Simulate sequence of observations
    samples = [
        (100.0, 0.050),
        (250.0, 0.051),
        (600.0, 0.052),
        (980.0, 0.055),  # Bottleneck reached!
        (1000.0, 0.075), # Router queue filling up
        (1000.0, 0.060), # Draining queue
        (1000.0, 0.050), # Back to min RTT
        (1000.0, 0.050), # Stable PROBE_BW
    ]

    print(f'{"Step":<5} | {"Mode":<10} | {"BtlBw (pkts/s)":<16} | {"RTprop (ms)":<12} | {"Pacing Rate":<14} | {"Target cwnd"}')
    print('-' * 75)

    for i, (bw, rtt) in enumerate(samples, 1):
        st = sim.update_model(bw, rtt)
        print(f'{i:<5} | {st.state:<10} | {st.btl_bw:<16.1f} | {st.rt_prop*1000:<12.1f} | {st.pacing_rate:<14.1f} | {st.target_cwnd:<10.1f} pkts')

    assert st.btl_bw == 1000.0, 'BtlBw must converge to 1000 pkts/sec'
    assert abs(st.rt_prop - 0.050) < 0.001, 'RTprop must track 50ms wire delay'
    print('-' * 75)
    print('\n[VERIFIED] Google BBR tracked physical bottleneck without loss-based collapse!')


if __name__ == '__main__':
    main()
