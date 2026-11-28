# Day 60: HTTP/3 & QUIC: UDP Transport and Stream Demultiplexing

## 1. What Are We Building & Why Does It Matter?
HTTP/2 brought multiplexing to web transport, but it still relied on TCP. Because TCP enforces strict in-order byte delivery at the OS transport layer, any single packet dropped on the wire causes **TCP-Level Head-of-Line Blocking**: all multiplexed HTTP/2 streams stall while the operating system waits for the dropped packet to be retransmitted, even if the dropped packet belonged to an unrelated stream!

**HTTP/3 (RFC 9114)** and **QUIC (RFC 9000)** solve this permanently by moving transport protocol logic from the OS kernel into userspace over **UDP**. In QUIC:
1. **Independent Stream Demultiplexing**: Packet loss on Stream A does NOT stall Stream B. Each stream has independent packet sequencing and reassembly buffers.
2. **Connection IDs (CID)**: Instead of identifying connections by the traditional 4-tuple (`Source IP`, `Source Port`, `Dest IP`, `Dest Port`), QUIC connections are identified by a 64-bit Connection ID. When a mobile smartphone switches from office Wi-Fi to 5G cellular, the connection survives without dropping or renegotiating TLS handshakes (**Connection Migration**).
3. **0-RTT Resumption**: Eliminates connection establishment latency.

In this lab, we build a QUIC short-header packet encoder/decoder over UDP, an independent multi-stream loss-isolation engine, and a connection migration handler.

## 2. Python Concepts for Beginners
Here are the key Python programming techniques used in this project:

- **Nested Dictionaries for Segment Reassembly**:
  To store out-of-order chunks on independent streams, we use nested dictionaries keyed by `stream_id` and `offset`:
  ```python
  streams: dict[int, dict[int, bytes]] = {}
  streams[stream_id][offset] = chunk_data
  ```
- **Sorting Dictionary Keys for In-Order Assembly**:
  By sorting the byte offsets, we check if all contiguous chunks are present from offset 0 to EOF:
  ```python
  expected = 0
  for offset in sorted(chunks.keys()):
      if offset != expected:
          return None  # Gap in stream data!
      expected += len(chunks[offset])
  ```
- **Enum for Protocol State Management**:
  Using Python `IntEnum` allows defining clean constants that serialize directly to byte fields.

## 3. Step-by-Step Code Walkthrough
1. **`QuicStreamFrame`**: Represents a payload chunk carried inside a QUIC packet, tracking `stream_id`, byte `offset`, payload `data`, and the `fin` termination flag.
2. **`QuicPacketCodec.encode_1rtt_packet()`**:
   - Creates the 1-RTT Short Header byte (`0x43`).
   - Writes the 8-byte Destination Connection ID.
   - Writes the 32-bit monotonically increasing packet number.
   - Packs each stream frame with its 11-byte frame metadata header.
3. **`QuicPacketCodec.decode_1rtt_packet()`**: Reads raw UDP datagram bytes and parses the header, Connection ID, and individual stream frames.
4. **`QuicConnection`**:
   - `receive_packet()`: Validates the incoming Connection ID and routes data chunks into isolated per-stream buffers.
   - `get_stream_data()`: Checks if all contiguous byte ranges are available for a specific stream. If Stream 0 has missing packets, Stream 4 can still be reassembled and returned immediately!
   - `migrate_peer_address()`: Updates the remote IP/port endpoint without resetting stream states or renegotiating keys.

## 4. How to Run & Expected Output
Execute the simulator script directly from the terminal:
```bash
python code/day-60/quic_udp_transport_and_stream_demux.py
```

Expected terminal output:
```text
=================================================================
Testing Day 60: HTTP/3 & QUIC Transport Simulator
=================================================================
[PASS] QUIC short-header packet successfully encoded into 87 UDP wire bytes.
[PASS] QUIC packet deserialization verified.
[PASS] QUIC zero Head-of-Line blocking verified: Stream 4 processed independently while Stream 0 is waiting.
[PASS] Stream 0 successfully reassembled after out-of-order delivery.
[PASS] Connection migration verified: Connection ID persisted across IP transition without renegotiation.

ALL DAY 60 HTTP/3 & QUIC TESTS PASSED (100% SUCCESS)!
```

## 5. Common Python Errors & Troubleshooting
- **`ValueError: Expected short header (bit 6 set)`**:
  *Cause*: Decoding a long-header packet (used during initial handshake) with the 1-RTT short-header decoder.
  *Fix*: Check `header_byte & 0x80` to route between long and short header decoders.
- **`ValueError: Destination Connection ID must be exactly 8 bytes`**:
  *Cause*: Passing an invalid length Connection ID string or byte array.
  *Fix*: QUIC connection IDs are typically 8 to 20 bytes; ensure exactly 8 bytes are passed for 1-RTT packets.
- **Silent Stream Reassembly Stalls**:
  *Cause*: A missing chunk creates an offset gap, causing `get_stream_data()` to return `None`.
  *Fix*: This is intended behavior in QUIC for that specific stream while waiting for retransmission, but other streams continue processing normally!

## 6. Beginner Exercises & Challenges
1. **Packet Loss Simulator**: Implement a UDP network wrapper with configurable drop probability ($P_{loss} = 0.10$) and verify that retransmissions recover missing offsets.
2. **ACK Frame Generator**: Add an RFC 9000 `ACK` frame that reports received packet numbers back to the peer so the sender can prune its retransmission buffer.
3. **0-RTT Early Data Cache**: Build an encryption token store that allows clients to transmit application data in the very first UDP datagram when reconnecting to a known server.
