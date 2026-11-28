# Day 58: HTTP/2 Binary Framing & Stream Multiplexing

## 1. What Are We Building & Why Does It Matter?
In HTTP/1.1, web browsers suffered severely from **Head-of-Line (HoL) Blocking**: because requests and responses were transferred as plain text over a single TCP stream, a slow request stalled all subsequent requests behind it. While browsers worked around this by opening 6 parallel TCP connections per domain, this caused severe network congestion, slow TCP slow-start ramps, and resource starvation.

HTTP/2 (RFC 7540) radically transformed web transport by replacing ASCII text with **Binary Framing**. All HTTP/2 communications are split into standardized 9-byte binary header frames. Multiple independent request/response exchanges—known as **Streams**—are multiplexed concurrently over a single shared TCP connection.

In addition, HTTP/2 includes a credit-based **Flow Control** mechanism that prevents fast senders from overflowing the buffers of slow receivers. Each stream maintains a window of bytes it is permitted to receive; when exhausted, the sender must pause until the receiver sends a `WINDOW_UPDATE` frame. In this lab, we build an RFC 7540 binary frame codec and a multi-stream multiplexer with flow control tracking.

## 2. Python Concepts for Beginners
Here are the key Python programming techniques used in this implementation:

- **24-bit Integer Packing**:
  Standard `struct` format characters support 1, 2, 4, or 8 bytes (`B`, `H`, `I`, `Q`). For 24-bit (3-byte) integers, we pack a 32-bit integer and slice off the leading byte, or use `.to_bytes()`:
  ```python
  length_bytes = length.to_bytes(3, byteorder="big")
  recovered_length = int.from_bytes(length_bytes, byteorder="big")
  ```
- **Bitwise Masking of the Reserved Bit**:
  The HTTP/2 Stream ID is 31 bits. The most significant bit (R) is reserved and must be cleared when parsing:
  ```python
  stream_id = raw_stream_int & 0x7FFFFFFF
  ```
- **Bytearrays for Efficient Data Accumulation**:
  Instead of repeatedly concatenating immutable `bytes` objects ($O(N^2)$ memory copying), we append chunks into a mutable `bytearray`:
  ```python
  stream_data = bytearray()
  stream_data.extend(new_chunk)
  ```
- **Stream State Enums**:
  Using Python `IntEnum` to model the stream state machine (`IDLE`, `OPEN`, `HALF_CLOSED_LOCAL`, `HALF_CLOSED_REMOTE`, `CLOSED`):
  ```python
  from enum import IntEnum
  class StreamState(IntEnum):
      IDLE = 0
      OPEN = 2
      CLOSED = 5
  ```

## 3. Step-by-Step Code Walkthrough
1. **`Http2FrameType`**: An enumeration defining the 10 standard HTTP/2 frame types: `DATA` (0x0), `HEADERS` (0x1), `PRIORITY` (0x2), `RST_STREAM` (0x3), `SETTINGS` (0x4), `WINDOW_UPDATE` (0x8), etc.
2. **`Http2FrameCodec.encode()`**: Packs the 9-byte frame header:
   - 3 bytes: 24-bit payload length
   - 1 byte: Frame type
   - 1 byte: Bit flags (e.g. `END_STREAM = 0x01`, `END_HEADERS = 0x04`)
   - 4 bytes: 31-bit Stream ID with the reserved bit cleared
   - Followed by the raw frame payload bytes.
3. **`Http2Stream`**: Maintains the lifecycle state of each stream (`IDLE`, `OPEN`, `HALF_CLOSED`, `CLOSED`), tracks its dedicated flow control credit window, and buffers received data chunks.
4. **`Http2StreamMultiplexer`**: Ingests interleaved frames from different stream IDs, updates stream states, verifies transitions, decrements connection and stream flow-control windows, and reassembles fragmented data.

## 4. How to Run & Expected Output
Run the script using Python:
```bash
python code/day-58/http2_frame_codec_and_stream_multiplexer.py
```

Expected terminal output:
```text
=================================================================
Testing Day 58: HTTP/2 Binary Framing & Multiplexer
=================================================================
[PASS] HTTP/2 9-byte header successfully constructed (48 total bytes).
[PASS] HTTP/2 frame decoding verified.
[PASS] Streams 1 and 3 opened concurrently on single multiplexer.
[PASS] Multiplexed interleaved data frames reassembled without cross-stream contamination.
[PASS] Flow control window correctly decremented: 65492 credits remaining.

ALL DAY 58 HTTP/2 MULTIPLEXER TESTS PASSED (100% SUCCESS)!
```

## 5. Common Python Errors & Troubleshooting
- **`struct.error: unpack requires a buffer of 4 bytes`**:
  *Cause*: Slicing the wrong number of bytes when extracting the 31-bit stream ID.
  *Fix*: Ensure `data[5:9]` (exactly 4 bytes) is passed to `struct.unpack("!I", ...)`.
- **Negative Flow Control Window**:
  *Cause*: Sending DATA frames when the available window has been exhausted without receiving a `WINDOW_UPDATE` frame.
  *Fix*: Senders must pause transmission when the stream or connection credit drops to zero.
- **Corrupted Frame Stream**:
  *Cause*: Failing to consume the full length of the payload before reading the next 9-byte header.
  *Fix*: Use the returned `consumed_bytes` count to advance your read buffer offset.
- **Invalid Stream State Transition**:
  *Cause*: Receiving DATA frames on a stream in IDLE or CLOSED state.
  *Fix*: Ensure a HEADERS frame opens the stream before sending DATA frames.

## 6. Beginner Exercises & Challenges
1. **WINDOW_UPDATE Transmitter**: Implement a mechanism that triggers a `WINDOW_UPDATE` frame back to the sender whenever a stream buffer's remaining credit falls below 16KB.
2. **RST_STREAM Error Handling**: Add a method to abort an active stream by sending a `RST_STREAM` frame with an RFC 7540 error code (e.g., `INTERNAL_ERROR = 0x2` or `CANCEL = 0x8`).
3. **Priority Tree Weighting**: Implement basic stream prioritization where streams with higher weights receive available connection flow-control credit before lower-weighted streams.
4. **Ping Round-Trip Timer**: Write a helper that constructs an HTTP/2 `PING` frame with 8 bytes of opaque payload and calculates round-trip time when the pong is received.
