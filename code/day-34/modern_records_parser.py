#!/usr/bin/env python3
"""
Day 34 Lab: Modern DNS Records Parser & Service Discovery
Parses modern application-layer DNS Resource Records:
- SRV (RFC 2782): Priority, Weight, Port, and Target hostname
- CAA (RFC 8659): Certification Authority Authorization flags & tags
- HTTPS / SVCB (RFC 9460): Next-generation HTTP/3 ALPN, ECH & port bindings
Uses Python standard library only.
"""

import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any


@dataclass
class SRVRecord:
    priority: int
    weight: int
    port: int
    target: str


@dataclass
class CAARecord:
    flags: int
    tag: str
    value: str


@dataclass
class HTTPSRecord:
    priority: int
    target_name: str
    params: Dict[int, bytes]


class ModernDNSRecordsParser:
    """Parses modern DNS discovery and security records."""

    @staticmethod
    def parse_srv(rdata: bytes) -> SRVRecord:
        """Parses RFC 2782 SRV record: Priority(16), Weight(16), Port(16), Target."""
        if len(rdata) < 7:
            raise ValueError("SRV RDATA too short (min 7 bytes)")
        priority, weight, port = struct.unpack("!HHH", rdata[:6])
        # Decode target label sequence
        target = ModernDNSRecordsParser._decode_labels(rdata[6:])
        return SRVRecord(priority=priority, weight=weight, port=port, target=target)

    @staticmethod
    def parse_caa(rdata: bytes) -> CAARecord:
        """Parses RFC 8659 CAA record: Flags(8), Tag Length(8), Tag(ASCII), Value."""
        if len(rdata) < 2:
            raise ValueError("CAA RDATA too short")
        flags = rdata[0]
        tag_len = rdata[1]
        tag = rdata[2:2 + tag_len].decode('ascii')
        value = rdata[2 + tag_len:].decode('utf-8')
        return CAARecord(flags=flags, tag=tag, value=value)

    @staticmethod
    def parse_https_svcb(rdata: bytes) -> HTTPSRecord:
        """Parses RFC 9460 HTTPS/SVCB: SvcPriority(16), TargetName, SvcParams."""
        if len(rdata) < 2:
            raise ValueError("HTTPS RDATA too short")
        priority = struct.unpack("!H", rdata[:2])[0]
        offset = 2

        # Decode TargetName (or root dot '.' if empty/0)
        target_labels = []
        while offset < len(rdata):
            length = rdata[offset]
            offset += 1
            if length == 0:
                break
            target_labels.append(rdata[offset:offset + length].decode('ascii'))
            offset += length

        target_name = ".".join(target_labels) if target_labels else "."

        # Parse SvcParams: key(16), len(16), value
        params = {}
        while offset + 4 <= len(rdata):
            param_key, param_len = struct.unpack("!HH", rdata[offset:offset + 4])
            offset += 4
            param_val = rdata[offset:offset + param_len]
            offset += param_len
            params[param_key] = param_val

        return HTTPSRecord(priority=priority, target_name=target_name, params=params)

    @staticmethod
    def _decode_labels(data: bytes) -> str:
        labels = []
        idx = 0
        while idx < len(data):
            length = data[idx]
            idx += 1
            if length == 0:
                break
            labels.append(data[idx:idx + length].decode('ascii'))
            idx += length
        return ".".join(labels)


def main():
    print("====================================================")
    print("DAY 34: MODERN DNS RECORDS PARSER (SRV, CAA, HTTPS)")
    print("====================================================")

    # 1. Test SRV Record (Priority=10, Weight=60, Port=5060, Target=sipserver.example.com)
    srv_wire = struct.pack("!HHH", 10, 60, 5060) + b"\x09sipserver\x07example\x03com\x00"
    srv = ModernDNSRecordsParser.parse_srv(srv_wire)
    assert srv.priority == 10
    assert srv.weight == 60
    assert srv.port == 5060
    assert srv.target == "sipserver.example.com"
    print(f"  [PASS] SRV Record: Target={srv.target}:{srv.port} (Priority={srv.priority}, Weight={srv.weight})")

    # 2. Test CAA Record (Flags=0, Tag='issue', Value='letsencrypt.org')
    tag = b"issue"
    caa_wire = bytes([0, len(tag)]) + tag + b"letsencrypt.org"
    caa = ModernDNSRecordsParser.parse_caa(caa_wire)
    assert caa.flags == 0
    assert caa.tag == "issue"
    assert caa.value == "letsencrypt.org"
    print(f"  [PASS] CAA Record: Tag='{caa.tag}', Value='{caa.value}' (Flags={caa.flags})")

    # 3. Test HTTPS/SVCB Record (Priority=1, Target='.', ALPN=['h3', 'h2'], Port=443)
    # Param 1 = ALPN (key 1). Param 3 = Port (key 3).
    alpn_val = b"\x02h3\x02h2"
    port_val = struct.pack("!H", 443)
    https_wire = (
        struct.pack("!H", 1) +  # Priority 1
        b"\x00" +              # Target '.' (root label length 0)
        struct.pack("!HH", 1, len(alpn_val)) + alpn_val +  # Key 1 (ALPN)
        struct.pack("!HH", 3, len(port_val)) + port_val    # Key 3 (Port)
    )
    https_rec = ModernDNSRecordsParser.parse_https_svcb(https_wire)
    assert https_rec.priority == 1
    assert https_rec.target_name == "."
    assert 1 in https_rec.params
    assert 3 in https_rec.params
    extracted_port = struct.unpack("!H", https_rec.params[3])[0]
    assert extracted_port == 443
    print(f"  [PASS] HTTPS Record: Priority={https_rec.priority}, ALPN={https_rec.params[1]!r}, Port={extracted_port}")

    print("\n[VERIFIED] Modern DNS Records Parser passed all tests with 100% fidelity!")


if __name__ == "__main__":
    main()
