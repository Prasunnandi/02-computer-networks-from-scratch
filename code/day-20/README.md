# Day 19-20 Lab: TCP SACK (RFC 2018) Option Parser

## For Beginners to Python

Welcome to Day 20! In this lab, we build an encoder and parser for Selective Acknowledgment (SACK) blocks.

### Key Concepts
SACK lets the receiver tell the sender: "I am missing bytes 1000-2000, but I already received bytes 2000-3000 and 4000-5000." This prevents the sender from needlessly re-sending bytes that were already received!

### How to Run
```bash
python sack_parser.py
```
