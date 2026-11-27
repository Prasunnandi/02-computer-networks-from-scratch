"""
Day 46: IPv4 Link-Local (APIPA) & Multicast DNS (mDNS) Simulator
100% pure Python standard library implementation of RFC 3927 APIPA (169.254/16)
dynamic address allocation with ARP Probing/Announcing and RFC 6762 mDNS queries.
"""

from dataclasses import dataclass
import random
import struct
import time
from typing import Dict, List, Optional, Tuple


@dataclass
class ARPPacket:
    op: int                  # 1 = ARP Request / Probe, 2 = ARP Reply / Announce
    sha: str                 # Sender Hardware Address (MAC)
    spa: str                 # Sender Protocol Address (IP)
    tha: str                 # Target Hardware Address (MAC)
    tpa: str                 # Target Protocol Address (IP)


class APIPAAllocator:
    """Simulates RFC 3927 dynamic IPv4 link-local address configuration."""

    NETWORK_PREFIX = "169.254."
    PROBE_NUM = 3            # RFC 3927 recommends 3 probes
    ANNOUNCE_NUM = 2         # RFC 3927 recommends 2 announcements

    def __init__(self, mac_address: str):
        self.mac = mac_address
        self.configured_ip: Optional[str] = None
        self.conflict_count = 0

    def generate_candidate_ip(self) -> str:
        """Generates random candidate IP in 169.254.1.0 to 169.254.254.255."""
        # RFC 3927 reserves 169.254.0.0/24 and 169.254.255.0/24
        octet3 = random.randint(1, 254)
        octet4 = random.randint(1, 254)
        return f"169.254.{octet3}.{octet4}"

    def build_arp_probe(self, candidate_ip: str) -> ARPPacket:
        """Constructs an ARP Probe: SIP=0.0.0.0, DIP=candidate_ip."""
        return ARPPacket(
            op=1,
            sha=self.mac,
            spa="0.0.0.0",
            tha="00:00:00:00:00:00",
            tpa=candidate_ip
        )

    def build_arp_announcement(self, candidate_ip: str) -> ARPPacket:
        """Constructs a Gratuitous ARP Announcement: SIP=candidate_ip, DIP=candidate_ip."""
        return ARPPacket(
            op=2,
            sha=self.mac,
            spa=candidate_ip,
            tha="FF:FF:FF:FF:FF:FF",
            tpa=candidate_ip
        )

    def allocate(self, network_existing_ips: List[str]) -> Tuple[str, List[ARPPacket]]:
        """Executes full APIPA probe and claim sequence."""
        packets_sent: List[ARPPacket] = []

        while True:
            candidate = self.generate_candidate_ip()
            conflict = False

            # Transmit 3 ARP Probes
            for _ in range(self.PROBE_NUM):
                probe = self.build_arp_probe(candidate)
                packets_sent.append(probe)
                if candidate in network_existing_ips:
                    conflict = True
                    break

            if conflict:
                self.conflict_count += 1
                continue  # Pick new candidate on conflict

            # Successfully claimed: send 2 ARP Announcements
            for _ in range(self.ANNOUNCE_NUM):
                ann = self.build_arp_announcement(candidate)
                packets_sent.append(ann)

            self.configured_ip = candidate
            return candidate, packets_sent


class MDNSCodec:
    """Encodes and decodes RFC 6762 Multicast DNS queries and responses."""

    MULTICAST_IPV4 = "224.0.0.251"
    PORT = 5353

    @staticmethod
    def encode_query(qname: str, qtype: int = 1) -> bytes:
        """Encodes an mDNS query for a .local domain."""
        # 12-byte DNS header: ID=0, Flags=0, QDCOUNT=1, ANCOUNT=0, NSCOUNT=0, ARCOUNT=0
        header = struct.pack("!HHHHHH", 0, 0x0000, 1, 0, 0, 0)
        qname_bytes = bytearray()
        for part in qname.split("."):
            qname_bytes.append(len(part))
            qname_bytes.extend(part.encode("ascii"))
        qname_bytes.append(0)  # Null terminator

        # QTYPE=1 (A), QCLASS=1 (IN) with unicast-response bit (0x8000) or standard
        question = struct.pack("!HH", qtype, 1)
        return header + bytes(qname_bytes) + question

    @staticmethod
    def decode_query(data: bytes) -> Tuple[int, str, int]:
        """Decodes an mDNS query packet."""
        header = struct.unpack("!HHHHHH", data[:12])
        qdcount = header[2]
        idx = 12
        labels = []
        while idx < len(data):
            length = data[idx]
            idx += 1
            if length == 0:
                break
            labels.append(data[idx:idx + length].decode("ascii"))
            idx += length

        qname = ".".join(labels)
        qtype, qclass = struct.unpack("!HH", data[idx:idx + 4])
        return qdcount, qname, qtype


def main():
    print("=== Day 46: IPv4 Link-Local (APIPA) & Multicast DNS (mDNS) Simulator ===")

    # Test 1: APIPA Allocation without conflict
    allocator = APIPAAllocator(mac_address="00:11:22:33:44:55")
    ip, packets = allocator.allocate(network_existing_ips=["169.254.10.20", "169.254.10.21"])
    assert ip.startswith("169.254.")
    assert allocator.configured_ip == ip
    # 3 Probes + 2 Announces = 5 packets
    assert len(packets) == 5
    assert packets[0].op == 1
    assert packets[0].spa == "0.0.0.0"
    assert packets[0].tpa == ip
    assert packets[3].op == 2
    assert packets[3].spa == ip
    assert packets[3].tpa == ip
    print(f"[*] Test 1 Passed: Claimed APIPA IP {ip} with {len(packets)} ARP frames")

    # Test 2: mDNS Query Encoding & Decoding
    query_pkt = MDNSCodec.encode_query("printer.local", qtype=1)
    qdcount, qname, qtype = MDNSCodec.decode_query(query_pkt)
    assert qdcount == 1
    assert qname == "printer.local"
    assert qtype == 1
    print(f"[*] Test 2 Passed: Encoded & Decoded mDNS query for '{qname}' (Type {qtype})")

    print("All APIPA and mDNS assertions passed successfully!")


if __name__ == "__main__":
    main()
