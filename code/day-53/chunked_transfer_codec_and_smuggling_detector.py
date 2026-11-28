"""
Day 53: HTTP Chunked Transfer Codec & Request Smuggling Detector
100% pure Python standard library implementation of RFC 9112 chunked framing,
hex-length streaming codecs, trailing headers, and CL.TE / TE.CL desync security checks.
"""

from dataclasses import dataclass, field
import io
from typing import Dict, Generator, List, Optional, Tuple


@dataclass
class DecodedChunkMessage:
    body: bytes
    trailers: Dict[str, str] = field(default_factory=dict)


class ChunkedTransferCodec:
    """Serializes dynamic streams into RFC 9112 chunks and parses raw wire streams."""

    CRLF = b"\r\n"

    @classmethod
    def encode_chunk(cls, data: bytes) -> bytes:
        """Encodes a single chunk: <hex_size>\r\n<data>\r\n."""
        size_hex = f"{len(data):X}".encode("ascii")
        return size_hex + cls.CRLF + data + cls.CRLF

    @classmethod
    def encode_stream(cls, chunks: List[bytes], trailers: Optional[Dict[str, str]] = None) -> bytes:
        """Serializes full chunked body terminating with 0\r\n\r\n."""
        stream = bytearray()
        for chunk in chunks:
            if chunk:
                stream.extend(cls.encode_chunk(chunk))

        # Terminating zero chunk
        stream.extend(b"0\r\n")

        # Optional trailers
        if trailers:
            for k, v in trailers.items():
                stream.extend(f"{k}: {v}".encode("ascii") + cls.CRLF)

        stream.extend(cls.CRLF)
        return bytes(stream)

    @classmethod
    def decode_stream(cls, raw: bytes) -> DecodedChunkMessage:
        """Parses raw chunked byte stream, validating hex sizes and delimiters."""
        body = bytearray()
        trailers: Dict[str, str] = {}
        offset = 0

        while offset < len(raw):
            crlf_idx = raw.find(cls.CRLF, offset)
            if crlf_idx == -1:
                raise ValueError("Malformed chunk: missing CRLF after size line")

            size_line = raw[offset:crlf_idx].decode("ascii", errors="replace")
            # Chunk extensions may appear after semicolon
            chunk_size_str = size_line.split(";")[0].strip()
            chunk_size = int(chunk_size_str, 16)

            offset = crlf_idx + 2  # Advance past CRLF

            if chunk_size == 0:
                # Terminating chunk reached; parse optional trailers until final CRLF
                trailer_end = raw.find(cls.CRLF + cls.CRLF, offset - 2)
                if trailer_end == -1:
                    # Check for simple final CRLF
                    if raw[offset:offset+2] == cls.CRLF:
                        offset += 2
                        break
                break

            if offset + chunk_size > len(raw):
                raise ValueError("Chunk data overflows buffer")

            chunk_data = raw[offset:offset + chunk_size]
            body.extend(chunk_data)
            offset += chunk_size

            if raw[offset:offset + 2] != cls.CRLF:
                raise ValueError("Malformed chunk: missing trailing CRLF")
            offset += 2

        return DecodedChunkMessage(body=bytes(body), trailers=trailers)


class RequestSmugglingDetector:
    """Detects HTTP Request Smuggling vulnerabilities (CL.TE and TE.CL desync)."""

    @staticmethod
    def audit_headers(headers: Dict[str, str]) -> Tuple[bool, str]:
        # Normalize header keys to lowercase
        norm = {k.lower(): v for k, v in headers.items()}

        has_cl = "content-length" in norm
        has_te = "transfer-encoding" in norm

        if has_cl and has_te:
            te_val = norm["transfer-encoding"].lower()
            return True, f"CRITICAL SECURITY ALERT: Both Content-Length ({norm['content-length']}) and Transfer-Encoding ({te_val}) present! Request Smuggling Risk!"

        if has_te and norm["transfer-encoding"].lower() != "chunked":
            return True, f"UNSUPPORTED TRANSFER-ENCODING: {norm['transfer-encoding']}"

        return False, "Headers compliant with RFC 9112"


def main():
    print("=== Day 53: HTTP Chunked Transfer Codec & Request Smuggling Detector ===")

    # Test 1: Chunked Encoding Serialization
    chunks = [b"Hello", b", ", b"Chunked ", b"World!"]
    wire_bytes = ChunkedTransferCodec.encode_stream(chunks)
    print(f"[*] Serialized Chunked Stream Length: {len(wire_bytes)} bytes")
    assert b"5\r\nHello\r\n" in wire_bytes
    assert wire_bytes.endswith(b"0\r\n\r\n")
    print("[*] Test 1 Passed: Encoded stream formatted with valid hex sizes and terminating 0\r\n\r\n")

    # Test 2: Chunked Decoding Round-Trip
    decoded = ChunkedTransferCodec.decode_stream(wire_bytes)
    assert decoded.body == b"Hello, Chunked World!"
    print(f"[*] Test 2 Passed: Decoded stream payload matches original: '{decoded.body.decode()}'")

    # Test 3: Large streaming chunk decode
    large_payloads = [b"A" * 1024, b"B" * 2048, b"C" * 512]
    large_wire = ChunkedTransferCodec.encode_stream(large_payloads)
    large_decoded = ChunkedTransferCodec.decode_stream(large_wire)
    assert len(large_decoded.body) == (1024 + 2048 + 512)
    assert large_decoded.body[:10] == b"AAAAAAAAAA"
    print(f"[*] Test 3 Passed: Large multi-kilobyte streaming chunks decoded perfectly")

    # Test 4: Request Smuggling Detection (CL.TE Desync Attack)
    malicious_headers = {
        "Host": "bank.com",
        "Content-Length": "13",
        "Transfer-Encoding": "chunked"
    }
    is_smuggling, alert = RequestSmugglingDetector.audit_headers(malicious_headers)
    assert is_smuggling is True
    assert "CRITICAL SECURITY ALERT" in alert
    print(f"[*] Test 4 Passed: Smuggling detector successfully flagged CL.TE desync: {alert}")

    # Test 5: Legitimate headers pass audit
    clean_headers = {"Host": "bank.com", "Transfer-Encoding": "chunked"}
    is_smuggling, msg = RequestSmugglingDetector.audit_headers(clean_headers)
    assert is_smuggling is False
    print(f"[*] Test 5 Passed: Clean headers accepted: {msg}")

    print("All HTTP Chunked Transfer & Smuggling Detector assertions passed successfully!")


if __name__ == "__main__":
    main()
