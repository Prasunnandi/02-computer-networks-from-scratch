"""
Day 08: Custom ICMP Engine & Programmatic Traceroute Simulator
Zero-Knowledge-Gap Implementation of RFC 792 ICMP & TTL Expiration Route Tracing.

Demonstrates:
1. Binary encoding & decoding of ICMP Echo Request / Reply and Time Exceeded headers.
2. Calculation and validation of the 16-bit ICMP checksum.
3. Complete simulation of the Traceroute algorithm (TTL probing from 1 to N).
4. Realistic handling of hop latencies, TTL expiry (ICMP Type 11), and target completion.
"""

import struct
import time
from typing import Dict, Any, List, Optional, Tuple


class ICMPPacket:
    """Represents an RFC 792 ICMP packet."""
    TYPE_ECHO_REPLY = 0
    TYPE_DEST_UNREACHABLE = 3
    TYPE_ECHO_REQUEST = 8
    TYPE_TIME_EXCEEDED = 11

    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """RFC 1071 Ones' Complement Checksum."""
        if len(data) % 2 != 0:
            data += b'\x00'

        total = 0
        for i in range(0, len(data), 2):
            total += (data[i] << 8) + data[i + 1]

        while (total >> 16) > 0:
            total = (total & 0xFFFF) + (total >> 16)

        return (~total) & 0xFFFF

    @classmethod
    def encode(cls, icmp_type: int, icmp_code: int, ident: int, seq: int, payload: bytes = b"") -> bytes:
        """Packs an 8-byte ICMP header + payload with calculated checksum."""
        checksum_placeholder = 0
        header_no_checksum = struct.pack("!BBHHH", icmp_type, icmp_code, checksum_placeholder, ident, seq) + payload
        chk = cls.calculate_checksum(header_no_checksum)
        return struct.pack("!BBHHH", icmp_type, icmp_code, chk, ident, seq) + payload

    @classmethod
    def decode(cls, raw_bytes: bytes) -> Dict[str, Any]:
        """Decodes an ICMP packet and verifies checksum."""
        if len(raw_bytes) < 8:
            raise ValueError(f"Packet too short for ICMP: {len(raw_bytes)} bytes")

        icmp_type, icmp_code, checksum, ident, seq = struct.unpack("!BBHHH", raw_bytes[:8])
        payload = raw_bytes[8:]

        # Checksum validation:
        # Summing over the entire packet including checksum should yield 0xFFFF (or NOT is 0x0000)
        validation = cls.calculate_checksum(raw_bytes)
        is_valid = (validation == 0x0000)

        return {
            "type": icmp_type,
            "code": icmp_code,
            "checksum": hex(checksum),
            "is_valid": is_valid,
            "ident": ident,
            "seq": seq,
            "payload": payload
        }


class SimulatedNetworkRouter:
    """Represents an intermediate router or destination node in a network path."""
    def __init__(self, ip: str, hostname: str, hop_delay_ms: float, drops_icmp: bool = False):
        self.ip = ip
        self.hostname = hostname
        self.hop_delay_ms = hop_delay_ms
        self.drops_icmp = drops_icmp


class TracerouteSimulator:
    """Simulates end-to-end hop discovery via TTL decrementation."""
    def __init__(self, target_ip: str, route_path: List[SimulatedNetworkRouter]):
        self.target_ip = target_ip
        self.route_path = route_path  # List of hops from first router to target

    def trace(self, max_hops: int = 30) -> List[Dict[str, Any]]:
        results = []

        for ttl in range(1, max_hops + 1):
            hop_index = ttl - 1
            if hop_index >= len(self.route_path):
                # Beyond network topology
                break

            target_node = self.route_path[hop_index]
            accumulated_rtt = sum(n.hop_delay_ms for n in self.route_path[:hop_index + 1]) * 2

            if target_node.drops_icmp:
                # Firewall drop -> timeout
                results.append({
                    "hop": ttl,
                    "ip": "*",
                    "hostname": "*",
                    "rtt_ms": None,
                    "status": "TIMEOUT (* * *)"
                })
                continue

            is_final_destination = (hop_index == len(self.route_path) - 1)

            if is_final_destination:
                # Target host receives packet with TTL >= 1, replies with Echo Reply (Type 0)
                reply = ICMPPacket.encode(ICMPPacket.TYPE_ECHO_REPLY, 0, ident=1234, seq=ttl)
                status = "REACHED_TARGET (Echo Reply)"
            else:
                # Intermediate router decrements TTL to 0, replies with Time Exceeded (Type 11)
                reply = ICMPPacket.encode(ICMPPacket.TYPE_TIME_EXCEEDED, 0, ident=1234, seq=ttl)
                status = "TTL_EXPIRED (ICMP Time Exceeded)"

            decoded_reply = ICMPPacket.decode(reply)

            results.append({
                "hop": ttl,
                "ip": target_node.ip,
                "hostname": target_node.hostname,
                "rtt_ms": round(accumulated_rtt, 2),
                "icmp_type": decoded_reply["type"],
                "status": status
            })

            if is_final_destination:
                break

        return results


