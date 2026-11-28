"""
Day 57: WebSocket Protocol: Upgrade Handshake, Binary Framing, and Unmasking Engine
Pure Python standard library implementation of RFC 6455.
Implements the SHA-1 + Base64 handshake verification, binary frame serialization,
and the 4-byte XOR client unmasking algorithm.
"""

import base64
import hashlib
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple


class WebSocketOpcode(IntEnum):
    """RFC 6455 4-bit Opcode constants."""
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


# RFC 6455 Magic GUID for handshake computation
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def compute_accept_key(client_key: str) -> str:
    """
    Computes Sec-WebSocket-Accept from Sec-WebSocket-Key.
    Algorithm: Base64(SHA1(client_key + GUID))
    """
    concat = client_key.strip() + WEBSOCKET_GUID
    digest = hashlib.sha1(concat.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8")


@dataclass
class WebSocketFrame:
    """Represents a decoded or to-be-encoded WebSocket frame."""
    fin: bool
    opcode: WebSocketOpcode
    masked: bool
    payload: bytes
    masking_key: Optional[bytes] = None  # 4 bytes if masked


class WebSocketFrameCodec:
    """Encodes and decodes RFC 6455 binary frames."""

    @staticmethod
    def encode(frame: WebSocketFrame) -> bytes:
        """Serializes a WebSocketFrame into raw binary wire format."""
        b0 = (0x80 if frame.fin else 0x00) | (frame.opcode & 0x0F)
        mask_bit = 0x80 if frame.masked else 0x00
        length = len(frame.payload)

        header = bytearray()
        header.append(b0)

        if length <= 125:
            header.append(mask_bit | length)
        elif length <= 65535:
            header.append(mask_bit | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(mask_bit | 127)
            header.extend(struct.pack("!Q", length))

        if frame.masked:
            if not frame.masking_key or len(frame.masking_key) != 4:
                raise ValueError("Masked frame requires exactly 4 bytes masking key")
            header.extend(frame.masking_key)
            # Mask payload using cyclic XOR: payload[i] ^ mask[i % 4]
            masked_payload = bytes(b ^ frame.masking_key[i % 4] for i, b in enumerate(frame.payload))
            return bytes(header) + masked_payload
        else:
            return bytes(header) + frame.payload

    @staticmethod
    def decode(data: bytes) -> Tuple[WebSocketFrame, int]:
        """
        Parses raw binary bytes into a WebSocketFrame.
        Returns (frame, total_bytes_consumed).
        """
        if len(data) < 2:
            raise ValueError("Incomplete frame: header requires at least 2 bytes")

        b0 = data[0]
        b1 = data[1]

        fin = bool(b0 & 0x80)
        opcode = WebSocketOpcode(b0 & 0x0F)
        masked = bool(b1 & 0x80)
        initial_len = b1 & 0x7F

        offset = 2
        if initial_len <= 125:
            payload_len = initial_len
        elif initial_len == 126:
            if len(data) < offset + 2:
                raise ValueError("Incomplete frame: missing 16-bit extended length")
            payload_len = struct.unpack("!H", data[offset:offset+2])[0]
            offset += 2
        else:  # 127
            if len(data) < offset + 8:
                raise ValueError("Incomplete frame: missing 64-bit extended length")
            payload_len = struct.unpack("!Q", data[offset:offset+8])[0]
            offset += 8

        masking_key = None
        if masked:
            if len(data) < offset + 4:
                raise ValueError("Incomplete frame: missing 4-byte masking key")
            masking_key = data[offset:offset+4]
            offset += 4

        if len(data) < offset + payload_len:
            raise ValueError(f"Incomplete frame: expected {payload_len} payload bytes, got {len(data) - offset}")

        raw_payload = data[offset:offset+payload_len]
        total_consumed = offset + payload_len

        if masked:
            # RFC 6455 XOR unmasking: unmasked[i] = raw_payload[i] ^ masking_key[i % 4]
            unmasked_payload = bytes(b ^ masking_key[i % 4] for i, b in enumerate(raw_payload))
        else:
            unmasked_payload = raw_payload

        return WebSocketFrame(
            fin=fin,
            opcode=opcode,
            masked=masked,
            payload=unmasked_payload,
            masking_key=masking_key
        ), total_consumed


def main():
    print("=================================================================")
    print("Testing Day 57: WebSocket Frame Codec and Unmasker")
    print("=================================================================")

    # Test 1: Handshake key calculation
    client_key = "dGhlIHNhbXBsZSBub25jZQ=="
    accept_key = compute_accept_key(client_key)
    expected_accept = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
    assert accept_key == expected_accept, f"Handshake failed: got {accept_key}, expected {expected_accept}"
    print(f"[PASS] Handshake Sec-WebSocket-Accept verified: {accept_key}")

    # Test 2: Unmasked text frame (Server -> Client)
    msg = "Hello, WebSocket!"
    text_frame = WebSocketFrame(
        fin=True,
        opcode=WebSocketOpcode.TEXT,
        masked=False,
        payload=msg.encode("utf-8")
    )
    encoded = WebSocketFrameCodec.encode(text_frame)
    decoded, consumed = WebSocketFrameCodec.decode(encoded)
    assert consumed == len(encoded)
    assert decoded.opcode == WebSocketOpcode.TEXT
    assert decoded.fin is True
    assert decoded.payload.decode("utf-8") == msg
    print(f"[PASS] Server->Client unmasked text frame encoded and decoded ({len(encoded)} bytes)")

    # Test 3: Masked client frame (Client -> Server)
    mask = b"\x1a\x2b\x3c\x4d"
    client_frame = WebSocketFrame(
        fin=True,
        opcode=WebSocketOpcode.TEXT,
        masked=True,
        payload=msg.encode("utf-8"),
        masking_key=mask
    )
    encoded_masked = WebSocketFrameCodec.encode(client_frame)
    # Verify wire bytes: wire payload must not equal raw message due to XOR mask
    wire_payload = encoded_masked[6:]  # 2 header + 4 mask bytes
    assert wire_payload != msg.encode("utf-8"), "Wire payload must be scrambled by XOR mask"

    # Decode and unmask
    decoded_client, _ = WebSocketFrameCodec.decode(encoded_masked)
    assert decoded_client.payload.decode("utf-8") == msg
    assert decoded_client.masked is True
    assert decoded_client.masking_key == mask
    print("[PASS] Client->Server masked frame successfully verified and XOR unmasked.")

    # Test 4: Extended 16-bit payload length (e.g., 500 bytes)
    large_payload = b"X" * 500
    large_frame = WebSocketFrame(
        fin=True,
        opcode=WebSocketOpcode.BINARY,
        masked=False,
        payload=large_payload
    )
    encoded_large = WebSocketFrameCodec.encode(large_frame)
    assert encoded_large[1] == 126, "Payload length 500 should set length indicator to 126"
    decoded_large, consumed_large = WebSocketFrameCodec.decode(encoded_large)
    assert decoded_large.payload == large_payload
    assert consumed_large == len(encoded_large)
    print(f"[PASS] 16-bit extended length frame (500 bytes) verified.")

    # Test 5: Control frame (PING / PONG)
    ping_payload = b"heartbeat_token_99"
    ping_frame = WebSocketFrame(
        fin=True,
        opcode=WebSocketOpcode.PING,
        masked=False,
        payload=ping_payload
    )
    encoded_ping = WebSocketFrameCodec.encode(ping_frame)
    decoded_ping, _ = WebSocketFrameCodec.decode(encoded_ping)
    assert decoded_ping.opcode == WebSocketOpcode.PING
    assert decoded_ping.payload == ping_payload
    print("[PASS] Control frame PING successfully encoded and decoded.")

    print("\nALL DAY 57 WEBSOCKET CODEC TESTS PASSED (100% SUCCESS)!")


if __name__ == "__main__":
    main()
