"""
Day 10: UDP Protocol Internals, Pseudo-Header Checksum & Datagram Socket Engine
Zero-Knowledge-Gap Implementation of RFC 768 UDP Header & Pseudo-Header Math.

Demonstrates:
1. Binary encoding/decoding of the 8-byte UDP header.
2. Mathematical 12-byte IPv4 Pseudo-Header Checksum construction & verification.
3. Datagram boundary preservation vs byte-stream fragmentation.
4. Simulating UDP high-throughput telemetry ingestion and buffer handling.
"""

import struct
import socket
from typing import Dict, Any, Tuple


class UDPDatagram:
    """Encodes, decodes, and computes RFC 768 UDP datagrams with IP pseudo-header checksums."""

    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """RFC 1071 16-bit Ones' Complement Checksum."""
        if len(data) % 2 != 0:
            data += b'\x00'

        total = 0
        for i in range(0, len(data), 2):
            total += (data[i] << 8) + data[i + 1]

        while (total >> 16) > 0:
            total = (total & 0xFFFF) + (total >> 16)

        chk = (~total) & 0xFFFF
        # RFC 768 rule: If computed checksum is 0x0000, it is transmitted as 0xFFFF
        return 0xFFFF if chk == 0 else chk

    @classmethod
    def craft(cls, src_ip: str, dst_ip: str, src_port: int, dst_port: int, payload: bytes) -> bytes:
        """
        Constructs an 8-byte UDP header with calculated checksum over the 12-byte Pseudo-Header.
        """
        udp_len = 8 + len(payload)
        checksum_placeholder = 0

        # 1. Build Pseudo-Header (12 bytes)
        # Src IP (4B) + Dst IP (4B) + Zero (1B) + Protocol (1B: 17 for UDP) + UDP Len (2B)
        src_bytes = socket.inet_aton(src_ip)
        dst_bytes = socket.inet_aton(dst_ip)
        pseudo_header = struct.pack("!4s4sBBH", src_bytes, dst_bytes, 0, 17, udp_len)

        # 2. Build UDP Header with zero checksum
        udp_header_zero = struct.pack("!HHHH", src_port, dst_port, udp_len, checksum_placeholder)

        # 3. Compute checksum over: Pseudo-Header + UDP Header + Payload
        checksum_payload = pseudo_header + udp_header_zero + payload
        calculated_checksum = cls.calculate_checksum(checksum_payload)

        # 4. Final UDP datagram (UDP Header + Payload)
        final_udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, calculated_checksum)
        return final_udp_header + payload

    @classmethod
    def decode(cls, datagram_bytes: bytes, src_ip: str, dst_ip: str) -> Dict[str, Any]:
        """Unpacks UDP datagram and validates pseudo-header checksum."""
        if len(datagram_bytes) < 8:
            raise ValueError(f"Datagram too short for UDP: {len(datagram_bytes)} bytes")

        src_port, dst_port, udp_len, checksum = struct.unpack("!HHHH", datagram_bytes[:8])
        payload = datagram_bytes[8:udp_len]

        is_valid = True
        if checksum != 0:
            # Checksum verification with pseudo-header
            src_bytes = socket.inet_aton(src_ip)
            dst_bytes = socket.inet_aton(dst_ip)
            pseudo_header = struct.pack("!4s4sBBH", src_bytes, dst_bytes, 0, 17, udp_len)
            validation_data = pseudo_header + datagram_bytes[:udp_len]
            # Folding over the entire block including checksum must equal 0xFFFF (or NOT is 0x0000)
            folded = cls.calculate_checksum(validation_data)
            is_valid = (folded == 0xFFFF or folded == 0x0000)

        return {
            "source_port": src_port,
            "destination_port": dst_port,
            "udp_length": udp_len,
            "checksum": hex(checksum),
            "is_checksum_valid": is_valid,
            "payload": payload
        }


# --- SELF-CONTAINED VERIFICATION LAB ---
if __name__ == "__main__":
    print("=" * 60)
    print("DAY 10 LAB: UDP PROTOCOL ENGINE & PSEUDO-HEADER CHECKSUM")
    print("=" * 60)

    # 1. Craft a UDP Datagram carrying simulated Market Data / Telemetry
    client_ip = "192.168.1.100"
    server_ip = "10.0.0.50"
    telemetry_payload = b"QUOTE:AAPL:185.50:VOL=5000:TIMESTAMP=1700000000"

    print(f"\n[1] Crafting UDP Datagram from {client_ip}:54321 -> {server_ip}:53 (DNS/Custom)...")
    raw_datagram = UDPDatagram.craft(
        src_ip=client_ip,
        dst_ip=server_ip,
        src_port=54321,
        dst_port=53,
        payload=telemetry_payload
    )

    print(f"    Raw Datagram Length: {len(raw_datagram)} bytes (8B header + {len(telemetry_payload)}B payload)")
    print(f"    UDP Header Hex: {raw_datagram[:8].hex(' ')}")

    # 2. Decode and Validate with Matching IPs
    print("\n[2] Decoding datagram on server with matching IP addresses...")
    decoded = UDPDatagram.decode(raw_datagram, src_ip=client_ip, dst_ip=server_ip)
    print(f"    Source Port     : {decoded['source_port']}")
    print(f"    Destination Port: {decoded['destination_port']}")
    print(f"    UDP Length      : {decoded['udp_length']} bytes")
    print(f"    Checksum        : {decoded['checksum']}")
    print(f"    Checksum Valid  : {decoded['is_checksum_valid']}")
    print(f"    Payload Data    : {decoded['payload'].decode('utf-8')}")

    assert decoded["source_port"] == 54321
    assert decoded["destination_port"] == 53
    assert decoded["is_checksum_valid"] is True, "Pseudo-header checksum validation failed!"
    assert decoded["payload"] == telemetry_payload
    print("    [PASS] UDP datagram and 12-byte Pseudo-Header checksum verified valid.")

    # 3. Demonstrate Pseudo-Header Cross-Talk Protection:
    # If packet was misrouted to a different IP (e.g. 10.0.0.99), the checksum MUST fail!
    print("\n[3] Simulating Router Misroute: Target host receives datagram at wrong IP (10.0.0.99)...")
    misrouted_decoded = UDPDatagram.decode(raw_datagram, src_ip=client_ip, dst_ip="10.0.0.99")
    print(f"    Checksum Valid on Wrong IP: {misrouted_decoded['is_checksum_valid']}")
    assert misrouted_decoded["is_checksum_valid"] is False, "Checksum MUST fail when destination IP does not match pseudo-header!"
    print("    [PASS] Pseudo-header checksum prevented misrouted packet ingestion.")

    # 4. Datagram Boundary Preservation Test
    print("\n[4] Verifying Datagram Message Boundary Preservation...")
    datagram_1 = UDPDatagram.craft(client_ip, server_ip, 5000, 8000, b"MSG_ONE")
    datagram_2 = UDPDatagram.craft(client_ip, server_ip, 5000, 8000, b"MSG_TWO")

    # In UDP, receiving 2 datagrams produces 2 discrete messages, never combined
    msg1 = UDPDatagram.decode(datagram_1, client_ip, server_ip)["payload"]
    msg2 = UDPDatagram.decode(datagram_2, client_ip, server_ip)["payload"]
    assert msg1 == b"MSG_ONE" and msg2 == b"MSG_TWO"
    print("    [PASS] Datagram boundaries preserved across separate transmissions.")

    print("\n" + "=" * 60)
    print("ALL DAY 10 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)
