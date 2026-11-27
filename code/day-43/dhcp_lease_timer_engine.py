"""
Day 43: DHCP Dynamic Lease Renewal & Rebinding Timer Engine
100% pure Python standard library implementation of RFC 2131 lease timer transitions:
BOUND -> RENEWING (T1 unicast) -> REBINDING (T2 broadcast) -> EXPIRED.
"""

from dataclasses import dataclass
import enum
import time
from typing import Optional, Tuple


class LeaseState(enum.Enum):
    BOUND = "BOUND"
    RENEWING = "RENEWING"
    REBINDING = "REBINDING"
    EXPIRED = "EXPIRED"


@dataclass
class LeaseContract:
    client_ip: str
    server_ip: str
    lease_duration: float
    start_time: float
    t1_ratio: float = 0.50
    t2_ratio: float = 0.875

    @property
    def t1_time(self) -> float:
        return self.start_time + (self.lease_duration * self.t1_ratio)

    @property
    def t2_time(self) -> float:
        return self.start_time + (self.lease_duration * self.t2_ratio)

    @property
    def expire_time(self) -> float:
        return self.start_time + self.lease_duration


class DHCPLeaseTimerEngine:
    """Manages client lease timers and state machine transitions."""

    def __init__(self, lease: LeaseContract):
        self.lease = lease
        self.state = LeaseState.BOUND
        self.unicast_renew_attempts = 0
        self.broadcast_rebind_attempts = 0

    def evaluate_state(self, current_time: float) -> LeaseState:
        if current_time >= self.lease.expire_time:
            self.state = LeaseState.EXPIRED
        elif current_time >= self.lease.t2_time:
            self.state = LeaseState.REBINDING
        elif current_time >= self.lease.t1_time:
            self.state = LeaseState.RENEWING
        else:
            self.state = LeaseState.BOUND
        return self.state

    def simulate_tick(self, current_time: float, server_reachable: bool, backup_server_reachable: bool = False) -> Tuple[LeaseState, Optional[str]]:
        curr_state = self.evaluate_state(current_time)
        action = None

        if curr_state == LeaseState.RENEWING:
            self.unicast_renew_attempts += 1
            if server_reachable:
                self.lease.start_time = current_time
                self.state = LeaseState.BOUND
                self.unicast_renew_attempts = 0
                action = f"Renewed unicast with {self.lease.server_ip}"
            else:
                action = f"Unicast renewal attempt #{self.unicast_renew_attempts} failed (server unreachable)"

        elif curr_state == LeaseState.REBINDING:
            self.broadcast_rebind_attempts += 1
            if backup_server_reachable:
                self.lease.start_time = current_time
                self.state = LeaseState.BOUND
                self.broadcast_rebind_attempts = 0
                action = "Rebound via broadcast with backup server"
            else:
                action = f"Broadcast rebind attempt #{self.broadcast_rebind_attempts} failed"

        elif curr_state == LeaseState.EXPIRED:
            action = "Lease expired: client unbinds IP and enters INIT state"

        return self.state, action


def main():
    print("=== Day 43: DHCP Dynamic Lease Renewal & Rebinding Timer Engine ===")

    contract = LeaseContract(
        client_ip="192.168.1.105",
        server_ip="192.168.1.1",
        lease_duration=100.0,
        start_time=0.0
    )
    engine = DHCPLeaseTimerEngine(contract)

    assert contract.t1_time == 50.0
    assert contract.t2_time == 87.5
    assert contract.expire_time == 100.0

    s, act = engine.simulate_tick(current_time=25.0, server_reachable=True)
    assert s == LeaseState.BOUND
    assert act is None

    s, act = engine.simulate_tick(current_time=50.0, server_reachable=True)
    assert s == LeaseState.BOUND
    assert "Renewed unicast" in act
    assert contract.start_time == 50.0
    print("[*] Scenario 1 Passed: T1 Unicast Renewal reset lease at t=50.0s")

    contract2 = LeaseContract(
        client_ip="192.168.1.106",
        server_ip="192.168.1.1",
        lease_duration=100.0,
        start_time=0.0
    )
    engine2 = DHCPLeaseTimerEngine(contract2)

    s, act = engine2.simulate_tick(current_time=60.0, server_reachable=False)
    assert s == LeaseState.RENEWING
    assert "failed" in act

    s, act = engine2.simulate_tick(current_time=90.0, server_reachable=False, backup_server_reachable=True)
    assert s == LeaseState.BOUND
    assert "Rebound via broadcast" in act
    print("[*] Scenario 2 Passed: T2 Rebind successfully recovered via broadcast backup server")

    contract3 = LeaseContract(
        client_ip="192.168.1.107",
        server_ip="192.168.1.1",
        lease_duration=100.0,
        start_time=0.0
    )
    engine3 = DHCPLeaseTimerEngine(contract3)
    s, act = engine3.simulate_tick(current_time=105.0, server_reachable=False, backup_server_reachable=False)
    assert s == LeaseState.EXPIRED
    assert "Lease expired" in act
    print("[*] Scenario 3 Passed: Lease expired at t=105s, IP reclaimed")

    print("All DHCP Lease Timer Engine assertions passed successfully!")


if __name__ == "__main__":
    main()
