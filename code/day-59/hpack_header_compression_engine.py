"""
Day 59: HPACK Header Compression Engine for HTTP/2
Pure Python standard library implementation of RFC 7541.
Implements the 61-entry static table, dynamic sliding window FIFO table,
and variable-length integer encoding/decoding.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# RFC 7541 Appendix A: Static Table Definition (first 61 standard entries)
STATIC_TABLE: List[Tuple[str, str]] = [
    (":authority", ""),
    (":method", "GET"),
    (":method", "POST"),
    (":path", "/"),
    (":path", "/index.html"),
    (":scheme", "http"),
    (":scheme", "https"),
    (":status", "200"),
    (":status", "204"),
    (":status", "206"),
    (":status", "304"),
    (":status", "400"),
    (":status", "404"),
    (":status", "500"),
    ("accept-charset", ""),
    ("accept-encoding", "gzip, deflate"),
    ("accept-language", ""),
    ("accept-ranges", ""),
    ("accept", ""),
    ("access-control-allow-origin", ""),
    ("age", ""),
    ("allow", ""),
    ("authorization", ""),
    ("cache-control", ""),
    ("content-disposition", ""),
    ("content-encoding", ""),
    ("content-language", ""),
    ("content-length", ""),
    ("content-location", ""),
    ("content-range", ""),
    ("content-type", ""),
    ("cookie", ""),
    ("date", ""),
    ("etag", ""),
    ("expect", ""),
    ("expires", ""),
    ("from", ""),
    ("host", ""),
    ("if-match", ""),
    ("if-modified-since", ""),
    ("if-none-match", ""),
    ("if-range", ""),
    ("if-unmodified-since", ""),
    ("last-modified", ""),
    ("link", ""),
    ("location", ""),
    ("max-forwards", ""),
    ("proxy-authenticate", ""),
    ("proxy-authorization", ""),
    ("range", ""),
    ("referer", ""),
    ("refresh", ""),
    ("retry-after", ""),
    ("server", ""),
    ("set-cookie", ""),
    ("strict-transport-security", ""),
    ("transfer-encoding", ""),
    ("user-agent", ""),
    ("vary", ""),
    ("via", ""),
    ("www-authenticate", "")
]


class HpackIntegerCodec:
    """RFC 7541 Section 5.1: Variable-Length Integer Representation."""

    @staticmethod
    def encode(value: int, prefix_bits: int) -> bytes:
        """Encodes an integer using an N-bit prefix."""
        max_prefix = (1 << prefix_bits) - 1
        if value < max_prefix:
            return bytes([value])

        result = bytearray([max_prefix])
        value -= max_prefix
        while value >= 128:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)

    @staticmethod
    def decode(data: bytes, prefix_bits: int, offset: int = 0) -> Tuple[int, int]:
        """
        Decodes an integer from data starting at offset.
        Returns (decoded_integer, bytes_consumed).
        """
        max_prefix = (1 << prefix_bits) - 1
        first_byte = data[offset] & max_prefix
        consumed = 1

        if first_byte < max_prefix:
            return first_byte, consumed

        value = first_byte
        m = 0
        while True:
            if offset + consumed >= len(data):
                raise ValueError("Incomplete variable-length integer buffer")
            b = data[offset + consumed]
            consumed += 1
            value += (b & 0x7F) << m
            m += 7
            if not (b & 0x80):
                break

        return value, consumed


class HpackDynamicTable:
    """RFC 7541 Dynamic Table with FIFO eviction and byte-size tracking."""

    ENTRY_OVERHEAD = 32  # RFC 7541 Section 4.1 adds 32 bytes overhead per entry

    def __init__(self, max_size_bytes: int = 4096):
        self.max_size = max_size_bytes
        self.current_size = 0
        self.entries: List[Tuple[str, str]] = []

    def add(self, name: str, value: str) -> None:
        """Inserts an entry at index 0, evicting oldest entries to obey max_size."""
        entry_size = len(name.encode("utf-8")) + len(value.encode("utf-8")) + self.ENTRY_OVERHEAD
        if entry_size > self.max_size:
            # Entry exceeds entire table capacity; purge table
            self.entries.clear()
            self.current_size = 0
            return

        while self.current_size + entry_size > self.max_size and self.entries:
            evicted_name, evicted_val = self.entries.pop()
            evicted_size = len(evicted_name.encode("utf-8")) + len(evicted_val.encode("utf-8")) + self.ENTRY_OVERHEAD
            self.current_size -= evicted_size

        self.entries.insert(0, (name, value))
        self.current_size += entry_size

    def get(self, index: int) -> Tuple[str, str]:
        """1-based dynamic index lookup."""
        if 1 <= index <= len(self.entries):
            return self.entries[index - 1]
        raise IndexError(f"Dynamic table index {index} out of range (1..{len(self.entries)})")


class HpackCodec:
    """Encodes and decodes HTTP headers using HPACK tables."""

    def __init__(self, max_dynamic_table_size: int = 4096):
        self.dynamic_table = HpackDynamicTable(max_dynamic_table_size)

    def lookup_index(self, name: str, value: str) -> Tuple[Optional[int], bool]:
        """
        Looks up a name and value across static and dynamic tables.
        Returns (index, is_exact_match).
        """
        # 1. Search Static Table (1-based: 1..61)
        name_match_idx = None
        for i, (s_name, s_val) in enumerate(STATIC_TABLE, start=1):
            if s_name == name:
                if s_val == value:
                    return i, True
                if name_match_idx is None:
                    name_match_idx = i

        # 2. Search Dynamic Table (62..)
        offset = len(STATIC_TABLE)
        for j, (d_name, d_val) in enumerate(self.dynamic_table.entries, start=1):
            if d_name == name:
                if d_val == value:
                    return offset + j, True
                if name_match_idx is None:
                    name_match_idx = offset + j

        return name_match_idx, False

    def encode_header(self, name: str, value: str) -> bytes:
        """Encodes a single header field into HPACK wire representation."""
        idx, exact = self.lookup_index(name, value)

        if exact and idx is not None:
            # Indexed Header Field: bit pattern 1xxxxxxx (7-bit prefix)
            prefix = HpackIntegerCodec.encode(idx, 7)
            first_byte = bytes([prefix[0] | 0x80])
            return first_byte + prefix[1:]

        # Literal with Incremental Indexing: bit pattern 01xxxxxx (6-bit prefix)
        out = bytearray()
        if idx is not None:
            # Name indexed, literal value
            prefix = HpackIntegerCodec.encode(idx, 6)
            out.append(prefix[0] | 0x40)
            out.extend(prefix[1:])
        else:
            # New name and new value: 01000000 (0x40) followed by name string
            out.append(0x40)
            name_bytes = name.encode("utf-8")
            out.extend(HpackIntegerCodec.encode(len(name_bytes), 7))
            out.extend(name_bytes)

        # Append value string
        val_bytes = value.encode("utf-8")
        out.extend(HpackIntegerCodec.encode(len(val_bytes), 7))
        out.extend(val_bytes)

        # Update dynamic table
        self.dynamic_table.add(name, value)
        return bytes(out)

    def decode_header(self, data: bytes, offset: int = 0) -> Tuple[str, str, int]:
        """
        Decodes a single header field from wire representation.
        Returns (name, value, bytes_consumed).
        """
        first = data[offset]

        if first & 0x80:
            # Indexed Header Field (7-bit prefix)
            idx, consumed = HpackIntegerCodec.decode(data, 7, offset)
            if idx <= len(STATIC_TABLE):
                name, val = STATIC_TABLE[idx - 1]
            else:
                dyn_idx = idx - len(STATIC_TABLE)
                name, val = self.dynamic_table.get(dyn_idx)
            return name, val, consumed

        elif first & 0x40:
            # Literal Header with Incremental Indexing (6-bit prefix)
            idx, consumed = HpackIntegerCodec.decode(data, 6, offset)
            curr = offset + consumed

            if idx != 0:
                # Name comes from index
                if idx <= len(STATIC_TABLE):
                    name, _ = STATIC_TABLE[idx - 1]
                else:
                    name, _ = self.dynamic_table.get(idx - len(STATIC_TABLE))
            else:
                # Literal name
                name_len, c_len = HpackIntegerCodec.decode(data, 7, curr)
                curr += c_len
                name = data[curr:curr+name_len].decode("utf-8")
                curr += name_len

            val_len, c_vlen = HpackIntegerCodec.decode(data, 7, curr)
            curr += c_vlen
            val = data[curr:curr+val_len].decode("utf-8")
            curr += val_len

            # Insert into dynamic table
            self.dynamic_table.add(name, val)
            return name, val, (curr - offset)

        else:
            raise NotImplementedError("Literal without indexing or Huffman coding not in scope")


def main():
    print("=================================================================")
    print("Testing Day 59: HPACK Header Compression Engine")
    print("=================================================================")

    # Test 1: Variable-Length Integer Encoding & Decoding (RFC 7541 tests)
    # Value 10 with 5-bit prefix (fits in prefix)
    enc1 = HpackIntegerCodec.encode(10, 5)
    dec1, c1 = HpackIntegerCodec.decode(enc1, 5)
    assert dec1 == 10 and c1 == 1
    print(f"[PASS] Integer 10 (5-bit prefix) encoded as {enc1.hex()} and verified.")

    # Value 1337 with 5-bit prefix (exceeds prefix)
    enc2 = HpackIntegerCodec.encode(1337, 5)
    dec2, c2 = HpackIntegerCodec.decode(enc2, 5)
    assert dec2 == 1337
    print(f"[PASS] Integer 1337 (5-bit prefix) encoded as {enc2.hex()} ({c2} bytes) and verified.")

    # Test 2: Indexed Header Field from Static Table (:method = GET -> Index 2)
    codec = HpackCodec()
    enc_get = codec.encode_header(":method", "GET")
    assert enc_get == b"\x82"  # 0x80 | 2 = 0x82 (1 byte!)
    dec_name, dec_val, consumed = codec.decode_header(enc_get)
    assert dec_name == ":method" and dec_val == "GET" and consumed == 1
    print(f"[PASS] Static table index 2 (:method: GET) compressed into single byte 0x82.")

    # Test 3: Incremental Indexing of Custom Header
    # First transmission: Literal with indexing
    enc_custom = codec.encode_header("custom-auth-token", "secret_xyz_12345")
    dec_c_name, dec_c_val, c_bytes = codec.decode_header(enc_custom)
    assert dec_c_name == "custom-auth-token"
    assert dec_c_val == "secret_xyz_12345"
    print(f"[PASS] Custom header incrementally indexed into dynamic table ({c_bytes} bytes).")

    # Second transmission: Must now resolve to an Indexed Header Field in the dynamic table!
    enc_custom_repeat = codec.encode_header("custom-auth-token", "secret_xyz_12345")
    assert enc_custom_repeat[0] & 0x80, "Must be encoded as an indexed header field (starts with bit 1)"
    dec_r_name, dec_r_val, r_bytes = codec.decode_header(enc_custom_repeat)
    assert dec_r_name == "custom-auth-token"
    assert dec_r_val == "secret_xyz_12345"
    assert r_bytes < c_bytes, "Repeated header must be significantly smaller due to indexing"
    print(f"[PASS] Repeated header compressed from {c_bytes} bytes down to {r_bytes} byte(s) via dynamic table.")

    # Test 4: Dynamic Table FIFO Eviction
    tiny_codec = HpackCodec(max_dynamic_table_size=120)  # small capacity
    tiny_codec.encode_header("header-a", "value-a")
    tiny_codec.encode_header("header-b", "value-b")
    tiny_codec.encode_header("header-c", "value-c")
    # Table should have evicted oldest entries to maintain 120 byte ceiling
    assert tiny_codec.dynamic_table.current_size <= 120
    print(f"[PASS] Dynamic table FIFO eviction enforced: size is {tiny_codec.dynamic_table.current_size} <= 120 bytes.")

    print("\nALL DAY 59 HPACK TESTS PASSED (100% SUCCESS)!")


if __name__ == "__main__":
    main()
