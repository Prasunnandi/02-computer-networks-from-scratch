#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zero_window_probe_sim.py - Zero Window & Persist Timer Simulator
Simulates persist timer exponential backoff and Zero Window Probes (ZWP).
"""

def simulate_persist_timer(initial_timeout_sec: float = 1.0, max_probes: int = 5) -> list:
    log = []
    timeout = initial_timeout_sec
    max_timeout = 60.0
    
    for probe_num in range(1, max_probes + 1):
        log.append({
            "probe_number": probe_num,
            "timer_delay_sec": timeout,
            "action": "Sending 1-Byte Zero Window Probe",
            "simulated_reply": "ACK received, Window=0" if probe_num < max_probes else "ACK received, Window=65535 (OPENED!)"
        })
        timeout = min(max_timeout, timeout * 2.0)
        
    return log

if __name__ == "__main__":
    probes = simulate_persist_timer()
    print("=== Zero Window Persist Timer Simulation ===")
    for p in probes:
        print(f"  Probe #{p['probe_number']} (after {p['timer_delay_sec']}s): {p['action']} -> {p['simulated_reply']}")
