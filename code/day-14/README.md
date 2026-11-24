# Day 14 Lab: TCP Reset (RST) Analyzer

## For Beginners to Python

Welcome to Day 14! In this lab, we examine why and when computers send `RST` (Reset) packets.

### Key Concepts
A `RST` packet is TCP's emergency abort:
1. When you connect to a closed port, the server sends `RST` (`Connection Refused`).
2. When a program closes a socket while unread data is still buffered, the kernel sends `RST` to prevent silent data loss.

### How to Run
```bash
python tcp_rst_analyzer.py
```
