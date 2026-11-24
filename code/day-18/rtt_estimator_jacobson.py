#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rtt_estimator_jacobson.py - Van Jacobson 1988 RTT & RTO Estimator (RFC 6298)
Implements EWMA Smoothed RTT, RTTVAR, and RTO calculation.
"""

class JacobsonRTTEstimator:
    def __init__(self, alpha: float = 0.125, beta: float = 0.25):
        self.alpha = alpha
        self.beta = beta
        self.srtt = None
        self.rttvar = None
        self.rto = 1.0 # Initial 1 sec RTO per RFC 6298

    def update(self, r_measured: float) -> dict:
        if self.srtt is None:
            # First measurement
            self.srtt = r_measured
            self.rttvar = r_measured / 2.0
        else:
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - r_measured)
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * r_measured
            
        # RTO = SRTT + 4 * RTTVAR, clamped to [0.2s, 120s]
        self.rto = max(0.2, min(120.0, self.srtt + 4 * self.rttvar))
        return {
            "measured_rtt_s": round(r_measured, 4),
            "srtt_s": round(self.srtt, 4),
            "rttvar_s": round(self.rttvar, 4),
            "rto_s": round(self.rto, 4)
        }

if __name__ == "__main__":
    estimator = JacobsonRTTEstimator()
    samples = [0.050, 0.055, 0.048, 0.150, 0.052] # 50ms average with a 150ms spike
    
    print("=== Van Jacobson RTT & RTO Estimation ===")
    for s in samples:
        res = estimator.update(s)
        print(f"Sample RTT: {res['measured_rtt_s']}s -> SRTT: {res['srtt_s']}s | RTTVAR: {res['rttvar_s']}s | RTO: {res['rto_s']}s")
