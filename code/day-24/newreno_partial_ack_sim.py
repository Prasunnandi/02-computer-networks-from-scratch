#!/usr/bin/env python3
"""
Day 24 Lab: TCP NewReno Partial ACK Recovery Simulator (RFC 6582)
Demonstrates how NewReno solves Reno's catastrophic stall when
multiple packets are dropped from a single transmission window.
"""

from dataclasses import dataclass
from typing import List, Set


@dataclass
class Packet:
    seq: int
    data: str


class TCPNewRenoSender:
    def __init__(self, window_size: int = 10):
        self.snd_una = 1         # Smallest unacknowledged sequence number
        self.snd_nxt = 1         # Next sequence number to send
        self.cwnd = float(window_size)
        self.ssthresh = 32.0
        self.in_fast_recovery = False
        self.recover = 0         # RFC 6582 recovery marker
        self.retransmitted: Set[int] = set()

    def transmit_window(self, total_packets: int = 10) -> List[int]:
        sent = []
        while self.snd_nxt <= total_packets and (self.snd_nxt - self.snd_una) < int(self.cwnd):
            sent.append(self.snd_nxt)
            self.snd_nxt += 1
        return sent

    def on_three_dup_acks(self, ack_num: int):
        """
        Enters Fast Recovery (RFC 6582):
        Sets recover = snd_nxt - 1 (the highest sequence sent so far).
        """
        self.ssthresh = max(2.0, self.cwnd / 2.0)
        self.cwnd = self.ssthresh + 3.0
        self.recover = self.snd_nxt - 1
        self.in_fast_recovery = True
        self.retransmitted.add(ack_num)

    def on_ack_received(self, ack_num: int) -> str:
        """
        Processes incoming ACK according to RFC 6582 rules.
        """
        if not self.in_fast_recovery:
            self.snd_una = ack_num
            self.cwnd += 1.0 / self.cwnd
            return 'NORMAL_ACK'

        if ack_num < self.recover:
            # PARTIAL ACK
            self.snd_una = ack_num
            self.retransmitted.add(ack_num)
            self.cwnd = self.ssthresh
            return f'PARTIAL_ACK (Immediate Retransmit Seq {ack_num})'
        else:
            # FULL ACK
            self.snd_una = ack_num
            self.cwnd = self.ssthresh
            self.in_fast_recovery = False
            return 'FULL_ACK (Exit Fast Recovery)'


def main():
    print('====================================================')
    print('DAY 24: TCP NEWRENO MULTI-PACKET DROP RECOVERY (RFC 6582)')
    print('====================================================')

    sender = TCPNewRenoSender(window_size=8)
    print(f'Sending initial window of 8 packets (Seq 1 to 8)...')
    sent = sender.transmit_window(8)
    print(f'Transmitted packets: {sent}')

    print('\n[NETWORK EVENT] Packets 3 and 5 dropped by router!')
    print('Packets 1 and 2 arrive -> Receiver sends ACK 3')
    print('Packets 4, 6, 7, 8 arrive -> Receiver sends 4 Duplicate ACKs for 3!')

    sender.on_three_dup_acks(ack_num=3)
    print(f'\n-> Entered Fast Recovery! recover marker set to Seq {sender.recover}')
    print(f'-> Retransmitted Seq 3: {sender.retransmitted}')

    print('\n--- Receiving ACK 5 ---')
    event1 = sender.on_ack_received(5)
    print(f'Sender Action : {event1}')
    print(f'Still in Fast Recovery: {sender.in_fast_recovery} (NewReno does NOT stall!)')
    assert 5 in sender.retransmitted, 'NewReno must immediately retransmit packet 5'

    print('\n--- Receiving ACK 9 ---')
    event2 = sender.on_ack_received(9)
    print(f'Sender Action : {event2}')
    print(f'In Fast Recovery: {sender.in_fast_recovery}')
    assert not sender.in_fast_recovery, 'Full ACK must exit Fast Recovery'

    print('\n[VERIFIED] NewReno successfully recovered multiple packet drops without RTO stall!')


if __name__ == '__main__':
    main()
