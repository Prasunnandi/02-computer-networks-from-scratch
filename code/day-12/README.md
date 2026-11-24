# Day 12 Lab: TCP 3-Way Handshake Simulator

## For Beginners to Python

Welcome to Day 12! In this lab, we simulate the classic TCP 3-Way Handshake step-by-step.

### Key Concepts
1. **Step 1 (SYN)**: Client says "I want to connect, my starting number is X".
2. **Step 2 (SYN-ACK)**: Server says "I acknowledge your X by asking for X+1, and my starting number is Y".
3. **Step 3 (ACK)**: Client says "I acknowledge your Y by asking for Y+1".
Both sides are now in the `ESTABLISHED` state!

### How to Run
```bash
python handshake_simulator.py
```
