#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fast_retransmit_sim.py - Fast Retransmit (3 Duplicate ACKs) Simulator
Simulates packet drop, out-of-order duplicate ACK generation, and immediate retransmission.
"""

def simulate_fast_retransmit(dropped_packet_id: int = 2, total_packets: int = 5) -> dict:
    log = []
    received_acks = []
    retransmit_triggered = False
    
    expected_ack = 1
    # Send packets
    for p_id in range(1, total_packets + 1):
        if p_id == dropped_packet_id:
            log.append(f"[WIRE DROP] Packet #{p_id} lost in transit!")
            continue
        # Receiver gets packet
        if p_id > dropped_packet_id:
            # Out of order packet arrives! Send duplicate ACK for dropped packet
            received_acks.append(dropped_packet_id)
            log.append(f"[OUT-OF-ORDER] Packet #{p_id} arrived -> Receiver generates DUP ACK for Packet #{dropped_packet_id}")
        else:
            received_acks.append(p_id + 1)
            
    # Check duplicate ACK count
    dup_count = received_acks.count(dropped_packet_id)
    if dup_count >= 3:
        retransmit_triggered = True
        log.append(f"[FAST RETRANSMIT] 3 Duplicate ACKs detected! Immediately re-sending Packet #{dropped_packet_id} without waiting for RTO timer!")
        
    return {
        "dropped_packet": dropped_packet_id,
        "duplicate_ack_count": dup_count,
        "fast_retransmit_triggered": retransmit_triggered,
        "event_log": log
    }

if __name__ == "__main__":
    res = simulate_fast_retransmit(dropped_packet_id=2, total_packets=5)
    print("=== TCP Fast Retransmit Simulation ===")
    for ev in res["event_log"]:
        print(f"  {ev}")
    print(f"\nResult: Fast Retransmit Triggered = {res['fast_retransmit_triggered']}")
