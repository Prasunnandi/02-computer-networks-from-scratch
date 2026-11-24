# Day 17 Lab: Nagle vs TCP_NODELAY Deadlock Simulator

## For Beginners to Python

Welcome to Day 17! In this lab, we simulate the famous 40ms latency deadlock caused by Nagle's algorithm and delayed ACKs.

### Key Concepts
- `Nagle`: Buffers small packets if unacknowledged data is outstanding.
- `Delayed ACK`: Waits up to 40ms before sending an ACK.
- `TCP_NODELAY`: Disables Nagle, delivering sub-millisecond response times for microservices and databases!

### How to Run
```bash
python nagle_delayed_ack_sim.py
```
