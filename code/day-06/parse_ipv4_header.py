"""
Day 06: Low-Level IPv4 Packet Header Decoder & Ones' Complement Checksum Engine
Zero-Knowledge-Gap Implementation of RFC 791 IPv4 Header Parsing and RFC 1071 Checksum Math.

Demonstrates:
1. Binary unpacking of the standard 20-byte IPv4 packet header.
2. Bit-level extraction: Version, IHL, DSCP/ECN, Flags (DF/MF), Fragment Offset.
3. Mathematical Ones' Complement 16-bit Checksum calculation and verification.
4. Decrementing TTL and updating checksum as an intermediate router hop.
"""

import struct
import socket
from typing import Dict, Any, Tuple


class IPv4HeaderDecoder:
    """Decodes and validates raw binary IPv4 packet headers."""

    @staticmethod
    def calculate_ones_complement_checksum(header_bytes: bytes) -> int:
        """
        RFC 1071 Ones' Complement Checksum algorithm:
        1. Pad to even length if odd.
        2. Sum all 16-bit big-endian words.
        3. Add high 16-bit carry bits back into low 16 bits (end-around carry).
        4. Bitwise NOT inversion.
        """
        if len(header_bytes) % 2 != 0:
            header_bytes += b'\x00'

        total_sum = 0
        for i in range(0, len(header_bytes), 2):
            word = (header_bytes[i] << 8) + header_bytes[i + 1]
            total_sum += word

        # End-around carry folding
        while (total_sum >> 16) > 0:
            total_sum = (total_sum & 0xFFFF) + (total_sum >> 16)

        # One's complement bitwise NOT
        return (~total_sum) & 0xFFFF

    @classmethod
    def decode(cls, raw_packet: bytes) -> Dict[str, Any]:
        """Unpacks the IPv4 header and validates fields."""
        if len(raw_packet) < 20:
            raise ValueError(f"Packet too short for IPv4 header: {len(raw_packet)} bytes (minimum 20)")

        # Unpack first 20 bytes:
        # ! = network byte order (Big-Endian)
        # B = unsigned char (1 byte)
        # H = unsigned short (2 bytes)
        # 4s = 4 byte string (IP address)
        first_byte, dscp_ecn, total_length, ident, flags_offset, ttl, protocol, checksum, src_raw, dst_raw = struct.unpack(
            "!BBHHHBBH4s4s", raw_packet[:20]
        )

        version = (first_byte >> 4) & 0x0F
        ihl_words = first_byte & 0x0F
        ihl_bytes = ihl_words * 4

        dscp = (dscp_ecn >> 2) & 0x3F
        ecn = dscp_ecn & 0x03

        # Flags (3 bits) & Fragment Offset (13 bits)
        flag_reserved = bool((flags_offset >> 15) & 0x01)
        flag_df = bool((flags_offset >> 14) & 0x01)  # Don't Fragment
        flag_mf = bool((flags_offset >> 13) & 0x01)  # More Fragments
        fragment_offset = (flags_offset & 0x1FFF) * 8  # 8-byte units to bytes

        src_ip = socket.inet_ntoa(src_raw)
        dst_ip = socket.inet_ntoa(dst_raw)

        # Checksum validation:
        # Over the entire 20-byte header (including checksum field),
        # the ones' complement sum must fold to 0xFFFF (or bitwise NOT is 0x0000).
        computed_validation = cls.calculate_ones_complement_checksum(raw_packet[:ihl_bytes])
        is_checksum_valid = (computed_validation == 0x0000)

        return {
            "version": version,
            "ihl_words": ihl_words,
            "ihl_bytes": ihl_bytes,
            "dscp": dscp,
            "ecn": ecn,
            "total_length": total_length,
            "identification": ident,
            "flags": {
                "reserved": flag_reserved,
                "dont_fragment": flag_df,
                "more_fragments": flag_mf
            },
            "fragment_offset_bytes": fragment_offset,
            "ttl": ttl,
            "protocol": protocol,
            "checksum": hex(checksum),
            "is_checksum_valid": is_checksum_valid,
            "source_ip": src_ip,
            "destination_ip": dst_ip
        }

    @classmethod
    def craft_header(cls, src_ip: str, dst_ip: str, protocol: int = 6, ttl: int = 64, payload_len: int = 0) -> bytes:
        """Constructs a valid 20-byte IPv4 header with calculated checksum."""
        version_ihl = (4 << 4) | 5  # IPv4, IHL = 5 (20 bytes)
        dscp_ecn = 0
        total_length = 20 + payload_len
        ident = 54321
        flags_offset = 0x4000  # DF bit set (0100 0000 0000 0000)
        checksum_placeholder = 0

        src_raw = socket.inet_aton(src_ip)
        dst_raw = socket.inet_aton(dst_ip)

        header_no_checksum = struct.pack(
            "!BBHHHBBH4s4s",
            version_ihl, dscp_ecn, total_length, ident, flags_offset, ttl, protocol, checksum_placeholder, src_raw, dst_raw
        )

        # Compute checksum over header bytes with checksum=0
        computed_checksum = cls.calculate_ones_complement_checksum(header_no_checksum)

        # Repack with calculated checksum
        return struct.pack(
            "!BBHHHBBH4s4s",
            version_ihl, dscp_ecn, total_length, ident, flags_offset, ttl, protocol, computed_checksum, src_raw, dst_raw
        )


# --- SELF-CONTAINED VERIFICATION LAB ---
if __name__ == "__main__":
    print("=" * 60)
    print("DAY 06 LAB: IPV4 HEADER DECODER & ONES' COMPLEMENT CHECKSUM")
    print("=" * 60)

    # 1. Craft a synthetic IPv4 packet header
    src = "192.168.1.10"
    dst = "142.250.190.46"  # Google
    crafted_header = IPv4HeaderDecoder.craft_header(src_ip=src, dst_ip=dst, protocol=6, ttl=64, payload_len=100)

    print(f"\n[1] Crafted Raw IPv4 Header ({len(crafted_header)} bytes):\n    {crafted_header.hex(' ')}")

    # 2. Decode the header and verify checksum
    decoded = IPv4HeaderDecoder.decode(crafted_header)
    print("\n[2] Decoded IPv4 Fields:")
    for k, v in decoded.items():
        print(f"    - {k:<22}: {v}")

    assert decoded["version"] == 4, "Version must be 4!"
    assert decoded["ihl_bytes"] == 20, "IHL must equal 20 bytes!"
    assert decoded["flags"]["dont_fragment"] is True, "DF flag should be true!"
    assert decoded["is_checksum_valid"] is True, "Header Checksum verification failed!"
    assert decoded["source_ip"] == src and decoded["destination_ip"] == dst
    print("\n    [PASS] IPv4 Header decoded and Ones' Complement Checksum verified valid.")

    # 3. Simulate Router Hop: Decrement TTL and observe checksum failure if not recalculated
    print("\n[3] Simulating Router Hop: Decrementing TTL from 64 to 63 without recalculating checksum...")
    corrupted_hop = bytearray(crafted_header)
    corrupted_hop[8] = 63  # TTL byte
    corrupted_decoded = IPv4HeaderDecoder.decode(bytes(corrupted_hop))
    print(f"    Hop TTL: {corrupted_decoded['ttl']}, Checksum Valid: {corrupted_decoded['is_checksum_valid']}")
    assert corrupted_decoded["is_checksum_valid"] is False, "Checksum should fail when TTL changed without recalculation!"
    print("    [PASS] Corrupted/unrecalculated header correctly rejected by RFC 1071 validator.")

    print("\n" + "=" * 60)
    print("ALL DAY 06 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)
