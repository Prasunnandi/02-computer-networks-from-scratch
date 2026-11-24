# Day 18 Lab: Van Jacobson RTT & RTO Estimator

## For Beginners to Python

Welcome to Day 18! In this lab, we implement the exact mathematics of Van Jacobson's 1988 RTO calculation algorithm.

### Key Concepts
- `SRTT`: Smoothed Round Trip Time (moving average).
- `RTTVAR`: Variance/jitter in network latency.
- `RTO`: How long the sender waits before retransmitting a lost packet.

### How to Run
```bash
python rtt_estimator_jacobson.py
```
