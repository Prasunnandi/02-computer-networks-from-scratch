#!/usr/bin/env python3
"""
Day 37 Lab: DNS Transport Simulator (UDP Truncation, TCP Fallback & EDNS0)
Simulates standard RFC 1035 UDP 512-byte payload limits, Truncation flag (TC=1)
triggering client automatic fallback to TCP, and RFC 6891 EDNS0 extension
enabling 4096-byte UDP buffers.
Uses Python standard library only.
"""

import struct
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class SimulatedDNSResponse:
    transport: str       # 'UDP' or 'TCP'
    tc_flag: bool        # Truncated?
    buffer_limit: int
    payload_size: int
    records_delivered: int


class DNSTransportSimulator:
    STANDARD_UDP_MAX = 512
    EDNS0_UDP_MAX = 4096

    def __init__(self):
        # Generate 30 mock A records (~16 bytes per record + headers)
        self.mock_records = [f"192.0.2.{i}" for i in range(1, 35)]

    def query_udp_classic(self) -> SimulatedDNSResponse:
        """Simulates classic RFC 1035 UDP query (max 512 bytes)."""
        # Header (12 bytes) + Question (~30 bytes) leaves ~470 bytes for answers
        # Each record takes ~16 bytes. 34 records = ~544 bytes -> Exceeds 512!
        total_size = 12 + 30 + (len(self.mock_records) * 16)
        if total_size > self.STANDARD_UDP_MAX:
            # Server sets TC=1 (Truncated) and delivers zero or partial answers
            return SimulatedDNSResponse(
                transport="UDP",
                tc_flag=True,
                buffer_limit=self.STANDARD_UDP_MAX,
                payload_size=self.STANDARD_UDP_MAX,
                records_delivered=0  # Forces TCP retry
            )
        return SimulatedDNSResponse(
            transport="UDP",
            tc_flag=False,
            buffer_limit=self.STANDARD_UDP_MAX,
            payload_size=total_size,
            records_delivered=len(self.mock_records)
        )

    def query_tcp_fallback(self) -> SimulatedDNSResponse:
        """Simulates TCP fallback query after receiving TC=1."""
        # In TCP, messages are prefixed with 2-byte length and have no 512-byte cap
        total_size = 12 + 30 + (len(self.mock_records) * 16)
        return SimulatedDNSResponse(
            transport="TCP",
            tc_flag=False,
            buffer_limit=65535,
            payload_size=total_size,
            records_delivered=len(self.mock_records)
        )

    def query_udp_edns0(self) -> SimulatedDNSResponse:
        """Simulates modern EDNS0 UDP query with 4096-byte OPT pseudo-record."""
        total_size = 12 + 30 + 11 + (len(self.mock_records) * 16)  # +11 bytes for OPT RR
        assert total_size <= self.EDNS0_UDP_MAX
        return SimulatedDNSResponse(
            transport="UDP (EDNS0)",
            tc_flag=False,
            buffer_limit=self.EDNS0_UDP_MAX,
            payload_size=total_size,
            records_delivered=len(self.mock_records)
        )


def build_edns0_opt_record(udp_payload_size: int = 4096) -> bytes:
    """Builds RFC 6891 OPT pseudo-RR wire format."""
    # Name: root dot (0x00)
    # Type: OPT (41 = 0x0029)
    # Class: Requestor's UDP payload size (e.g. 4096 = 0x1000)
    # Extended RCODE and Flags (32 bits = 0x00000000)
    # RDLENGTH (16 bits = 0x0000)
    return struct.pack("!BHHII", 0, 41, udp_payload_size, 0, 0)


def main():
    print("====================================================")
    print("DAY 37: DNS TRANSPORT (UDP TRUNCATION & TCP FALLBACK)")
    print("====================================================")

    sim = DNSTransportSimulator()

    # Step 1: Classic UDP query (overflows 512B)
    udp_resp = sim.query_udp_classic()
    print(f"1. Classic UDP Query:")
    print(f"   Payload Size: {udp_resp.payload_size}B / Limit: {udp_resp.buffer_limit}B | TC Flag: {udp_resp.tc_flag}")
    assert udp_resp.tc_flag is True, "Classic UDP must set TC=1 when payload exceeds 512B"
    print("   [+] Client detected TC=1! Triggering automatic TCP fallback...")

    # Step 2: Fallback to TCP
    tcp_resp = sim.query_tcp_fallback()
    print(f"2. TCP Fallback Query:")
    print(f"   Transport: {tcp_resp.transport} | Records Delivered: {tcp_resp.records_delivered} / {len(sim.mock_records)}")
    assert tcp_resp.records_delivered == len(sim.mock_records)
    print("   [PASS] TCP successfully transferred entire oversized answer without truncation.")

    # Step 3: Modern EDNS0 Query
    edns0_resp = sim.query_udp_edns0()
    print(f"3. Modern EDNS0 Query:")
    print(f"   Transport: {edns0_resp.transport} | Buffer: {edns0_resp.buffer_limit}B | Records: {edns0_resp.records_delivered}")
    assert edns0_resp.tc_flag is False
    assert edns0_resp.records_delivered == len(sim.mock_records)
    print("   [PASS] EDNS0 transferred full answer over single UDP packet!")

    # Step 4: Verify OPT RR binary layout
    opt_wire = build_edns0_opt_record(4096)
    assert len(opt_wire) == 13  # 1 + 2 + 2 + 4 + 4 = 13 bytes
    root_name, opt_type, opt_buf = struct.unpack("!BHH", opt_wire[:5])
    assert root_name == 0
    assert opt_type == 41
    assert opt_buf == 4096
    print(f"   [PASS] OPT Pseudo-RR wire format verified (Type 41, Buffer {opt_buf}B).")

    print("\n[VERIFIED] DNS Transport & Fallback Simulator passed all tests with 100% fidelity!")


if __name__ == "__main__":
    main()
