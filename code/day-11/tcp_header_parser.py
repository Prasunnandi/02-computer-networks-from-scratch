#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tcp_header_parser.py - Binary RFC 793 TCP Header Parser & Generator
Encodes and decodes 20-byte TCP binary headers and extracts control flags.
"""
import struct

def build_tcp_header(src_port: int, dst_port: int, seq_num: int, ack_num: int,
                     flags: dict, window: int = 65535) -> bytes:
    # 4 bits data offset (5 = 20 bytes), 4 bits reserved (0)
    data_offset_res = (5 << 4) | 0
    
    # 8-bit flags: CWR | ECE | URG | ACK | PSH | RST | SYN | FIN
    flag_byte = 0
    if flags.get('CWR'): flag_byte |= (1 << 7)
    if flags.get('ECE'): flag_byte |= (1 << 6)
    if flags.get('URG'): flag_byte |= (1 << 5)
    if flags.get('ACK'): flag_byte |= (1 << 4)
    if flags.get('PSH'): flag_byte |= (1 << 3)
    if flags.get('RST'): flag_byte |= (1 << 2)
    if flags.get('SYN'): flag_byte |= (1 << 1)
    if flags.get('FIN'): flag_byte |= (1 << 0)
    
    checksum = 0
    urgent_ptr = 0
    
    return struct.pack("!HHIIBBHHH",
                       src_port, dst_port, seq_num, ack_num,
                       data_offset_res, flag_byte, window, checksum, urgent_ptr)

def parse_tcp_header(raw_bytes: bytes) -> dict:
    fields = struct.unpack("!HHIIBBHHH", raw_bytes[:20])
    src_port = fields[0]
    dst_port = fields[1]
    seq_num = fields[2]
    ack_num = fields[3]
    data_offset = (fields[4] >> 4) * 4
    flag_byte = fields[5]
    window = fields[6]
    
    flags = {
        "CWR": bool(flag_byte & (1 << 7)),
        "ECE": bool(flag_byte & (1 << 6)),
        "URG": bool(flag_byte & (1 << 5)),
        "ACK": bool(flag_byte & (1 << 4)),
        "PSH": bool(flag_byte & (1 << 3)),
        "RST": bool(flag_byte & (1 << 2)),
        "SYN": bool(flag_byte & (1 << 1)),
        "FIN": bool(flag_byte & (1 << 0)),
    }
    
    return {
        "src_port": src_port,
        "dst_port": dst_port,
        "seq_num": seq_num,
        "ack_num": ack_num,
        "header_length_bytes": data_offset,
        "window_size": window,
        "flags": flags
    }

if __name__ == "__main__":
    flags_in = {"SYN": True, "ACK": False}
    header_bytes = build_tcp_header(src_port=54321, dst_port=80, seq_num=1000000, ack_num=0, flags=flags_in)
    parsed = parse_tcp_header(header_bytes)
    
    print("=== Binary TCP Header (RFC 793) Parsing ===")
    print(f"Raw Header Bytes ({len(header_bytes)} bytes): {header_bytes.hex()}")
    for k, v in parsed.items():
        if k != "flags":
            print(f"  {k}: {v}")
    print("  flags:")
    for f, val in parsed["flags"].items():
        if val:
            print(f"    {f}: {val}")
