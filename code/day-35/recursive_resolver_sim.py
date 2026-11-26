#!/usr/bin/env python3
"""
Day 35 Lab: Recursive Resolver Simulator with Bailiwick Security Filter
Simulates a full iterative root-to-authoritative resolver that serves stub
clients recursively, while enforcing the Bailiwick Rule (RFC 2181/7871)
to discard out-of-zone spoofed records.
Uses Python standard library only.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Record:
    name: str
    rtype: str
    value: str
    ttl: int = 300


@dataclass
class QueryResponse:
    status: str  # 'ANSWER', 'REFERRAL', 'NXDOMAIN'
    zone: str
    records: List[Record] = field(default_factory=list)
    referral_ns: Optional[str] = None
    referral_ip: Optional[str] = None


class MockNameserver:
    def __init__(self, zone: str, ip: str):
        self.zone = zone
        self.ip = ip
        self.records: Dict[str, List[Record]] = {}
        self.delegations: Dict[str, Tuple[str, str]] = {}  # subzone -> (ns_name, ns_ip)

    def handle_query(self, qname: str, qtype: str) -> QueryResponse:
        # Check direct answer
        if qname in self.records:
            matches = [r for r in self.records[qname] if r.rtype == qtype]
            if matches:
                return QueryResponse(status="ANSWER", zone=self.zone, records=matches)

        # Check delegations
        for subzone, (ns_name, ns_ip) in self.delegations.items():
            if qname.endswith(subzone) or qname == subzone.rstrip('.'):
                return QueryResponse(
                    status="REFERRAL",
                    zone=self.zone,
                    referral_ns=ns_name,
                    referral_ip=ns_ip
                )

        return QueryResponse(status="NXDOMAIN", zone=self.zone)


class RecursiveResolverWithBailiwick:
    def __init__(self, root_ip: str = "198.41.0.4"):
        self.root_ip = root_ip
        self.servers: Dict[str, MockNameserver] = {}
        self.cache: Dict[Tuple[str, str], List[Record]] = {}

    def register_server(self, server: MockNameserver):
        self.servers[server.ip] = server

    def is_in_bailiwick(self, record_name: str, server_zone: str) -> bool:
        """Enforces Bailiwick rule: server can only provide records within its authority."""
        # Clean trailing dots
        r_name = record_name.rstrip('.')
        s_zone = server_zone.rstrip('.')
        if s_zone == "":
            return True  # Root has universal bailiwick
        return r_name == s_zone or r_name.endswith('.' + s_zone)

    def resolve(self, qname: str, qtype: str = "A") -> List[Record]:
        """Recursive resolution entry point for client."""
        cache_key = (qname, qtype)
        if cache_key in self.cache:
            print(f"[CACHE HIT] Returning cached answer for {qname}")
            return self.cache[cache_key]

        print(f"[RECURSION START] Client queried: {qname} {qtype}")
        current_ip = self.root_ip
        hops = 0

        while hops < 10:
            hops += 1
            server = self.servers.get(current_ip)
            if not server:
                raise RuntimeError(f"Server {current_ip} not found!")

            resp = server.handle_query(qname, qtype)

            if resp.status == "ANSWER":
                # Validate Bailiwick before accepting into cache
                valid_records = []
                for r in resp.records:
                    if self.is_in_bailiwick(r.name, resp.zone):
                        valid_records.append(r)
                    else:
                        print(f"  [SECURITY ALERT] Discarded out-of-bailiwick record: {r.name} from zone {resp.zone}!")

                if valid_records:
                    self.cache[cache_key] = valid_records
                    return valid_records
                return []

            elif resp.status == "REFERRAL":
                print(f"  Hop {hops}: Server {server.zone} ({server.ip}) referred to {resp.referral_ns} ({resp.referral_ip})")
                current_ip = resp.referral_ip

            elif resp.status == "NXDOMAIN":
                print(f"  Hop {hops}: Server {server.zone} returned NXDOMAIN")
                return []

        raise RuntimeError("Recursion limit exceeded (possible delegation loop)")


def main():
    print("====================================================")
    print("DAY 35: RECURSIVE RESOLVER & BAILIWICK FILTER")
    print("====================================================")

    resolver = RecursiveResolverWithBailiwick()

    # 1. Setup Root server
    root = MockNameserver(zone=".", ip="198.41.0.4")
    root.delegations[".net."] = ("a.gtld-servers.net.", "192.5.6.30")
    resolver.register_server(root)

    # 2. Setup .net TLD server
    net_tld = MockNameserver(zone=".net.", ip="192.5.6.30")
    net_tld.delegations["cloudflare.net."] = ("ns1.cloudflare.net.", "172.64.32.1")
    resolver.register_server(net_tld)

    # 3. Setup Authoritative server for cloudflare.net
    auth = MockNameserver(zone="cloudflare.net.", ip="172.64.32.1")
    auth.records["api.cloudflare.net."] = [
        Record("api.cloudflare.net.", "A", "104.16.123.96")
    ]
    # Attempt to inject out-of-bailiwick poison record for google.com
    auth.records["api.cloudflare.net."].append(
        Record("google.com.", "A", "6.6.6.6")  # Malicious poison!
    )
    resolver.register_server(auth)

    # Test 1: Resolve legitimate record
    results = resolver.resolve("api.cloudflare.net.", "A")
    assert len(results) == 1, "Poison record must be discarded by Bailiwick filter"
    assert results[0].value == "104.16.123.96"
    print(f"  [PASS] Resolved legitimately: {results[0].name} -> {results[0].value}")

    # Test 2: Verify Cache Hit
    cached = resolver.resolve("api.cloudflare.net.", "A")
    assert len(cached) == 1
    print("  [PASS] Verified second query served from local cache.")

    print("\n[VERIFIED] Recursive Resolver with Bailiwick Filter passed all tests!")


if __name__ == "__main__":
    main()
