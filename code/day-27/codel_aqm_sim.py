#!/usr/bin/env python3
"""
Day 27 Lab: Controlled Delay (CoDel) Active Queue Management Simulator (RFC 8290)
Simulates router queue management based on packet sojourn time (dwell time)
rather than queue byte length, dropping packets on an inverse square root schedule.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class EnqueuedPacket:
    packet_id: int
    arrival_time: float  # seconds


class CoDelQueue:
    def __init__(self, target: float = 0.005, interval: float = 0.100):
        self.TARGET = target      # 5ms target buffer delay
        self.INTERVAL = interval  # 100ms inspection window
        self.queue: List[EnqueuedPacket] = []
        
        # State variables
        self.first_above_time: float = 0.0
        self.drop_next: float = 0.0
        self.dropping: bool = False
        self.count: int = 0
        self.dropped_packets: List[int] = []

    def enqueue(self, pkt_id: int, now: float):
        self.queue.append(EnqueuedPacket(pkt_id, now))

    def dequeue(self, now: float) -> Tuple[EnqueuedPacket, bool]:
        """
        Dequeues next packet and executes CoDel drop logic based on sojourn time.
        Returns: (packet, was_dropped)
        """
        if not self.queue:
            self.first_above_time = 0.0
            return None, False

        pkt = self.queue.pop(0)
        sojourn_time = now - pkt.arrival_time

        if sojourn_time < self.TARGET:
            # Buffer delay is safe; reset timer
            self.first_above_time = 0.0
            if self.dropping and (now - self.drop_next > 0):
                self.dropping = False
            return pkt, False

        # Sojourn time is ABOVE target!
        if self.first_above_time == 0.0:
            # First time exceeding target
            self.first_above_time = now + self.INTERVAL
        elif now >= self.first_above_time:
            # Delay has stayed above target for a full INTERVAL (persistent bufferbloat!)
            if not self.dropping:
                self.dropping = True
                self.count = 1
                self.drop_next = now + (self.INTERVAL / math.sqrt(self.count))
                self.dropped_packets.append(pkt.packet_id)
                return pkt, True
            elif now >= self.drop_next:
                # Time for next scheduled drop!
                self.count += 1
                self.drop_next = now + (self.INTERVAL / math.sqrt(self.count))
                self.dropped_packets.append(pkt.packet_id)
                return pkt, True

        return pkt, False


def main():
    print('====================================================')
    print('DAY 27: CODEL ACTIVE QUEUE MANAGEMENT (RFC 8290)')
    print('====================================================')

    codel = CoDelQueue(target=0.005, interval=0.100)
    print(f'CoDel Target Delay   : {codel.TARGET * 1000:.1f} ms')
    print(f'CoDel Interval       : {codel.INTERVAL * 1000:.1f} ms\n')

    # Enqueue a burst of 10 packets at t = 0.000s
    for i in range(1, 11):
        codel.enqueue(i, now=0.000)

    # Dequeue packets with high dwell time (simulating slow link = 25ms per packet)
    print(f'{"Packet":<8} | {"Dequeue Time":<14} | {"Sojourn Time":<14} | {"CoDel Action"}')
    print('-' * 60)

    now = 0.025
    delivered_count = 0
    while codel.queue:
        pkt, dropped = codel.dequeue(now)
        sojourn = now - pkt.arrival_time
        action = '*** DROPPED (CoDel Signal) ***' if dropped else 'DELIVERED'
        print(f'{pkt.packet_id:<8} | {now*1000:<14.1f} | {sojourn*1000:<14.1f} | {action}')
        if not dropped:
            delivered_count += 1
        now += 0.025  # Next packet dequeued 25ms later

    print('-' * 60)
    print(f'Packets Dropped by CoDel : {len(codel.dropped_packets)} (IDs: {codel.dropped_packets})')
    print(f'Packets Delivered Safely : {delivered_count}')

    assert len(codel.dropped_packets) > 0, 'CoDel must drop packets to signal sender under persistent delay'
    print('\n[VERIFIED] CoDel successfully identified bufferbloat and triggered drops!')


if __name__ == '__main__':
    main()
