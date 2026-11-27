"""
Day 49: Precision Time Protocol (IEEE 1588 PTP v2) Sync Simulator
100% pure Python standard library implementation of PTP End-to-End (E2E)
hardware timestamp synchronization: Mean Path Delay, Clock Offset, and nanosecond correction.
"""

from dataclasses import dataclass
import struct
from typing import Tuple


@dataclass
class PTPTimestamp:
    seconds: int
    nanoseconds: int

    def to_nanoseconds(self) -> int:
        return (self.seconds * 1_000_000_000) + self.nanoseconds

    @classmethod
    def from_nanoseconds(cls, total_ns: int) -> "PTPTimestamp":
        sec = total_ns // 1_000_000_000
        ns = total_ns % 1_000_000_000
        return cls(seconds=sec, nanoseconds=ns)


class IEEE1588PTPEngine:
    """Simulates IEEE 1588 PTP v2 E2E delay request-response clock synchronization."""

    @staticmethod
    def calculate_delay_and_offset(
        t1_ns: int,  # Master Sync transmit timestamp
        t2_ns: int,  # Slave Sync receive timestamp
        t3_ns: int,  # Slave Delay_Req transmit timestamp
        t4_ns: int   # Master Delay_Req receive timestamp
    ) -> Tuple[int, int]:
        """
        Mean Path Delay D = ((t2 - t1) + (t4 - t3)) / 2
        Clock Offset theta = ((t2 - t1) - (t4 - t3)) / 2
        All calculations in integer nanoseconds.
        """
        d1 = t2_ns - t1_ns  # Forward delay + offset
        d2 = t4_ns - t3_ns  # Reverse delay - offset

        mean_path_delay = (d1 + d2) // 2
        clock_offset = (d1 - d2) // 2
        return mean_path_delay, clock_offset


class PTPSlaveClock:
    """Maintains a simulated slave hardware clock adjusted via PTP feedback."""

    def __init__(self, initial_drift_ns: int):
        self.offset_drift_ns = initial_drift_ns

    def get_time_ns(self, master_time_ns: int) -> int:
        """Returns slave clock reading given master reference time."""
        return master_time_ns + self.offset_drift_ns

    def adjust_clock(self, offset_ns: int):
        """Applies correction offset to eliminate clock drift."""
        self.offset_drift_ns -= offset_ns


def main():
    print("=== Day 49: Precision Time Protocol (IEEE 1588 PTP) Sync Simulator ===")

    # Initialize slave clock running 250,000 nanoseconds (250 microseconds) ahead
    slave = PTPSlaveClock(initial_drift_ns=250_000)
    one_way_fiber_delay_ns = 5_000  # 5 microseconds propagation delay

    # Step 1: Master transmits Sync message at t1
    t1_master_ns = 1_000_000_000_000  # 1000.000000000 seconds
    t2_slave_ns = slave.get_time_ns(t1_master_ns + one_way_fiber_delay_ns)

    # Step 2: Slave transmits Delay_Req message at t3
    t3_slave_ns = t2_slave_ns + 10_000_000  # 10ms later
    # Corresponding master arrival time t4:
    # t3_slave_ns was measured with slave offset, so master reference time when t3 sent is:
    t3_master_ref = t3_slave_ns - slave.offset_drift_ns
    t4_master_ns = t3_master_ref + one_way_fiber_delay_ns

    # Step 3: Run PTP calculation
    delay_ns, offset_ns = IEEE1588PTPEngine.calculate_delay_and_offset(
        t1_ns=t1_master_ns,
        t2_ns=t2_slave_ns,
        t3_ns=t3_slave_ns,
        t4_ns=t4_master_ns
    )

    print(f"[*] Measured Mean Path Delay: {delay_ns} ns ({delay_ns / 1000:.1f} us)")
    print(f"[*] Calculated Clock Offset:  {offset_ns} ns ({offset_ns / 1000:.1f} us)")

    assert delay_ns == one_way_fiber_delay_ns
    assert offset_ns == 250_000

    # Step 4: Adjust slave clock
    slave.adjust_clock(offset_ns)
    assert slave.offset_drift_ns == 0
    print("[*] Slave clock adjusted: residual offset is 0 nanoseconds!")

    print("All IEEE 1588 PTP assertions passed successfully!")


if __name__ == "__main__":
    main()
