"""
Day 45: Layer 2 DHCP Snooping Switch Simulator
100% pure Python standard library implementation of DHCP Snooping security:
trusted vs untrusted port filtering, rogue server mitigation, and binding database.
"""

from dataclasses import dataclass, field
import enum
import time
from typing import Dict, List, Optional, Set, Tuple


class PortTrust(enum.Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"


@dataclass
class BindingEntry:
    mac_address: str
    ip_address: str
    vlan: int
    interface: str
    lease_duration: float
    expiry_timestamp: float


class DHCPSnoopingSwitch:
    """Simulates Layer 2 switch port security inspecting DHCP traffic."""

    def __init__(self, ports: Dict[str, PortTrust], rate_limit_pps: int = 10):
        self.ports = ports
        self.rate_limit_pps = rate_limit_pps
        self.port_traffic_history: Dict[str, List[float]] = {p: [] for p in ports}
        self.binding_db: Dict[str, BindingEntry] = {}
        self.dropped_rogue_packets = 0
        self.dropped_rate_limit = 0

    def _check_rate_limit(self, interface: str, timestamp: float) -> bool:
        history = self.port_traffic_history[interface]
        self.port_traffic_history[interface] = [t for t in history if timestamp - t < 1.0]
        if len(self.port_traffic_history[interface]) >= self.rate_limit_pps:
            return False
        self.port_traffic_history[interface].append(timestamp)
        return True

    def process_packet(
        self,
        interface: str,
        msg_type: int,
        src_mac: str,
        offered_ip: str,
        vlan: int,
        lease_time: float,
        timestamp: float
    ) -> Tuple[bool, str]:
        trust = self.ports.get(interface, PortTrust.UNTRUSTED)

        if trust == PortTrust.UNTRUSTED:
            if not self._check_rate_limit(interface, timestamp):
                self.dropped_rate_limit += 1
                return False, f"Rate limit exceeded on untrusted port {interface}"

        if trust == PortTrust.UNTRUSTED and msg_type in (2, 5):
            self.dropped_rogue_packets += 1
            return False, f"SECURITY ALERT: Blocked rogue DHCP reply (type {msg_type}) on untrusted port {interface}"

        if trust == PortTrust.TRUSTED and msg_type == 5:
            self.binding_db[src_mac] = BindingEntry(
                mac_address=src_mac,
                ip_address=offered_ip,
                vlan=vlan,
                interface=interface,
                lease_duration=lease_time,
                expiry_timestamp=timestamp + lease_time
            )
            return True, f"Learned binding: {src_mac} -> {offered_ip} on VLAN {vlan}"

        return True, "Packet forwarded"

    def verify_source_ip(self, src_mac: str, src_ip: str, timestamp: float) -> bool:
        entry = self.binding_db.get(src_mac)
        if not entry:
            return False
        if timestamp > entry.expiry_timestamp:
            del self.binding_db[src_mac]
            return False
        return entry.ip_address == src_ip


def main():
    print("=== Day 45: Layer 2 DHCP Snooping Switch Simulator ===")

    switch = DHCPSnoopingSwitch(
        ports={
            "Gi0/1": PortTrust.TRUSTED,
            "Gi0/2": PortTrust.UNTRUSTED,
            "Gi0/3": PortTrust.UNTRUSTED,
        },
        rate_limit_pps=5
    )

    now = time.time()

    ok, reason = switch.process_packet(
        interface="Gi0/2", msg_type=1, src_mac="00:11:22:33:44:01",
        offered_ip="0.0.0.0", vlan=10, lease_time=0, timestamp=now
    )
    assert ok is True
    print(f"[*] Test 1 Passed: Client DISCOVER on untrusted Gi0/2 allowed ({reason})")

    ok, reason = switch.process_packet(
        interface="Gi0/3", msg_type=2, src_mac="00:11:22:33:44:99",
        offered_ip="192.168.10.99", vlan=10, lease_time=3600, timestamp=now
    )
    assert ok is False
    assert switch.dropped_rogue_packets == 1
    print(f"[*] Test 2 Passed: Rogue OFFER on Gi0/3 blocked ({reason})")

    ok, reason = switch.process_packet(
        interface="Gi0/1", msg_type=5, src_mac="00:11:22:33:44:01",
        offered_ip="192.168.10.55", vlan=10, lease_time=3600, timestamp=now
    )
    assert ok is True
    assert "00:11:22:33:44:01" in switch.binding_db
    binding = switch.binding_db["00:11:22:33:44:01"]
    assert binding.ip_address == "192.168.10.55"
    print(f"[*] Test 3 Passed: Legitimate ACK on trusted Gi0/1 accepted. {reason}")

    assert switch.verify_source_ip("00:11:22:33:44:01", "192.168.10.55", now + 100) is True
    assert switch.verify_source_ip("00:11:22:33:44:01", "192.168.10.99", now + 100) is False
    print("[*] Test 4 Passed: IP Source Guard successfully validated legitimate and rejected spoofed IP")

    # Test 5: Rate limit throttling on untrusted port
    rate_test_time = now + 10.0
    for i in range(5):
        ok, _ = switch.process_packet("Gi0/2", 1, "AA:BB:CC:DD:EE:01", "0.0.0.0", 10, 0, rate_test_time)
        assert ok is True
    ok, reason = switch.process_packet("Gi0/2", 1, "AA:BB:CC:DD:EE:01", "0.0.0.0", 10, 0, rate_test_time)
    assert ok is False
    assert switch.dropped_rate_limit == 1
    print(f"[*] Test 5 Passed: DHCP starvation attack rate-limited ({reason})")

    print("All DHCP Snooping Switch assertions passed successfully!")


if __name__ == "__main__":
    main()
