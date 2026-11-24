# Day 13 Lab: TCP 4-Way Teardown Simulator

## For Beginners to Python

Welcome to Day 13! In this lab, we simulate how a TCP connection safely closes down without losing data.

### Key Concepts
- `CLOSE_WAIT`: The server knows the client is done sending, but the server might still have pending files to finish transmitting.
- `TIME_WAIT`: The active closer waits for $2 \times MSL$ (60 seconds) to ensure delayed packets expire.

### How to Run
```bash
python tcp_state_machine_sim.py
```
