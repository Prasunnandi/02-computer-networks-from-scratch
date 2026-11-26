#!/usr/bin/env python3
"""
Day 32 Lab: DNS Binary Packet Codec & Name Compression Engine
Encodes and decodes the 12-byte binary DNS wire format header and implements
RFC 1035 Section 4.1.4 message compression (0xC0 pointer offsets).
Uses Python standard library only.
"""

import struct
from typing import Tuple, List, Dict


class DNSPacketCodec:
    """Encodes and decodes standard RFC 1035 DNS binary packets."""

    HEADER_FORMAT = "!HHHHHH"  # 12 bytes: ID, Flags, QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT

    @staticmethod
    def pack_header(
        pkt_id: int,
        qr: int = 0,
        opcode: int = 0,
        aa: int = 0,
        tc: int = 0,
        rd: int = 1,
        ra: int = 0,
        rcode: int = 0,
        qdcount: int = 1,
        ancount: int = 0,
        nscount: int = 0,
        arcount: int = 0
    ) -> bytes:
        """Packs DNS flags and 12-byte header into binary bytes."""
        flags = (
            ((qr & 1) << 15) |
            ((opcode & 0xF) << 11) |
            ((aa & 1) << 10) |
            ((tc & 1) << 9) |
            ((rd & 1) << 8) |
            ((ra & 1) << 7) |
            (rcode & 0xF)
        )
        return struct.pack(DNSPacketCodec.HEADER_FORMAT, pkt_id, flags, qdcount, ancount, nscount, arcount)

    @staticmethod
    def unpack_header(data: bytes) -> Dict[str, int]:
        """Unpacks 12-byte DNS header into component fields."""
        if len(data) < 12:
            raise ValueError("Data too short for DNS header (requires 12 bytes)")
        pkt_id, flags, qdcount, ancount, nscount, arcount = struct.unpack(
            DNSPacketCodec.HEADER_FORMAT, data[:12]
        )
        return {
            "id": pkt_id,
            "qr": (flags >> 15) & 1,
            "opcode": (flags >> 11) & 0xF,
            "aa": (flags >> 10) & 1,
            "tc": (flags >> 9) & 1,
            "rd": (flags >> 8) & 1,
            "ra": (flags >> 7) & 1,
            "rcode": flags & 0xF,
            "qdcount": qdcount,
            "ancount": ancount,
            "nscount": nscount,
            "arcount": arcount
        }

    @staticmethod
    def encode_qname(name: str) -> bytes:
        """Encodes domain name into standard DNS label format (e.g. 3www7example3com0)."""
        labels = name.strip('.').split('.')
        wire = bytearray()
        for label in labels:
            encoded_label = label.encode('ascii')
            wire.append(len(encoded_label))
            wire.extend(encoded_label)
        wire.append(0)  # Terminating null label
        return bytes(wire)

    @staticmethod
    def decode_name_with_compression(buffer: bytes, offset: int) -> Tuple[str, int]:
        """Decodes DNS name handling RFC 1035 0xC0 pointer offsets."""
        labels = []
        original_offset = offset
        jumped = False
        bytes_consumed = 0

        while True:
            if offset >= len(buffer):
                raise ValueError("Premature end of buffer while decoding name")
            length = buffer[offset]

            # Check if this is a compression pointer (top two bits set: 0xC0)
            if (length & 0xC0) == 0xC0:
                if offset + 1 >= len(buffer):
                    raise ValueError("Incomplete compression pointer")
                pointer_offset = ((length & 0x3F) << 8) | buffer[offset + 1]
                if not jumped:
                    bytes_consumed = (offset + 2) - original_offset
                    jumped = True
                offset = pointer_offset
                continue

            # Standard label
            offset += 1
            if length == 0:
                break
            label = buffer[offset:offset + length].decode('ascii')
            labels.append(label)
            offset += length

        if not jumped:
            bytes_consumed = offset - original_offset

        return ".".join(labels), bytes_consumed


def main():
    print("====================================================")
    print("DAY 32: DNS PACKET BINARY CODEC & COMPRESSION")
    print("====================================================")

    # Test 1: Header Pack & Unpack
    header = DNSPacketCodec.pack_header(
        pkt_id=0x1234, qr=0, rd=1, qdcount=1, ancount=0
    )
    assert len(header) == 12, "DNS header must be exactly 12 bytes"
    unpacked = DNSPacketCodec.unpack_header(header)
    assert unpacked["id"] == 0x1234
    assert unpacked["qr"] == 0
    assert unpacked["rd"] == 1
    assert unpacked["qdcount"] == 1
    print("  [PASS] 12-Byte Header packed & unpacked successfully.")

    # Test 2: Label encoding
    wire_name = DNSPacketCodec.encode_qname("www.example.com")
    expected_wire = b"\x03www\x07example\x03com\x00"
    assert wire_name == expected_wire
    print("  [PASS] Domain name label wire encoding matches RFC 1035.")

    # Test 3: Construct packet with RFC 1035 Compression Pointer
    # Layout:
    # Offset 12: Question name 'api.example.com' (17 bytes: 3api7example3com0)
    # Offset 29: Answer name pointing back to 'example.com' at Offset 16 (0xC0, 16)
    packet = bytearray(header)
    offset_qname = len(packet)  # 12
    packet.extend(DNSPacketCodec.encode_qname("api.example.com"))

    # Append question type (A=1) and class (IN=1)
    packet.extend(struct.pack("!HH", 1, 1))

    # Append answer section using compression pointer to "example.com"
    offset_ptr = len(packet)
    # Offset of "example.com" within qname is 12 + 1 (len byte) + 3 ('api') = 16
    pointer = 0xC000 | 16
    packet.extend(struct.pack("!H", pointer))

    decoded_full, _ = DNSPacketCodec.decode_name_with_compression(packet, offset_qname)
    assert decoded_full == "api.example.com"

    decoded_ptr, consumed = DNSPacketCodec.decode_name_with_compression(packet, offset_ptr)
    assert decoded_ptr == "example.com"
    assert consumed == 2, "Compression pointer consumes exactly 2 bytes in wire"
    print(f"  [PASS] Compressed Pointer (0x{pointer:04X}) decoded: '{decoded_ptr}' (consumed {consumed} bytes).")

    print("\n[VERIFIED] DNS Binary Packet Codec passed all tests with 100% fidelity!")


if __name__ == "__main__":
    main()
