#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sack_parser.py - TCP Selective Acknowledgment (SACK - RFC 2018) Parser
Encodes and decodes SACK option blocks (Left Edge, Right Edge).
"""
import struct

def build_sack_option(blocks: list) -> bytes:
    # Option Kind: 5 (SACK), Length = 2 + 8 * num_blocks
    assert len(blocks) <= 4, "Maximum 4 SACK blocks permitted in TCP Options!"
    length = 2 + len(blocks) * 8
    payload = bytearray([5, length])
    for left_edge, right_edge in blocks:
        payload.extend(struct.pack("!II", left_edge, right_edge))
    return bytes(payload)

def parse_sack_option(raw_bytes: bytes) -> list:
    kind = raw_bytes[0]
    length = raw_bytes[1]
    assert kind == 5, f"Expected SACK option kind 5, got {kind}"
    
    num_blocks = (length - 2) // 8
    blocks = []
    offset = 2
    for _ in range(num_blocks):
        left, right = struct.unpack("!II", raw_bytes[offset:offset+8])
        blocks.append((left, right))
        offset += 8
    return blocks

if __name__ == "__main__":
    # Receiver successfully received [2000-3000] and [4000-5000], missing [1000-2000] and [3000-4000]
    original_blocks = [(2000, 3000), (4000, 5000)]
    encoded = build_sack_option(original_blocks)
    decoded = parse_sack_option(encoded)
    
    print("=== TCP SACK (RFC 2018) Option Parsing ===")
    print(f"Encoded Binary SACK Option ({len(encoded)} bytes): {encoded.hex()}")
    print("Decoded Non-Contiguous Received Blocks:")
    for left, right in decoded:
        print(f"  Received: bytes [{left} to {right}]")
