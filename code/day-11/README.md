# Day 11 Lab: Binary TCP Header Parser (RFC 793)

## For Beginners to Python

Welcome to Day 11! In this lab, we build an encoder and decoder that creates real binary TCP packets using Python's `struct` module.

### Key Concepts
- `struct.pack("!HHIIBBHHH", ...)`: Converts Python integers into exact binary network bytes (Big-Endian format).
  - `H`: 16-bit unsigned short (Ports, Window)
  - `I`: 32-bit unsigned integer (Sequence & Acknowledgment numbers)
  - `B`: 8-bit unsigned char (Data Offset, Flags)

### How to Run
```bash
python tcp_header_parser.py
```
