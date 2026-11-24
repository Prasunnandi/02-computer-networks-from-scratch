# Hands-On Lab: Day 20 - TCP SACK Option Parser (`sack_parser.py`)

## 1. What Are We Building & Why Does It Matter?
When multiple packets are dropped in the same window, standard TCP cumulative ACKs cannot tell the sender which specific packets survived.
The **Selective Acknowledgment (SACK)** option (RFC 2018) solves this by appending up to 4 isolated ranges of received bytes ($[	ext{Left Edge}, 	ext{Right Edge})$) to the TCP header.

In this lab, we build `sack_parser.py` to binary encode and decode RFC 2018 SACK option blocks using `struct.pack` and `struct.unpack`.

---

## 2. Python Concepts for Beginners
1. **Tuples of Ranges (`(start, end)`)**:
   - We represent SACK blocks as tuples of two 32-bit integers: `(5000, 6000)`.
2. **Binary Packing in Loops**:
   - `struct.pack("!II", left, right)` packs two 32-bit integers (8 bytes total) per block.

---

## 3. Step-by-Step Code Walkthrough

```python
import struct

def build_sack_option(blocks: list) -> bytes:
    # Option Kind: 5 (SACK), Length = 2 + 8 * num_blocks
    opt_kind = 5
    opt_len = 2 + len(blocks) * 8
    header = struct.pack("!BB", opt_kind, opt_len)

    payload = bytearray(header)
    for left, right in blocks:
        payload.extend(struct.pack("!II", left, right))
    return bytes(payload)
```
- Serializes isolated data blocks into the standard RFC 2018 wire format.

---

## 4. How to Run the Script

```bash
cd code/day-20
python sack_parser.py
```

### Expected Output
```
Building SACK Option with 2 Blocks:
  Block 1: [5000 ... 6000) (1000 bytes)
  Block 2: [8000 ... 9500) (1500 bytes)
Raw SACK Binary (18 bytes):
  0512000013880000177000001f400000251c

Parsing SACK Binary:
  Option Kind  : 5 (SACK)
  Total Length : 18 bytes
  Decoded SACK Blocks:
    |-- Block 1: Left=5000, Right=6000 (Received)
    |-- Block 2: Left=8000, Right=9500 (Received)
Sender Action: Retransmit missing gap [6000 ... 8000) immediately!
```

---

## 5. Beginner Exercises to Try
1. Add a 3rd SACK block and verify that `opt_len` increases to 26 bytes.
2. Verify that trying to add more than 4 blocks raises an error (RFC maximum limit).
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

