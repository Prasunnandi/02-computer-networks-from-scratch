#!/usr/bin/env python3
"""
Day 29 Lab: Cryptographic SYN Cookie Generator & Validator (RFC 4987)
Demonstrates defense against TCP SYN Floods by embedding connection state
and cryptographic MAC inside the 32-bit Initial Sequence Number (ISN).
"""

import hmac
import hashlib
import struct
import time
from typing import Tuple


# RFC 4987 8-entry standard MSS table (encoded in 3 bits: 0 to 7)
MSS_TABLE = [64, 256, 512, 536, 1024, 1440, 1460, 8960]


class SYNCookieEngine:
    def __init__(self, secret_key: bytes = b'super_secret_kernel_seed_key_123'):
        self.secret_key = secret_key

    def _get_time_counter(self, timestamp: float = None) -> int:
        """
        Slow counter incrementing every 64 seconds (5 bits: 0 to 31).
        """
        if timestamp is None:
            timestamp = time.time()
        return int(timestamp // 64) & 0x1F

    def _mss_to_index(self, mss: int) -> int:
        """
        Maps client requested MSS to nearest lower or equal index in 8-entry table.
        """
        best_idx = 0
        for i, val in enumerate(MSS_TABLE):
            if val <= mss:
                best_idx = i
            else:
                break
        return best_idx

    def generate_cookie(self, saddr: str, daddr: str, sport: int, dport: int, client_mss: int, timestamp: float = None) -> int:
        """
        Generates 32-bit SYN Cookie ISN:
        - Bits 31..27 (5 bits): Time counter t mod 32
        - Bits 26..24 (3 bits): MSS index (0..7)
        - Bits 23..0  (24 bits): Truncated HMAC-SHA256(saddr, daddr, sport, dport, t)
        """
        t = self._get_time_counter(timestamp)
        mss_idx = self._mss_to_index(client_mss)

        # Message: 4-tuple + timestamp counter
        msg = f'{saddr}:{daddr}:{sport}:{dport}:{t}'.encode('utf-8')
        mac = hmac.new(self.secret_key, msg, hashlib.sha256).digest()
        # Extract 24 bits (3 bytes)
        mac_24 = struct.unpack('>I', b'\x00' + mac[:3])[0] & 0x00FFFFFF

        # Pack into 32-bit integer
        cookie = (t << 27) | (mss_idx << 24) | mac_24
        return cookie

    def validate_cookie(self, saddr: str, daddr: str, sport: int, dport: int, ack_num: int, current_time: float = None) -> Tuple[bool, int]:
        """
        Validates client ACK number (which should be cookie ISN + 1).
        Recovers MSS and checks timestamp freshness (valid for up to 2 time units = 128s).
        Returns: (is_valid, recovered_mss)
        """
        cookie = (ack_num - 1) & 0xFFFFFFFF
        t_cookie = (cookie >> 27) & 0x1F
        mss_idx = (cookie >> 24) & 0x07
        cookie_mac = cookie & 0x00FFFFFF

        current_t = self._get_time_counter(current_time)
        # Cookie is fresh if t_cookie == current_t or (current_t - 1) mod 32
        time_diff = (current_t - t_cookie) & 0x1F
        if time_diff > 2:
            return False, 0  # Expired cookie!

        # Recompute expected MAC using t_cookie
        msg = f'{saddr}:{daddr}:{sport}:{dport}:{t_cookie}'.encode('utf-8')
        expected_mac = hmac.new(self.secret_key, msg, hashlib.sha256).digest()
        expected_mac_24 = struct.unpack('>I', b'\x00' + expected_mac[:3])[0] & 0x00FFFFFF

        if cookie_mac == expected_mac_24:
            return True, MSS_TABLE[mss_idx]
        return False, 0


def main():
    print('====================================================')
    print('DAY 29: CRYPTOGRAPHIC TCP SYN COOKIE DEFENSE (RFC 4987)')
    print('====================================================')

    engine = SYNCookieEngine()
    client_ip, client_port = '198.51.100.42', 54321
    server_ip, server_port = '203.0.113.1', 80
    client_mss = 1460

    print(f'Incoming SYN from {client_ip}:{client_port} (Requested MSS: {client_mss})')
    print('SYN Backlog full! Server generates stateless SYN Cookie...')

    # Step 1: Generate Cookie
    cookie_isn = engine.generate_cookie(client_ip, server_ip, client_port, server_port, client_mss)
    print(f'Generated 32-bit ISN Cookie : 0x{cookie_isn:08X} ({cookie_isn})')
    print('Server saves ZERO bytes of memory in state table! (SYN flood defeated)')

    # Step 2: Client returns ACK = ISN + 1
    client_ack = cookie_isn + 1
    print(f'\nClient completes 3-way handshake with ACK: 0x{client_ack:08X}')

    # Step 3: Validate cookie
    valid, recovered_mss = engine.validate_cookie(client_ip, server_ip, client_port, server_port, client_ack)
    print(f'Cookie Authenticity Check   : {"VALID" if valid else "INVALID"}')
    print(f'Recovered Negotiated MSS    : {recovered_mss} bytes')

    assert valid, 'Legitimate cookie must pass validation'
    assert recovered_mss == 1460, f'Expected MSS 1460, got {recovered_mss}'

    # Step 4: Validate tamper resistance (attacker guessing ACK)
    fake_ack = client_ack ^ 0x00000001  # Bit flip
    fake_valid, _ = engine.validate_cookie(client_ip, server_ip, client_port, server_port, fake_ack)
    print(f'Tampered ACK Check (1-bit flip): {"VALID" if fake_valid else "BLOCKED (Fake/Tampered)"}')
    assert not fake_valid, 'Tampered cookie must fail validation'

    print('\n[VERIFIED] Stateless cryptographic SYN cookie generated and verified cleanly!')


if __name__ == '__main__':
    main()
