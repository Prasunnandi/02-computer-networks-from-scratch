#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sliding_window_sim.py - TCP Sliding Window & Flow Control Simulator
Calculates Usable Window, SND.UNA, SND.NXT and Bandwidth-Delay Product.
"""

def calculate_bdp_bytes(bandwidth_gbps: float, rtt_ms: float) -> dict:
    bandwidth_bps = bandwidth_gbps * 1e9
    rtt_sec = rtt_ms / 1000.0
    bdp_bytes = int((bandwidth_bps / 8.0) * rtt_sec)
    
    # 16-bit window limit without scaling: 65535 bytes
    max_16bit_win = 65535
    wscale_needed = 0
    while (max_16bit_win << wscale_needed) < bdp_bytes and wscale_needed < 14:
        wscale_needed += 1
        
    return {
        "bandwidth_gbps": bandwidth_gbps,
        "rtt_ms": rtt_ms,
        "bdp_bytes": bdp_bytes,
        "bdp_mb": round(bdp_bytes / (1024**2), 2),
        "window_scale_factor_needed": wscale_needed
    }

def update_sliding_window(snd_una: int, snd_nxt: int, rcv_wnd: int) -> dict:
    usable_window = rcv_wnd - (snd_nxt - snd_una)
    return {
        "snd_una": snd_una,
        "snd_nxt": snd_nxt,
        "rcv_wnd": rcv_wnd,
        "bytes_in_flight": snd_nxt - snd_una,
        "usable_window_bytes": max(0, usable_window)
    }

if __name__ == "__main__":
    bdp = calculate_bdp_bytes(bandwidth_gbps=10.0, rtt_ms=80.0)
    print("=== Bandwidth-Delay Product (BDP) Calculation ===")
    for k, v in bdp.items():
        print(f"  {k}: {v}")
        
    sw = update_sliding_window(snd_una=1000, snd_nxt=2500, rcv_wnd=4000)
    print("\n=== Sliding Window State ===")
    for k, v in sw.items():
        print(f"  {k}: {v}")