# --- SELF-CONTAINED VERIFICATION LAB ---
if __name__ == "__main__":
    print("=" * 60)
    print("DAY 08 LAB: ICMP PROTOCOL ENCODER & TRACEROUTE SIMULATOR")
    print("=" * 60)

    # 1. Test ICMP Encoding & Checksum Validation
    print("\n[1] Encoding ICMP Echo Request (Type 8)...")
    payload_data = b"Hello Network Lab Timestamp"
    raw_echo = ICMPPacket.encode(icmp_type=8, icmp_code=0, ident=42, seq=1, payload=payload_data)
    print(f"    Raw Encoded ICMP Packet ({len(raw_echo)} bytes): {raw_echo.hex(' ')}")

    decoded = ICMPPacket.decode(raw_echo)
    print(f"    Decoded: Type={decoded['type']}, Code={decoded['code']}, ValidChecksum={decoded['is_valid']}")
    assert decoded["type"] == 8 and decoded["code"] == 0, "Type/Code mismatch!"
    assert decoded["is_valid"] is True, "ICMP Checksum failed validation!"
    assert decoded["payload"] == payload_data, "Payload mismatch!"
    print("    [PASS] ICMP Echo Request packed and validated successfully.")

    # 2. Configure a multi-hop simulated route across the Internet
    simulated_topology = [
        SimulatedNetworkRouter("192.168.1.1", "home-gateway.local", hop_delay_ms=0.8),
        SimulatedNetworkRouter("10.240.0.1", "isp-edge-node.net", hop_delay_ms=2.1),
        SimulatedNetworkRouter("198.51.100.42", "transit-backbone.tier1.com", hop_delay_ms=6.5),
        SimulatedNetworkRouter("203.0.113.1", "firewalled-core.internal", hop_delay_ms=5.0, drops_icmp=True),
        SimulatedNetworkRouter("142.250.190.46", "dns.google", hop_delay_ms=4.2)
    ]

    print("\n[2] Executing Simulated Traceroute to 142.250.190.46 (dns.google)...")
    tracer = TracerouteSimulator("142.250.190.46", simulated_topology)
    trace_output = tracer.trace()

    print(f"\n{'HOP':<4} {'IP ADDRESS':<18} {'HOSTNAME':<30} {'RTT':<10} {'STATUS'}")
    print("-" * 80)
    for row in trace_output:
        rtt_str = f"{row['rtt_ms']} ms" if row['rtt_ms'] is not None else "* * *"
        print(f"{row['hop']:<4} {row['ip']:<18} {row['hostname']:<30} {rtt_str:<10} {row['status']}")

    assert len(trace_output) == 5, f"Expected 5 hops, got {len(trace_output)}"
    assert trace_output[0]["icmp_type"] == 11, "Hop 1 must be ICMP Type 11 (Time Exceeded)!"
    assert trace_output[3]["status"] == "TIMEOUT (* * *)", "Hop 4 must timeout due to firewall drop!"
    assert trace_output[4]["icmp_type"] == 0, "Final hop must be ICMP Type 0 (Echo Reply)!"
    print("\n    [PASS] Traceroute successfully discovered topology, simulated firewall drop, and terminated at destination.")

    print("\n" + "=" * 60)
    print("ALL DAY 08 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)
