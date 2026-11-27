"""
Day 47: LLMNR & NetBIOS Name Resolution Simulator & Security Auditor
100% pure Python standard library implementation of RFC 1001/1002 NetBIOS first-level
encoding, RFC 4795 LLMNR multicast resolution, and rogue poison responder detection.
"""

from dataclasses import dataclass
import struct
from typing import Dict, List, Optional, Tuple


class NetBIOSCodec:
    """Encodes and decodes 16-character NetBIOS names using RFC 1001/1002 half-byte encoding."""

    @classmethod
    def encode_name(cls, name: str, scope: str = "", service_type: int = 0x20) -> bytes:
        """
        Pad name to 15 uppercase characters, append 1-byte service type (e.g. 0x20 for File Server),
        and encode each byte as two uppercase ASCII characters offset by 0x41 ('A').
        """
        padded = name.upper()[:15].ljust(15, " ")
        raw_16 = padded.encode("ascii") + bytes([service_type])

        encoded = bytearray()
        for b in raw_16:
            high_nibble = (b >> 4) & 0x0F
            low_nibble = b & 0x0F
            encoded.append(high_nibble + 0x41)
            encoded.append(low_nibble + 0x41)

        result = bytearray([len(encoded)]) + encoded
        if scope:
            for part in scope.split("."):
                result.append(len(part))
                result.extend(part.encode("ascii"))
        result.append(0)  # Null terminator
        return bytes(result)

    @classmethod
    def decode_name(cls, data: bytes) -> Tuple[str, int]:
        """Decodes a 32-byte half-byte encoded NetBIOS name."""
        length = data[0]
        if length != 32:
            raise ValueError(f"Expected NetBIOS name length 32, got {length}")

        encoded = data[1:33]
        decoded = bytearray()
        for i in range(0, 32, 2):
            high_nibble = encoded[i] - 0x41
            low_nibble = encoded[i + 1] - 0x41
            byte_val = (high_nibble << 4) | low_nibble
            decoded.append(byte_val)

        name_str = decoded[:15].decode("ascii").rstrip(" ")
        service_type = decoded[15]
        return name_str, service_type


class LLMNRSimulator:
    """Simulates RFC 4795 LLMNR query and poisoning attack detection."""

    MULTICAST_IPV4 = "224.0.0.252"
    PORT = 5355

    def __init__(self, legitimate_hosts: Dict[str, str]):
        self.legitimate_hosts = legitimate_hosts  # hostname -> ip

    def resolve(self, query_name: str, simulated_rogue_ip: Optional[str] = None) -> Tuple[Optional[str], bool]:
        """
        Attempts to resolve name.
        If a rogue attacker responds faster than genuine host, flags poisoning attack.
        Returns (resolved_ip, was_poisoned).
        """
        if simulated_rogue_ip:
            # Rogue attacker responded first via multicast injection
            return simulated_rogue_ip, True

        ip = self.legitimate_hosts.get(query_name)
        return ip, False


def main():
    print("=== Day 47: LLMNR & NetBIOS Name Resolution Simulator ===")

    # Test 1: NetBIOS RFC 1001/1002 Half-byte encoding
    raw_encoded = NetBIOSCodec.encode_name("FILESERVER", service_type=0x20)
    assert len(raw_encoded) == 34  # 1 byte len + 32 bytes encoded + 1 byte null
    name, svc = NetBIOSCodec.decode_name(raw_encoded)
    assert name == "FILESERVER"
    assert svc == 0x20
    print(f"[*] Test 1 Passed: NetBIOS Name '{name}' (Service 0x{svc:02X}) encoded to {len(raw_encoded)} bytes and decoded perfectly")

    # Test 2: LLMNR Resolution without attacker
    sim = LLMNRSimulator(legitimate_hosts={"win-dc-01": "10.0.0.1", "db-prod": "10.0.0.2"})
    resolved_ip, poisoned = sim.resolve("win-dc-01")
    assert resolved_ip == "10.0.0.1"
    assert poisoned is False
    print(f"[*] Test 2 Passed: Legitimate LLMNR resolution for 'win-dc-01' -> {resolved_ip}")

    # Test 3: Rogue Poisoner Simulation (e.g. Responder tool attack)
    rogue_ip = "10.0.0.99"
    poisoned_ip, was_poisoned = sim.resolve("win-dc-01", simulated_rogue_ip=rogue_ip)
    assert poisoned_ip == "10.0.0.99"
    assert was_poisoned is True
    print(f"[*] Test 3 Passed: Detected simulated rogue LLMNR poison response ({poisoned_ip})")

    print("All LLMNR and NetBIOS assertions passed successfully!")


if __name__ == "__main__":
    main()
