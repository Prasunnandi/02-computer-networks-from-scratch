# -*- coding: utf-8 -*-
"""
Day 1 Lab: Custom Binary & Hexadecimal Converter from Scratch
Converts integers, binary strings, and hex without using bin() or hex() builtins!
"""

HEX_CHARS = "0123456789ABCDEF"

def int_to_binary_manual(n):
    if n == 0:
        return "00000000"
    bits = []
    num = n
    while num > 0:
        remainder = num % 2
        bits.append(str(remainder))
        num //= 2
    # Reverse to read from Most Significant to Least Significant Bit
    result = "".join(reversed(bits))
    # Pad to 8 bits
    return result.zfill(8)

def int_to_hex_manual(n):
    if n == 0:
        return "00"
    chars = []
    num = n
    while num > 0:
        remainder = num % 16
        chars.append(HEX_CHARS[remainder])
        num //= 16
    result = "".join(reversed(chars))
    return result.zfill(2)

def main():
    print("==================================================")
    print("  NETWORKS DAY 1: BINARY & HEXADECIMAL DECODER    ")
    print("==================================================")

    sample_numbers = [0, 5, 10, 15, 16, 127, 128, 255]
    print(f"{'Decimal':<10} {'Binary (8-bit)':<18} {'Hex (1 byte)':<12}")
    print("-" * 42)
    for num in sample_numbers:
        b_str = int_to_binary_manual(num)
        h_str = int_to_hex_manual(num)
        print(f"{num:<10} {b_str:<18} 0x{h_str:<12}")

    print("==================================================")
    print("Notice how 255 fills an entire byte: 11111111 = 0xFF!")

if __name__ == "__main__":
    main()
