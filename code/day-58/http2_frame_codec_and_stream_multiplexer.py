"""
Day 58: HTTP/2 Binary Framing, Stream Multiplexing, and Flow Control Engine
Pure Python standard library implementation of RFC 7540.
Implements the 9-byte frame header, frame serialization, stream state transitions,
and multiplexed stream credit management (flow control).
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple


class Http2FrameType(IntEnum):
    """RFC 7540 Frame Types."""
    DATA = 0x0
    HEADERS = 0x1
    PRIORITY = 0x2
    RST_STREAM = 0x3
    SETTINGS = 0x4
    PUSH_PROMISE = 0x5
    PING = 0x6
    GOAWAY = 0x7
    WINDOW_UPDATE = 0x8
    CONTINUATION = 0x9


class StreamState(IntEnum):
    """HTTP/2 Stream State Machine."""
    IDLE = 0
    RESERVED = 1
    OPEN = 2
    HALF_CLOSED_LOCAL = 3
    HALF_CLOSED_REMOTE = 4
    CLOSED = 5


@dataclass
class Http2Frame:
    """Represents a 9-byte header + payload HTTP/2 frame."""
    length: int
    frame_type: Http2FrameType
    flags: int
    stream_id: int
    payload: bytes


class Http2FrameCodec:
    """Encodes and decodes RFC 7540 9-byte binary frame headers."""

    HEADER_SIZE = 9

    @classmethod
    def encode(cls, frame_type: Http2FrameType, flags: int, stream_id: int, payload: bytes) -> bytes:
        """
        Packs an HTTP/2 frame into wire format:
        - Length: 24 bits (3 bytes)
        - Type: 8 bits (1 byte)
        - Flags: 8 bits (1 byte)
        - R (1 bit reserved) + Stream ID (31 bits) (4 bytes)
        - Payload: N bytes
        """
        length = len(payload)
        if length > 0xFFFFFF:
            raise ValueError(f"Payload length exceeds 24-bit maximum: {length}")

        # Pack length (24-bit) as 3 bytes
        len_b = struct.pack("!I", length)[1:]  # slice off highest byte
        type_b = struct.pack("!B", int(frame_type))
        flags_b = struct.pack("!B", flags)
        stream_b = struct.pack("!I", stream_id & 0x7FFFFFFF)  # Clear R bit

        return len_b + type_b + flags_b + stream_b + payload

    @classmethod
    def decode(cls, data: bytes) -> Tuple[Http2Frame, int]:
        """
        Decodes raw bytes into Http2Frame.
        Returns (frame, total_bytes_consumed).
        """
        if len(data) < cls.HEADER_SIZE:
            raise ValueError("Buffer too short for 9-byte HTTP/2 frame header")

        length = int.from_bytes(data[0:3], byteorder="big")
        frame_type = Http2FrameType(data[3])
        flags = data[4]
        stream_id = struct.unpack("!I", data[5:9])[0] & 0x7FFFFFFF

        total_frame_len = cls.HEADER_SIZE + length
        if len(data) < total_frame_len:
            raise ValueError(f"Incomplete payload: expected {length} bytes, got {len(data) - cls.HEADER_SIZE}")

        payload = data[cls.HEADER_SIZE:total_frame_len]
        return Http2Frame(length, frame_type, flags, stream_id, payload), total_frame_len


@dataclass
class Http2Stream:
    """Tracks state and flow-control window for an individual HTTP/2 stream."""
    stream_id: int
    state: StreamState = StreamState.IDLE
    window_size: int = 65535  # Default initial window size 64KB - 1
    received_data: bytearray = field(default_factory=bytearray)


class Http2StreamMultiplexer:
    """Manages multiplexed concurrent streams over a single connection."""

    def __init__(self, initial_window: int = 65535):
        self.initial_window = initial_window
        self.streams: Dict[int, Http2Stream] = {}
        self.connection_window = initial_window

    def get_or_create_stream(self, stream_id: int) -> Http2Stream:
        """Retrieves or instantiates a new stream."""
        if stream_id not in self.streams:
            self.streams[stream_id] = Http2Stream(stream_id=stream_id, window_size=self.initial_window)
        return self.streams[stream_id]

    def process_incoming_frame(self, frame: Http2Frame) -> None:
        """Processes an incoming frame, updates stream states and flow control."""
        if frame.stream_id == 0:
            # Connection-level frames (SETTINGS, WINDOW_UPDATE, PING)
            if frame.frame_type == Http2FrameType.WINDOW_UPDATE:
                increment = struct.unpack("!I", frame.payload)[0] & 0x7FFFFFFF
                self.connection_window += increment
            return

        stream = self.get_or_create_stream(frame.stream_id)

        if frame.frame_type == Http2FrameType.HEADERS:
            # Transition from IDLE to OPEN
            if stream.state == StreamState.IDLE:
                stream.state = StreamState.OPEN
            # Check END_STREAM flag (0x01)
            if frame.flags & 0x01:
                stream.state = StreamState.HALF_CLOSED_REMOTE

        elif frame.frame_type == Http2FrameType.DATA:
            if stream.state not in (StreamState.OPEN, StreamState.HALF_CLOSED_LOCAL):
                raise ValueError(f"DATA frame received on invalid stream state: {stream.state}")

            # Deduct from stream and connection flow control windows
            stream.window_size -= len(frame.payload)
            self.connection_window -= len(frame.payload)
            stream.received_data.extend(frame.payload)

            # Check END_STREAM flag (0x01)
            if frame.flags & 0x01:
                stream.state = StreamState.CLOSED if stream.state == StreamState.HALF_CLOSED_LOCAL else StreamState.HALF_CLOSED_REMOTE

        elif frame.frame_type == Http2FrameType.RST_STREAM:
            stream.state = StreamState.CLOSED


def main():
    print("=================================================================")
    print("Testing Day 58: HTTP/2 Binary Framing & Multiplexer")
    print("=================================================================")

    # Test 1: 9-Byte Header Serialization
    payload_sample = b"<html><body>Hello HTTP/2!</body></html>"
    raw_frame = Http2FrameCodec.encode(
        frame_type=Http2FrameType.DATA,
        flags=0x01,  # END_STREAM
        stream_id=1,
        payload=payload_sample
    )
    assert len(raw_frame) == 9 + len(payload_sample)
    # Check 24-bit length
    assert int.from_bytes(raw_frame[0:3], "big") == len(payload_sample)
    # Check type
    assert raw_frame[3] == 0x00  # DATA
    # Check flags
    assert raw_frame[4] == 0x01
    # Check stream ID
    assert struct.unpack("!I", raw_frame[5:9])[0] == 1
    print(f"[PASS] HTTP/2 9-byte header successfully constructed ({len(raw_frame)} total bytes).")

    # Test 2: Frame Deserialization
    decoded_frame, consumed = Http2FrameCodec.decode(raw_frame)
    assert consumed == len(raw_frame)
    assert decoded_frame.frame_type == Http2FrameType.DATA
    assert decoded_frame.stream_id == 1
    assert decoded_frame.flags == 0x01
    assert decoded_frame.payload == payload_sample
    print("[PASS] HTTP/2 frame decoding verified.")

    # Test 3: Multiplexing two concurrent streams
    mux = Http2StreamMultiplexer()

    # Stream 1: GET /index.html
    h1 = Http2FrameCodec.encode(Http2FrameType.HEADERS, 0x04, 1, b"HEADERS_PAYLOAD_1")  # END_HEADERS
    # Stream 3: GET /styles.css
    h3 = Http2FrameCodec.encode(Http2FrameType.HEADERS, 0x04, 3, b"HEADERS_PAYLOAD_3")

    f1, _ = Http2FrameCodec.decode(h1)
    f3, _ = Http2FrameCodec.decode(h3)
    mux.process_incoming_frame(f1)
    mux.process_incoming_frame(f3)

    assert mux.streams[1].state == StreamState.OPEN
    assert mux.streams[3].state == StreamState.OPEN
    print("[PASS] Streams 1 and 3 opened concurrently on single multiplexer.")

    # Interleaved Data chunks on Stream 1 and Stream 3
    d1 = Http2FrameCodec.encode(Http2FrameType.DATA, 0x00, 1, b"chunk1_stream1")
    d3 = Http2FrameCodec.encode(Http2FrameType.DATA, 0x00, 3, b"chunk1_stream3")
    d1_end = Http2FrameCodec.encode(Http2FrameType.DATA, 0x01, 1, b"_final_stream1")

    f_d1, _ = Http2FrameCodec.decode(d1)
    f_d3, _ = Http2FrameCodec.decode(d3)
    f_d1_end, _ = Http2FrameCodec.decode(d1_end)

    mux.process_incoming_frame(f_d1)
    mux.process_incoming_frame(f_d3)
    mux.process_incoming_frame(f_d1_end)

    assert bytes(mux.streams[1].received_data) == b"chunk1_stream1_final_stream1"
    assert bytes(mux.streams[3].received_data) == b"chunk1_stream3"
    assert mux.streams[1].state == StreamState.HALF_CLOSED_REMOTE
    assert mux.streams[3].state == StreamState.OPEN
    print("[PASS] Multiplexed interleaved data frames reassembled without cross-stream contamination.")

    # Verify flow control window reduction
    consumed_bytes = len(b"chunk1_stream1") + len(b"chunk1_stream3") + len(b"_final_stream1")
    assert mux.connection_window == 65535 - consumed_bytes
    print(f"[PASS] Flow control window correctly decremented: {mux.connection_window} credits remaining.")

    print("\nALL DAY 58 HTTP/2 MULTIPLEXER TESTS PASSED (100% SUCCESS)!")


if __name__ == "__main__":
    main()
