#!/usr/bin/env python3
"""
Day 28 Lab: Bandwidth-Delay Product (BDP) & Linux Socket Buffer Tuner
Calculates physical BDP, required TCP receive/send buffer sizes,
window scale factor (RFC 7323), and generates optimal sysctl.conf settings.
"""

import math
from dataclasses import dataclass


@dataclass
class NetworkLink:
    name: str
    bandwidth_mbps: float  # Megabits per second
    rtt_ms: float          # Round-Trip Time in milliseconds


def calculate_bdp_and_buffers(link: NetworkLink):
    """
    Computes BDP in bytes, maximum window scaling shift,
    and Linux kernel tcp_rmem / tcp_wmem parameters.
    """
    # 1 Mbps = 1,000,000 bits/sec
    # RTT in seconds = rtt_ms / 1000.0
    bdp_bits = (link.bandwidth_mbps * 1e6) * (link.rtt_ms / 1000.0)
    bdp_bytes = bdp_bits / 8.0

    # For TCP receive buffer, standard recommendation is 2x BDP
    # (to accommodate packet reordering, TCP/IP header overhead, and socket buffer slack)
    optimal_rmem_max = int(bdp_bytes * 2.0)
    optimal_wmem_max = int(bdp_bytes * 2.0)

    # Standard unscaled TCP window limit is 65,535 bytes (16 bits)
    standard_window_limit = 65535
    needs_window_scaling = bdp_bytes > standard_window_limit

    # Calculate required window scale shift factor (up to max 14)
    if needs_window_scaling:
        # 65535 * (2 ** shift) >= bdp_bytes
        ratio = bdp_bytes / standard_window_limit
        shift = min(14, math.ceil(math.log2(ratio)))
    else:
        shift = 0

    return {
        'bdp_bytes': int(bdp_bytes),
        'bdp_kb': bdp_bytes / 1024.0,
        'bdp_mb': bdp_bytes / (1024.0 * 1024.0),
        'needs_scaling': needs_window_scaling,
        'window_scale_shift': shift,
        'tcp_rmem_max': optimal_rmem_max,
        'tcp_wmem_max': optimal_wmem_max,
    }


def main():
    print('====================================================')
    print('DAY 28: BANDWIDTH-DELAY PRODUCT (BDP) SOCKET TUNER')
    print('====================================================')

    links = [
        NetworkLink('Local DC LAN', bandwidth_mbps=1000.0, rtt_ms=0.5),        # 1 Gbps, 0.5ms
        NetworkLink('Home Fiber Internet', bandwidth_mbps=300.0, rtt_ms=25.0), # 300 Mbps, 25ms
        NetworkLink('Transatlantic WAN', bandwidth_mbps=10000.0, rtt_ms=100.0),# 10 Gbps, 100ms
    ]

    for link in links:
        res = calculate_bdp_and_buffers(link)
        print(f'Link: {link.name} ({link.bandwidth_mbps:.0f} Mbps, {link.rtt_ms:.1f}ms RTT)')
        print(f'  BDP                 : {res["bdp_bytes"]:,} bytes ({res["bdp_mb"]:.2f} MB)')
        print(f'  Window Scale Needed : {res["needs_scaling"]} (Shift Factor = {res["window_scale_shift"]})')
        print(f'  Optimal tcp_rmem max: {res["tcp_rmem_max"]:,} bytes ({res["tcp_rmem_max"]/(1024*1024):.2f} MB)')
        print(f'  Recommended sysctl  :')
        print(f'    net.ipv4.tcp_rmem = 4096 87380 {res["tcp_rmem_max"]}')
        print(f'    net.ipv4.tcp_wmem = 4096 65536 {res["tcp_wmem_max"]}')
        print()

    # Verify Transatlantic 10G link requires substantial memory
    trans = calculate_bdp_and_buffers(links[2])
    assert trans['bdp_mb'] > 100.0, '10 Gbps @ 100ms RTT must have BDP > 100 MB'
    assert trans['window_scale_shift'] >= 11, 'High BDP link must require window scale shift >= 11'

    print('[VERIFIED] BDP calculations and kernel socket buffer formulas validated!')


if __name__ == '__main__':
    main()
