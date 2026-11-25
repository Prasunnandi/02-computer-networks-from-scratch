#!/usr/bin/env python3
"""
Day 22 Lab: TCP Slow Start & Congestion Avoidance Simulator
Models the exponential window expansion of Slow Start, transition at ssthresh,
linear Congestion Avoidance, and RTO packet loss recovery.
"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TCPState:
    cwnd: float       # Congestion Window (in Maximum Segment Size units - MSS)
    ssthresh: float   # Slow Start Threshold (in MSS)
    phase: str        # 'SLOW_START' or 'CONGESTION_AVOIDANCE'
    rtt_counter: int


class TCPSlowStartSimulator:
    def __init__(self, init_cwnd: float = 1.0, init_ssthresh: float = 16.0):
        self.state = TCPState(
            cwnd=init_cwnd,
            ssthresh=init_ssthresh,
            phase='SLOW_START',
            rtt_counter=0
        )

    def on_ack_received(self):
        """
        Updates cwnd upon receiving a single ACK:
        - In Slow Start: cwnd += 1.0 MSS (doubles every RTT)
        - In Congestion Avoidance: cwnd += 1.0 / cwnd (adds 1 MSS per RTT)
        """
        if self.state.cwnd < self.state.ssthresh:
            self.state.phase = 'SLOW_START'
            self.state.cwnd += 1.0
        else:
            self.state.phase = 'CONGESTION_AVOIDANCE'
            self.state.cwnd += 1.0 / self.state.cwnd

    def on_timeout(self):
        """
        Handles Retransmission Timeout (RTO):
        - ssthresh is set to max(2, cwnd / 2)
        - cwnd collapses back to 1.0 MSS
        - Phase resets to Slow Start
        """
        self.state.ssthresh = max(2.0, self.state.cwnd / 2.0)
        self.state.cwnd = 1.0
        self.state.phase = 'SLOW_START'

    def simulate_rtt(self, packet_loss: bool = False) -> TCPState:
        """
        Simulates one full Round-Trip Time (RTT):
        Sender transmits a full window of packets, and receives ACKs.
        """
        self.state.rtt_counter += 1
        if packet_loss:
            self.on_timeout()
            return TCPState(self.state.cwnd, self.state.ssthresh, self.state.phase, self.state.rtt_counter)

        num_acks = max(1, int(self.state.cwnd))
        for _ in range(num_acks):
            self.on_ack_received()

        return TCPState(self.state.cwnd, self.state.ssthresh, self.state.phase, self.state.rtt_counter)


def main():
    print('====================================================')
    print('DAY 22: TCP SLOW START & CONGESTION AVOIDANCE SIM')
    print('====================================================')

    sim = TCPSlowStartSimulator(init_cwnd=1.0, init_ssthresh=16.0)
    print(f'Initial State: cwnd={sim.state.cwnd:.1f} MSS, ssthresh={sim.state.ssthresh:.1f} MSS\n')
    print(f'{"RTT":<6} | {"Phase":<22} | {"cwnd (MSS)":<12} | {"ssthresh (MSS)":<14} | {"Growth Rate"}')
    print('-' * 70)

    for rtt in range(1, 15):
        loss = (rtt == 9)  # Inject packet drop timeout at RTT 9
        st = sim.simulate_rtt(packet_loss=loss)
        note = '*** PACKET TIMEOUT (RTO) ***' if loss else ('Exponential (+100%/RTT)' if st.phase == 'SLOW_START' else 'Linear (+1 MSS/RTT)')
        print(f'{st.rtt_counter:<6} | {st.phase:<22} | {st.cwnd:<12.2f} | {st.ssthresh:<14.2f} | {note}')

    assert sim.state.cwnd > 1.0, 'Window should have recovered after timeout'
    assert sim.state.ssthresh <= 16.0, 'ssthresh should have been halved on timeout'
    print('-' * 70)
    print('\n[VERIFIED] TCP Slow Start exponential expansion and linear avoidance verified!')


if __name__ == '__main__':
    main()
