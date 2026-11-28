"""
Day 60: HTTP/3 and QUIC: UDP Transport, Connection IDs, and Independent Stream Demux
Pure Python standard library implementation of RFC 9000 (QUIC) and RFC 9114 (HTTP/3).
Implements QUIC packet encapsulation over UDP, Connection ID (CID) connection migration,
and independent stream demultiplexing to eliminate TCP Head-of-Line blocking.
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple


class QuicPacketType(IntEnum):
    """QUIC Packet Header Types."""
    INITIAL = 0x0
    ZERO_RTT = 0x1
    HANDSHAKE = 0x2
    RETRY = 0x3
    SHORT_HEADER_1RTT = 0x4  # Standard post-handshake data packet


@dataclass
class QuicStreamFrame:
    """Represents a STREAM frame carrying application data."""
    stream_id: int
    offset: int
    data: bytes
    fin: bool = False


@dataclass
class QuicPacket:
    """Represents a serialized or parsed QUIC packet."""
    packet_type: QuicPacketType
    dest_conn_id: bytes  # Connection ID (CID) allows seamless IP migration
    packet_number: int   # Monotonically increasing 32-bit packet sequence
    frames: List[QuicStreamFrame] = field(default_factory=list)


class QuicPacketCodec:
    """Encodes and decodes QUIC 1-RTT Short Header packets."""

    @classmethod
    def encode_1rtt_packet(cls, packet: QuicPacket) -> bytes:
        """
        Packs a Short Header (1-RTT) QUIC packet:
        - Header byte: [0 (fixed) | 1 (short header) | Spin (1b) | Key (1b) | Reserved (2b) | Packet Number Len (2b)]
        - Destination Connection ID: 8 bytes
        - Packet Number: 4 bytes (uint32)
        - Frames: [Stream ID (4B) | Offset (4B) | Length (2B) | FIN (1B) | Data]
        """
        buf = bytearray()
        # 0x43: Short header flag + 4-byte packet number indicator
        buf.append(0x43)
        if len(packet.dest_conn_id) != 8:
            raise ValueError("Destination Connection ID must be exactly 8 bytes")
        buf.extend(packet.dest_conn_id)
        buf.extend(struct.pack("!I", packet.packet_number))

        # Serialize stream frames
        for frame in packet.frames:
            buf.extend(struct.pack("!IIHB", frame.stream_id, frame.offset, len(frame.data), 1 if frame.fin else 0))
            buf.extend(frame.data)

        return bytes(buf)

    @classmethod
    def decode_1rtt_packet(cls, data: bytes) -> QuicPacket:
        """Parses a raw UDP packet into a QuicPacket object."""
        if len(data) < 13:
            raise ValueError("Packet too short for QUIC short header (minimum 13 bytes)")

        header_byte = data[0]
        if not (header_byte & 0x40):
            raise ValueError("Expected short header (bit 6 set)")

        dest_cid = data[1:9]
        packet_number = struct.unpack("!I", data[9:13])[0]
        curr = 13

        frames = []
        while curr + 11 <= len(data):
            stream_id, offset, data_len, fin_int = struct.unpack("!IIHB", data[curr:curr+11])
            curr += 11
            if curr + data_len > len(data):
                raise ValueError("Frame data truncated in UDP datagram")
            frame_data = data[curr:curr+data_len]
            curr += data_len
            frames.append(QuicStreamFrame(stream_id=stream_id, offset=offset, data=frame_data, fin=bool(fin_int)))

        return QuicPacket(
            packet_type=QuicPacketType.SHORT_HEADER_1RTT,
            dest_conn_id=dest_cid,
            packet_number=packet_number,
            frames=frames
        )


class QuicConnection:
    """Manages an active QUIC connection over UDP, supporting connection migration."""

    def __init__(self, connection_id: bytes):
        self.connection_id = connection_id
        self.peer_address: Tuple[str, int] = ("127.0.0.1", 4433)
        self.streams: Dict[int, Dict[int, bytes]] = {}  # stream_id -> {offset: data}
        self.stream_finished: Dict[int, bool] = {}
        self.highest_packet_number = -1

    def migrate_peer_address(self, new_ip: str, new_port: int) -> None:
        """
        Simulates connection migration when a mobile client changes IP
        (e.g., from Wi-Fi to 5G cellular network). The connection persists!
        """
        self.peer_address = (new_ip, new_port)

    def receive_packet(self, packet: QuicPacket) -> None:
        """Ingests a packet, updating independent stream buffers."""
        if packet.dest_conn_id != self.connection_id:
            raise ValueError(f"Packet CID {packet.dest_conn_id.hex()} does not match connection {self.connection_id.hex()}")

        if packet.packet_number > self.highest_packet_number:
            self.highest_packet_number = packet.packet_number

        for frame in packet.frames:
            if frame.stream_id not in self.streams:
                self.streams[frame.stream_id] = {}
                self.stream_finished[frame.stream_id] = False

            self.streams[frame.stream_id][frame.offset] = frame.data
            if frame.fin:
                self.stream_finished[frame.stream_id] = True

    def get_stream_data(self, stream_id: int) -> Optional[bytes]:
        """Reassembles stream data in offset order."""
        if stream_id not in self.streams:
            return None
        chunks = self.streams[stream_id]
        sorted_offsets = sorted(chunks.keys())
        # Check contiguous
        expected_offset = 0
        buf = bytearray()
        for off in sorted_offsets:
            if off != expected_offset:
                # Missing chunk: Head-of-line blocking on THIS stream only!
                return None
            buf.extend(chunks[off])
            expected_offset += len(chunks[off])
        return bytes(buf)


def main():
    print("=================================================================")
    print("Testing Day 60: HTTP/3 & QUIC Transport Simulator")
    print("=================================================================")

    # Test 1: QUIC Packet Serialization with 8-byte Connection ID
    cid = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    f1 = QuicStreamFrame(stream_id=0, offset=0, data=b"GET /index.html HTTP/3", fin=True)
    f2 = QuicStreamFrame(stream_id=4, offset=0, data=b"GET /styles.css HTTP/3", fin=True)

    pkt1 = QuicPacket(
        packet_type=QuicPacketType.SHORT_HEADER_1RTT,
        dest_conn_id=cid,
        packet_number=1001,
        frames=[f1, f2]
    )
    wire_bytes = QuicPacketCodec.encode_1rtt_packet(pkt1)
    assert wire_bytes[0] == 0x43
    assert wire_bytes[1:9] == cid
    print(f"[PASS] QUIC short-header packet successfully encoded into {len(wire_bytes)} UDP wire bytes.")

    # Test 2: QUIC Packet Deserialization
    parsed_pkt = QuicPacketCodec.decode_1rtt_packet(wire_bytes)
    assert parsed_pkt.dest_conn_id == cid
    assert parsed_pkt.packet_number == 1001
    assert len(parsed_pkt.frames) == 2
    assert parsed_pkt.frames[0].stream_id == 0
    assert parsed_pkt.frames[0].data == b"GET /index.html HTTP/3"
    assert parsed_pkt.frames[1].stream_id == 4
    print("[PASS] QUIC packet deserialization verified.")

    # Test 3: Multi-stream Independent Loss Isolation (No Cross-Stream HoL Blocking)
    # Suppose Packet A contains Stream 0 (Part 1). Packet B contains Stream 4 (All). Packet C contains Stream 0 (Part 2).
    # If Packet A is dropped, Stream 4 MUST STILL be fully readable immediately!
    conn = QuicConnection(connection_id=cid)

    # Packet B arrives (Stream 4):
    pkt_b = QuicPacket(
        packet_type=QuicPacketType.SHORT_HEADER_1RTT,
        dest_conn_id=cid,
        packet_number=1002,
        frames=[QuicStreamFrame(stream_id=4, offset=0, data=b"body { color: blue; }", fin=True)]
    )
    conn.receive_packet(pkt_b)

    # Stream 4 is immediately available despite Stream 0 missing!
    assert conn.get_stream_data(4) == b"body { color: blue; }"
    assert conn.get_stream_data(0) is None, "Stream 0 should be unready due to missing offset 0"
    print("[PASS] QUIC zero Head-of-Line blocking verified: Stream 4 processed independently while Stream 0 is waiting.")

    # Now Packet C arrives (Stream 0 Part 2):
    pkt_c = QuicPacket(
        packet_type=QuicPacketType.SHORT_HEADER_1RTT,
        dest_conn_id=cid,
        packet_number=1003,
        frames=[QuicStreamFrame(stream_id=0, offset=6, data=b"World!", fin=True)]
    )
    conn.receive_packet(pkt_c)
    assert conn.get_stream_data(0) is None, "Stream 0 still incomplete (offset 0 missing)"

    # Finally Packet A arrives (Stream 0 Part 1 retransmission):
    pkt_a = QuicPacket(
        packet_type=QuicPacketType.SHORT_HEADER_1RTT,
        dest_conn_id=cid,
        packet_number=1004,
        frames=[QuicStreamFrame(stream_id=0, offset=0, data=b"Hello ", fin=False)]
    )
    conn.receive_packet(pkt_a)
    assert conn.get_stream_data(0) == b"Hello World!"
    print("[PASS] Stream 0 successfully reassembled after out-of-order delivery.")

    # Test 4: Connection Migration (Client switches from Wi-Fi to 5G)
    conn.migrate_peer_address("198.51.100.45", 56789)
    assert conn.peer_address == ("198.51.100.45", 56789)
    # Send another packet with the same Connection ID from the new IP:
    pkt_migrated = QuicPacket(
        packet_type=QuicPacketType.SHORT_HEADER_1RTT,
        dest_conn_id=cid,
        packet_number=1005,
        frames=[QuicStreamFrame(stream_id=8, offset=0, data=b"Migrated data stream", fin=True)]
    )
    conn.receive_packet(pkt_migrated)
    assert conn.get_stream_data(8) == b"Migrated data stream"
    print("[PASS] Connection migration verified: Connection ID persisted across IP transition without renegotiation.")

    print("\nALL DAY 60 HTTP/3 & QUIC TESTS PASSED (100% SUCCESS)!")


if __name__ == "__main__":
    main()
