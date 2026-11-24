#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nagle_delayed_ack_sim.py - Nagle's Algorithm & Delayed ACK Deadlock Simulator
Demonstrates the 40ms deadlock pathology between small writes and delayed ACKs.
"""

def simulate_nagle_delayed_ack(payload1_bytes: int, payload2_bytes: int,
                              tcp_nodelay: bool = False, mss: int = 1460) -> dict:
    unacked_in_flight = 0
    total_latency_ms = 0.0
    network_rtt_ms = 2.0
    delayed_ack_timeout_ms = 40.0
    
    # Send Packet 1
    unacked_in_flight += payload1_bytes
    total_latency_ms += network_rtt_ms / 2.0
    
    # Try sending Packet 2
    deadlock_occurred = False
    if not tcp_nodelay:
        # Nagle is active: if unacked data in flight and packet < MSS, buffer!
        if unacked_in_flight > 0 and payload2_bytes < mss:
            deadlock_occurred = True
            total_latency_ms += delayed_ack_timeout_ms # Must wait for delayed ACK!
    
    total_latency_ms += network_rtt_ms / 2.0
    
    return {
        "tcp_nodelay_enabled": tcp_nodelay,
        "deadlock_occurred": deadlock_occurred,
        "total_latency_ms": total_latency_ms
    }

if __name__ == "__main__":
    standard = simulate_nagle_delayed_ack(payload1_bytes=300, payload2_bytes=200, tcp_nodelay=False)
    optimized = simulate_nagle_delayed_ack(payload1_bytes=300, payload2_bytes=200, tcp_nodelay=True)
    
    print("=== Nagle vs TCP_NODELAY Deadlock Analysis ===")
    print(f"Standard (Nagle Enabled): Latency = {standard['total_latency_ms']} ms (Deadlock: {standard['deadlock_occurred']})")
    print(f"Optimized (TCP_NODELAY):   Latency = {optimized['total_latency_ms']} ms (Deadlock: {optimized['deadlock_occurred']})")
