# Day 01 Lab: Binary, Hexadecimal & Signal Foundations in Python

> **Welcome to Computer Networks!** At the physical layer, all networks (fiber optics, Wi-Fi, Ethernet copper cables) transmit only **bits (0s and 1s)**.
> In this lab, you will learn how computers convert decimal numbers into binary and hexadecimal completely from scratch without using Python's built-in shortcuts!

---

## 🎯 What Does This Lab Do?
1. **`binary_hex_converter.py`**: Implements the base-2 and base-16 conversion algorithms manually.
   - Converts `42` into binary `00101010` using repeated division by 2.
   - Converts `42` into hexadecimal `2A` using repeated division by 16.
2. **`binary_signal_sim.py`**: Calculates the mathematical maximum data speed of a physical channel using the **Shannon-Hartley Theorem**:
   $$C = B \cdot \log_2(1 + \text{SNR})$$

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python binary_hex_converter.py
```
Or run the extended signal simulation:
```bash
python binary_signal_sim.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Integer Division (`//`) vs Modulo Remainder (`%`)
* In Python:
  - `num % 2` gives the **remainder** (either `0` or `1`). This is our binary bit!
  - `num // 2` gives the **whole number quotient** (e.g. `9 // 2 = 4`), throwing away any decimal fraction.
* By looping while `num > 0`, we extract every single binary bit from right to left!

### 2. Building Strings from Lists: `"".join(...)`
* In Python, adding strings together in a loop like `s = s + char` is slow.
* Best practice: Append characters to a list `bits.append(remainder)`, reverse it with `reversed(bits)`, and glue them together with `"".join(...)`.

### 3. Padding with Zeros: `.zfill(8)`
* A byte always has 8 bits. If a number only has 5 bits (like `10101`), `.zfill(8)` adds leading zeros: `'00010101'`.

### 4. Logarithms: `math.log2(x)`
* `math.log2(8)` returns `3.0` because $2^3 = 8$.
* In networking, base-2 logarithms tell us how many bits of information can be packed into a signal wave!

---

## 🔍 Code Walkthrough

```python
HEX_CHARS = "0123456789ABCDEF"

def int_to_binary_manual(n):
    if n == 0:
        return "00000000"
    bits = []
    num = n
    # Divide by 2 repeatedly until quotient is 0
    while num > 0:
        bits.append(str(num % 2))
        num //= 2
    # Read remainders from bottom to top (reversed)
    return "".join(reversed(bits)).zfill(8)

def int_to_hex_manual(n):
    if n == 0:
        return "00"
    chars = []
    num = n
    # Divide by 16 repeatedly
    while num > 0:
        chars.append(HEX_CHARS[num % 16])
        num //= 16
    return "".join(reversed(chars)).zfill(2)
```

---

## 📋 Expected Terminal Output
```text
==================================================
  DAY 1 LAB: MANUAL BINARY & HEXADECIMAL CONVERTER
==================================================
Number:   0 -> Binary: 00000000 | Hex: 0x00
Number:   1 -> Binary: 00000001 | Hex: 0x01
Number:   2 -> Binary: 00000010 | Hex: 0x02
Number:  15 -> Binary: 00001111 | Hex: 0x0F
Number:  16 -> Binary: 00010000 | Hex: 0x10
Number:  42 -> Binary: 00101010 | Hex: 0x2A
Number: 255 -> Binary: 11111111 | Hex: 0xFF
==================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: What is decimal `100` in binary and hexadecimal? Run the script to find out!
2. **Challenge 2**: Why do network MAC addresses use Hexadecimal instead of Binary? (Answer: Hex is 4x more compact! One hex character represents 4 binary bits).
