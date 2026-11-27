"""
Day 48: Network Time Protocol (NTP v4) Timestamp Engine
100% pure Python standard library implementation of RFC 5905 NTP 48-byte header codec,
64-bit fixed-point timestamp math, clock offset (theta), and round-trip delay (delta).
"""

from dataclasses import dataclass
import struct
import time
from typing import Tuple

# NTP epoch begins Jan 1, 1900; Unix epoch begins Jan 1, 1970
NTP_TIMESTAMP_DELTA = 2208988800


@dataclass
class NTPPacket:
    leap_indicator: int      # 2 bits
    version: int             # 3 bits (usually 4)
    mode: int                # 3 bits (3 = Client, 4 = Server)
    stratum: int             # 8 bits (1 = Primary Reference, 2-15 = Secondary)
    poll: int                # 8 bits (poll interval)
    precision: int           # 8 bits (signed integer)
    root_delay: float        # 32 bits (16.16 fixed-point)
    root_dispersion: float   # 32 bits (16.16 fixed-point)
    ref_id: bytes            # 32 bits (e.g., b'GPS\x00' or IPv4)
    ref_timestamp: float     # 64 bits (32.32 fixed-point)
    orig_timestamp: float    # t1: client transmit time
    recv_timestamp: float    # t2: server receive time
    tx_timestamp: float      # t3: server transmit time


class NTPCodec:
    """Serializes and deserializes RFC 5905 NTP v4 48-byte packets."""

    HEADER_FORMAT = "!BBBbII4sQQQQ"
    HEADER_SIZE = 48

    @classmethod
    def timestamp_to_fixed_point(cls, ts: float) -> int:
        """Converts floating-point seconds (Unix epoch) to NTP 64-bit fixed-point."""
        if ts == 0.0:
            return 0
        ntp_seconds = ts + NTP_TIMESTAMP_DELTA
        sec_int = int(ntp_seconds)
        frac = int((ntp_seconds - sec_int) * (2 ** 32))
        return (sec_int << 32) | (frac & 0xFFFFFFFF)

    @classmethod
    def fixed_point_to_timestamp(cls, fp: int) -> float:
        """Converts NTP 64-bit fixed-point to floating-point seconds (Unix epoch)."""
        if fp == 0:
            return 0.0
        sec_int = (fp >> 32) & 0xFFFFFFFF
        frac = fp & 0xFFFFFFFF
        ts = sec_int - NTP_TIMESTAMP_DELTA + (frac / (2 ** 32))
        return ts

    @classmethod
    def encode(cls, pkt: NTPPacket) -> bytes:
        li_vn_mode = ((pkt.leap_indicator & 0x03) << 6) | ((pkt.version & 0x07) << 3) | (pkt.mode & 0x07)
        root_delay_fp = int(pkt.root_delay * 65536)
        root_disp_fp = int(pkt.root_dispersion * 65536)

        return struct.pack(
            cls.HEADER_FORMAT,
            li_vn_mode,
            pkt.stratum,
            pkt.poll,
            pkt.precision,
            root_delay_fp,
            root_disp_fp,
            pkt.ref_id.ljust(4, b"\x00"),
            cls.timestamp_to_fixed_point(pkt.ref_timestamp),
            cls.timestamp_to_fixed_point(pkt.orig_timestamp),
            cls.timestamp_to_fixed_point(pkt.recv_timestamp),
            cls.timestamp_to_fixed_point(pkt.tx_timestamp)
        )

    @classmethod
    def decode(cls, data: bytes) -> NTPPacket:
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} bytes")

        unpacked = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        li_vn_mode = unpacked[0]
        li = (li_vn_mode >> 6) & 0x03
        version = (li_vn_mode >> 3) & 0x07
        mode = li_vn_mode & 0x07

        return NTPPacket(
            leap_indicator=li,
            version=version,
            mode=mode,
            stratum=unpacked[1],
            poll=unpacked[2],
            precision=unpacked[3],
            root_delay=unpacked[4] / 65536.0,
            root_dispersion=unpacked[5] / 65536.0,
            ref_id=unpacked[6],
            ref_timestamp=cls.fixed_point_to_timestamp(unpacked[7]),
            orig_timestamp=cls.fixed_point_to_timestamp(unpacked[8]),
            recv_timestamp=cls.fixed_point_to_timestamp(unpacked[9]),
            tx_timestamp=cls.fixed_point_to_timestamp(unpacked[10])
        )


class NTPClockFilter:
    """Calculates clock offset and round-trip delay using RFC 5905 formulas."""

    @staticmethod
    def calculate_offset_and_delay(t1: float, t2: float, t3: float, t4: float) -> Tuple[float, float]:
        """
        t1 = client transmit timestamp
        t2 = server receive timestamp
        t3 = server transmit timestamp
        t4 = client receive timestamp

        theta (clock offset) = ((t2 - t1) + (t3 - t4)) / 2
        delta (round trip delay) = (t4 - t1) - (t3 - t2)
        """
        offset = ((t2 - t1) + (t3 - t4)) / 2.0
        delay = (t4 - t1) - (t3 - t2)
        return offset, delay


def main():
    print("=== Day 48: Network Time Protocol (NTP v4) Timestamp Engine ===")

    # Test 1: Fixed-point timestamp conversion accuracy
    now = 1700000000.125
    fp = NTPCodec.timestamp_to_fixed_point(now)
    recovered = NTPCodec.fixed_point_to_timestamp(fp)
    assert abs(now - recovered) < 1e-6
    print(f"[*] Test 1 Passed: Timestamp {now} converted to 64-bit FP and back with microsecond fidelity")

    # Test 2: NTP Packet Serialization and Parsing
    pkt = NTPPacket(
        leap_indicator=0,
        version=4,
        mode=4,  # Server
        stratum=1,  # Primary GPS source
        poll=6,
        precision=-20,
        root_delay=0.0001,
        root_dispersion=0.0002,
        ref_id=b"GPS",
        ref_timestamp=now - 50.0,
        orig_timestamp=now,
        recv_timestamp=now + 0.015,
        tx_timestamp=now + 0.016
    )

    encoded = NTPCodec.encode(pkt)
    assert len(encoded) == 48
    decoded = NTPCodec.decode(encoded)
    assert decoded.stratum == 1
    assert decoded.version == 4
    assert decoded.ref_id.rstrip(b"\x00") == b"GPS"
    assert abs(decoded.tx_timestamp - pkt.tx_timestamp) < 1e-6
    print(f"[*] Test 2 Passed: Encoded & Decoded 48-byte NTP v4 frame (Stratum {decoded.stratum})")

    # Test 3: Mathematical offset and delay calculation
    # Simulate a network where round-trip latency is 20ms and client clock is 50ms slow
    client_tx = 1000.000  # t1
    server_rx = 1000.060  # t2 (+10ms propagation + 50ms clock offset)
    server_tx = 1000.062  # t3 (2ms server processing)
    client_rx = 1000.022  # t4 (+10ms return propagation)

    theta, delta = NTPClockFilter.calculate_offset_and_delay(client_tx, server_rx, server_tx, client_rx)
    assert abs(theta - 0.050) < 1e-6
    assert abs(delta - 0.020) < 1e-6
    print(f"[*] Test 3 Passed: Verified RFC 5905 formulas: Offset theta={theta*1000:.1f}ms, Delay delta={delta*1000:.1f}ms")

    print("All NTP v4 assertions passed successfully!")


if __name__ == "__main__":
    main()
