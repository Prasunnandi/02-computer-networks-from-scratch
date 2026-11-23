"""
Day 07: IPv4 Packet Fragmentation & Reassembly Engine
Zero-Knowledge-Gap Implementation of RFC 791 Fragmentation Mechanics.

Demonstrates:
1. Fragmenting an oversized IP datagram across an MTU boundary.
2. Enforcing the strict 8-byte alignment rule for intermediate fragment payloads.
3. Correct manipulation of DF (Don't Fragment) and MF (More Fragments) flags and 13-bit Fragment Offsets.
4. Destination host reassembly engine matching Identification and reconstructing the byte stream.
"""

from typing import List, Dict, Any, Tuple


class IPv4Fragment:
    """Represents an individual IPv4 packet fragment."""
    def __init__(self, ident: int, df: bool, mf: bool, offset_8byte_units: int, payload: bytes):
        self.ident = ident
        self.df = df
        self.mf = mf
        self.offset = offset_8byte_units # in 8-byte units
        self.payload = payload
        self.header_len = 20
        self.total_length = self.header_len + len(payload)

    @property
    def byte_offset(self) -> int:
        return self.offset * 8

    def __repr__(self):
        return (f"<Frag ID={hex(self.ident)} | Len={self.total_length}B | "
                f"DF={int(self.df)} MF={int(self.mf)} | Offset={self.offset} ({self.byte_offset}B)>")


class IPv4FragmentationRouter:
    """Simulates router-side fragmentation logic."""

    @staticmethod
    def fragment(ident: int, payload: bytes, mtu: int, df_flag: bool = False) -> List[IPv4Fragment]:
        """
        Splits a payload into fragments that conform to the link MTU.
        Raises RuntimeError if df_flag is set and packet exceeds MTU.
        """
        header_len = 20
        total_len = header_len + len(payload)

        if total_len <= mtu:
            # Fits within MTU: No fragmentation required
            return [IPv4Fragment(ident, df=df_flag, mf=False, offset_8byte_units=0, payload=payload)]

        if df_flag:
            raise RuntimeError(f"ICMP Type 3, Code 4: Fragmentation Needed and DF Set! (Packet {total_len}B > MTU {mtu}B)")

        # Max payload per fragment must be a multiple of 8 bytes:
        max_raw_payload = mtu - header_len
        max_aligned_payload = max_raw_payload - (max_raw_payload % 8)

        fragments = []
        current_byte_offset = 0
        remaining_data = payload

        while remaining_data:
            chunk = remaining_data[:max_aligned_payload]
            remaining_data = remaining_data[max_aligned_payload:]

            is_more_fragments = len(remaining_data) > 0
            offset_units = current_byte_offset // 8

            frag = IPv4Fragment(
                ident=ident,
                df=False,
                mf=is_more_fragments,
                offset_8byte_units=offset_units,
                payload=chunk
            )
            fragments.append(frag)
            current_byte_offset += len(chunk)

        return fragments


class IPv4Reassembler:
    """Simulates destination host buffer reassembly."""

    @staticmethod
    def reassemble(fragments: List[IPv4Fragment]) -> bytes:
        if not fragments:
            return b""

        ident = fragments[0].ident
        # Sort fragments by byte offset
        sorted_frags = sorted(fragments, key=lambda f: f.byte_offset)

        reassembled = bytearray()
        expected_offset = 0

        for frag in sorted_frags:
            assert frag.ident == ident, "Mismatched fragment Identification in reassembly queue!"
            assert frag.byte_offset == expected_offset, (
                f"Missing fragment gap! Expected offset {expected_offset}, got {frag.byte_offset}"
            )
            reassembled.extend(frag.payload)
            expected_offset += len(frag.payload)

        # The last fragment must have MF=False
        assert sorted_frags[-1].mf is False, "Terminal fragment must have MF=0!"
        return bytes(reassembled)


# --- SELF-CONTAINED VERIFICATION LAB ---
if __name__ == "__main__":
    print("=" * 60)
    print("DAY 07 LAB: IPV4 FRAGMENTATION & REASSEMBLY SIMULATOR")
    print("=" * 60)

    # 1. Create a 3,980-byte synthetic application payload (e.g. large TLS certificate + HTML)
    original_data = bytes([i % 256 for i in range(3980)])
    packet_id = 0x4A21
    print(f"\n[1] Original Datagram: 20-byte IP Header + {len(original_data)}-byte Payload = 4,000 bytes.")

    # 2. Fragment across standard Ethernet MTU = 1,500 bytes
    link_mtu = 1500
    print(f"\n[2] Forwarding across Link MTU = {link_mtu} bytes (DF=0)...")
    frags = IPv4FragmentationRouter.fragment(ident=packet_id, payload=original_data, mtu=link_mtu, df_flag=False)

    print(f"    Generated {len(frags)} fragments:")
    for idx, f in enumerate(frags, 1):
        print(f"    - Fragment {idx}: {f} | Payload = {len(f.payload)} bytes")

    # Assertions on fragment boundaries
    assert len(frags) == 3, f"Expected 3 fragments, got {len(frags)}"
    assert len(frags[0].payload) == 1480, "Fragment 1 payload must be 1,480 bytes (8-byte aligned)!"
    assert frags[0].mf is True and frags[0].offset == 0
    assert len(frags[1].payload) == 1480
    assert frags[1].mf is True and frags[1].offset == 185  # 1480 / 8 = 185
    assert len(frags[2].payload) == 1020
    assert frags[2].mf is False and frags[2].offset == 370 # (1480 + 1480) / 8 = 370
    print("    [PASS] 8-byte offset alignment and MF flags mathematically verified.")

    # 3. Simulate Reassembly at Destination Host
    print("\n[3] Simulating Destination Host Reassembly...")
    # Shuffle fragment arrival order to simulate out-of-order network routing
    shuffled_frags = [frags[2], frags[0], frags[1]]
    recovered_data = IPv4Reassembler.reassemble(shuffled_frags)

    assert recovered_data == original_data, "Validation Failure: Reassembled data does not match original payload!"
    print(f"    Successfully reconstructed {len(recovered_data)} bytes without loss.")
    print("    [PASS] Out-of-order reassembly completed with 100% byte fidelity.")

    # 4. Test PMTUD Behavior with DF=1
    print("\n[4] Testing Path MTU Discovery constraint (DF=1)...")
    try:
        IPv4FragmentationRouter.fragment(ident=packet_id, payload=original_data, mtu=link_mtu, df_flag=True)
        assert False, "Should have thrown ICMP Fragmentation Needed error!"
    except RuntimeError as e:
        print(f"    Router Response: {e}")
        print("    [PASS] Router correctly rejected oversize packet and triggered ICMP Type 3 Code 4.")

    print("\n" + "=" * 60)
    print("ALL DAY 07 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)
