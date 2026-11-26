#!/usr/bin/env python3
"""
Day 31 Lab: DNS Hierarchy Walker & Referral Chaser
Simulates how a DNS resolver walks the global domain tree:
Root (.) -> TLD (.com) -> Authoritative Nameserver (example.com) -> Host IP.
Uses Python standard library only.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DNSRecord:
    name: str
    record_type: str  # 'A', 'NS', 'SOA'
    value: str
    ttl: int = 300


@dataclass
class NameserverZone:
    zone_name: str
    server_ip: str
    records: Dict[str, List[DNSRecord]] = field(default_factory=dict)
    referrals: Dict[str, str] = field(default_factory=dict)  # subzone -> ns_ip

    def query(self, qname: str, qtype: str) -> Dict[str, any]:
        """Queries this nameserver for qname and qtype."""
        # 1. Direct answer match
        if qname in self.records:
            matching = [r for r in self.records[qname] if r.record_type == qtype]
            if matching:
                return {"status": "ANSWER", "records": matching}

        # 2. Check for child referral (delegation)
        for subzone, ns_ip in self.referrals.items():
            if qname.endswith(subzone) or qname == subzone.rstrip('.'):
                return {"status": "REFERRAL", "target_ns": ns_ip, "zone": subzone}

        return {"status": "NXDOMAIN", "records": []}


class DNSHierarchySimulator:
    def __init__(self):
        self.servers: Dict[str, NameserverZone] = {}
        self.root_ip = "198.41.0.4"  # Mock a.root-servers.net
        self._bootstrap_mock_internet()

    def _bootstrap_mock_internet(self):
        # 1. Root Server (.)
        root = NameserverZone(zone_name=".", server_ip=self.root_ip)
        root.referrals[".com."] = "192.5.6.30"  # a.gtld-servers.net
        root.referrals[".org."] = "199.19.56.1" # a0.org.afilias-nst.info
        self.servers[root.server_ip] = root

        # 2. TLD Server (.com)
        com_tld = NameserverZone(zone_name=".com.", server_ip="192.5.6.30")
        com_tld.referrals["example.com."] = "208.67.222.222"
        com_tld.referrals["google.com."] = "216.239.32.10"
        self.servers[com_tld.server_ip] = com_tld

        # 3. Authoritative Server (example.com)
        auth_example = NameserverZone(zone_name="example.com.", server_ip="208.67.222.222")
        auth_example.records["example.com."] = [
            DNSRecord("example.com.", "A", "93.184.216.34", 86400),
            DNSRecord("example.com.", "NS", "ns1.example.com.", 86400)
        ]
        auth_example.records["api.example.com."] = [
            DNSRecord("api.example.com.", "A", "93.184.216.35", 300)
        ]
        self.servers[auth_example.server_ip] = auth_example

    def resolve_iterative(self, target_domain: str, qtype: str = "A") -> List[DNSRecord]:
        """Emulates iterative resolution walking from root down to authoritative."""
        # Ensure FQDN trailing dot
        fqdn = target_domain if target_domain.endswith('.') else target_domain + '.'
        current_server_ip = self.root_ip
        step = 1

        print(f"[*] Starting Iterative Resolution for: {fqdn} (Type: {qtype})")

        while True:
            current_server = self.servers.get(current_server_ip)
            if not current_server:
                raise RuntimeError(f"Server {current_server_ip} unreachable!")

            print(f"  Step {step}: Querying {current_server.zone_name} at IP {current_server.server_ip}...")
            resp = current_server.query(fqdn, qtype)

            if resp["status"] == "ANSWER":
                print(f"  [+] Final Answer Received from {current_server.zone_name}!")
                for r in resp["records"]:
                    print(f"      -> {r.name}  TTL={r.ttl}  IN {r.record_type}  {r.value}")
                return resp["records"]

            elif resp["status"] == "REFERRAL":
                print(f"  [->] Referral Delegation to {resp['zone']} at IP {resp['target_ns']}")
                current_server_ip = resp["target_ns"]
                step += 1

            elif resp["status"] == "NXDOMAIN":
                print(f"  [-] NXDOMAIN: {fqdn} does not exist in {current_server.zone_name}")
                return []


def main():
    print("====================================================")
    print("DAY 31: DNS HIERARCHY WALKER & REFERRAL CHASER")
    print("====================================================")

    sim = DNSHierarchySimulator()

    # Test 1: Resolve apex domain
    records = sim.resolve_iterative("example.com")
    assert len(records) > 0
    assert records[0].value == "93.184.216.34"
    print("  [PASS] Test 1: example.com resolved successfully.")

    # Test 2: Resolve subdomain
    print()
    sub_records = sim.resolve_iterative("api.example.com")
    assert len(sub_records) > 0
    assert sub_records[0].value == "93.184.216.35"
    print("  [PASS] Test 2: api.example.com resolved successfully.")

    # Test 3: Non-existent domain
    print()
    nx_records = sim.resolve_iterative("nonexistent.example.com")
    assert len(nx_records) == 0
    print("  [PASS] Test 3: Non-existent domain correctly returned NXDOMAIN.")

    print("\n[VERIFIED] DNS Hierarchy Walker passed all tests with 100% fidelity!")


if __name__ == "__main__":
    main()
