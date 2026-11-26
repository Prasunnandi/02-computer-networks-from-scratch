#!/usr/bin/env python3
"""
Day 40 Lab: Encrypted DNS Simulator (DNS-over-TLS & DNS-over-HTTPS)
Implements:
1. DNS-over-TLS (RFC 7858): 2-byte length-delimited stream framing over TLS (port 853).
2. DNS-over-HTTPS (RFC 8484): HTTP/2 POST wire format and GET base64url encoding.
Uses Python standard library only.
"""

import base64
import struct
from typing import Tuple, Dict


class EncryptedDNSCodec:
    """Encodes and decodes encrypted DNS payloads for DoT and DoH."""

    # ----------------------------------------------------
    # 1. DNS-over-TLS (DoT - RFC 7858)
    # ----------------------------------------------------
    @staticmethod
    def frame_dot_message(dns_wire_bytes: bytes) -> bytes:
        """Prepends 2-byte big-endian length prefix for TLS byte streams."""
        length = len(dns_wire_bytes)
        if length > 65535:
            raise ValueError("DNS message exceeds 65535 bytes")
        return struct.pack("!H", length) + dns_wire_bytes

    @staticmethod
    def unframe_dot_stream(stream_buffer: bytes) -> Tuple[Optional_bytes := bytes, int]:
        """Extracts complete DNS message from stream buffer. Returns (msg, bytes_consumed)."""
        if len(stream_buffer) < 2:
            return b"", 0
        expected_len = struct.unpack("!H", stream_buffer[:2])[0]
        if len(stream_buffer) < 2 + expected_len:
            return b"", 0  # Incomplete message in buffer
        msg = stream_buffer[2:2 + expected_len]
        return msg, 2 + expected_len

    # ----------------------------------------------------
    # 2. DNS-over-HTTPS (DoH - RFC 8484)
    # ----------------------------------------------------
    @staticmethod
    def encode_doh_get_url(base_url: str, dns_wire_bytes: bytes) -> str:
        """Encodes DNS wire message into HTTP GET query parameter using base64url without padding."""
        # RFC 8484 Section 4.1: base64url encoding without trailing '='
        encoded_dns = base64.urlsafe_b64encode(dns_wire_bytes).decode('ascii').rstrip('=')
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}dns={encoded_dns}"

    @staticmethod
    def decode_doh_get_param(base64url_param: str) -> bytes:
        """Decodes base64url query parameter back to raw DNS binary wire bytes."""
        # Add required padding back for Python base64 decoder
        padded = base64url_param + '=' * ((4 - len(base64url_param) % 4) % 4)
        return base64.urlsafe_b64decode(padded)

    @staticmethod
    def build_doh_post_headers(payload_length: int) -> Dict[str, str]:
        """Returns standard RFC 8484 HTTP headers for DoH POST request."""
        return {
            "Content-Type": "application/dns-message",
            "Accept": "application/dns-message",
            "Content-Length": str(payload_length)
        }


def main():
    print("====================================================")
    print("DAY 40: ENCRYPTED DNS (DoT & DoH CODEC)")
    print("====================================================")

    # Synthetic 12-byte DNS query header
    sample_dns_query = struct.pack("!HHHHHH", 0xABCD, 0x0100, 1, 0, 0, 0)

    # 1. Test DNS-over-TLS (DoT)
    dot_frame = EncryptedDNSCodec.frame_dot_message(sample_dns_query)
    assert len(dot_frame) == 14  # 2-byte header + 12-byte payload
    assert dot_frame[:2] == struct.pack("!H", 12)
    print("1. DNS-over-TLS (DoT):")
    print(f"   Original Size: {len(sample_dns_query)}B -> Framed Size: {len(dot_frame)}B")

    # Unframe stream
    extracted_msg, consumed = EncryptedDNSCodec.unframe_dot_stream(dot_frame)
    assert extracted_msg == sample_dns_query
    assert consumed == 14
    print("   [PASS] DoT stream framing & unframing verified with 100% fidelity.")

    # 2. Test DNS-over-HTTPS (DoH) GET Method
    base_endpoint = "mock://doh.internal.resolver/resolve"
    doh_url = EncryptedDNSCodec.encode_doh_get_url(base_endpoint, sample_dns_query)
    print("\n2. DNS-over-HTTPS (DoH) GET Request:")
    print(f"   URL: {doh_url}")
    assert "?dns=" in doh_url
    assert "=" not in doh_url.split("?dns=")[1]  # No padding per RFC 8484

    # Decode back from URL parameter
    param = doh_url.split("?dns=")[1]
    decoded_wire = EncryptedDNSCodec.decode_doh_get_param(param)
    assert decoded_wire == sample_dns_query
    print("   [PASS] DoH GET base64url roundtrip verified without padding.")

    # 3. Test DNS-over-HTTPS (DoH) POST Headers
    post_headers = EncryptedDNSCodec.build_doh_post_headers(len(sample_dns_query))
    assert post_headers["Content-Type"] == "application/dns-message"
    assert post_headers["Accept"] == "application/dns-message"
    print("\n3. DNS-over-HTTPS (DoH) POST Headers:")
    print(f"   Headers: {post_headers}")
    print("   [PASS] DoH POST binary MIME type verified (application/dns-message).")

    print("\n[VERIFIED] Encrypted DNS Codec passed all tests with 100% fidelity!")


if __name__ == "__main__":
    main()
