# Day 57: WebSocket Protocol: Handshake, Framing, and Unmasking

## 1. What Are We Building & Why Does It Matter?
HTTP/1.1 is strictly request-response: clients send a request, and servers respond. For real-time applications such as live financial market feeds, collaborative document editors, interactive chat platforms, and online multiplayer gaming, standard HTTP polling introduces unacceptable network latency and massive header overhead.

The WebSocket protocol (RFC 6455) solves this by providing full-duplex, bidirectional communication over a single persistent TCP socket. It begins with an HTTP upgrade handshake containing a client challenge key (`Sec-WebSocket-Key`). The server verifies this challenge by concatenating a globally unique identifier (GUID), computing a SHA-1 hash, and returning a Base64 encoded `Sec-WebSocket-Accept` header.

Once the connection is upgraded, the TCP stream switches from ASCII HTTP headers to lightweight binary framing with headers as small as 2 to 10 bytes. To prevent malicious web pages from poisoning intermediate transparent HTTP proxy caches (known as cache poisoning and cross-protocol attacks), the WebSocket specification mandates that all client-to-server frames must be masked with a random 4-byte XOR key. In this lab, we build an RFC 6455 handshake authenticator, binary frame serializer, and XOR unmasking engine.

## 2. Python Concepts for Beginners
Here are the core Python mechanisms used in this lab:

- **Hashing and Base64**:
  The handshake requires combining the client's key with the magic GUID string, taking the SHA-1 digest, and encoding it into Base64:
  ```python
  import hashlib, base64

  concat = (client_key + GUID).encode("utf-8")
  digest = hashlib.sha1(concat).digest()
  accept = base64.b64encode(digest).decode("utf-8")
  ```
- **Bitwise Shifting and Masking**:
  WebSocket headers pack multiple fields inside single bytes:
  - `b0 & 0x80`: Extracts the FIN bit (most significant bit).
  - `b0 & 0x0F`: Extracts the 4-bit Opcode.
  - `b1 & 0x80`: Checks if the frame is masked (client frames must be masked).
  - `b1 & 0x7F`: Extracts the 7-bit payload length indicator.
- **Cyclic XOR Transformation**:
  Unmasking applies the 4-byte masking key cyclically across the payload:
  ```python
  unmasked = bytes(b ^ mask[i % 4] for i, b in enumerate(masked_payload))
  ```
- **Binary Packing with `struct`**:
  Packing 16-bit and 64-bit unsigned integers in network big-endian format (`!H` and `!Q`):
  ```python
  import struct
  two_byte_len = struct.pack("!H", 500)
  recovered = struct.unpack("!H", two_byte_len)[0]
  ```

## 3. Step-by-Step Code Walkthrough
1. **`compute_accept_key()`**: Takes the client's `Sec-WebSocket-Key`, appends `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`, calculates SHA-1, and returns the Base64 response header `Sec-WebSocket-Accept`.
2. **`WebSocketOpcode`**: An `IntEnum` representing RFC 6455 message types: `CONTINUATION` (0x0), `TEXT` (0x1), `BINARY` (0x2), `CLOSE` (0x8), `PING` (0x9), and `PONG` (0xA).
3. **`WebSocketFrame`**: Dataclass representing a frame with `fin`, `opcode`, `masked`, `payload`, and optional `masking_key`.
4. **`WebSocketFrameCodec.encode()`**:
   - Packs the FIN bit and Opcode into byte 0.
   - Handles variable payload lengths: $\le 125$ bytes (1 byte), $126-65535$ bytes (2-byte extended uint16), $> 65535$ bytes (8-byte extended uint64).
   - If `masked` is True, validates the 4-byte key and XOR-encrypts the payload.
5. **`WebSocketFrameCodec.decode()`**: Reads the header, parses the variable length, reads the 4-byte mask (if present), and applies the cyclic XOR unmasking formula to recover the original payload.

## 4. How to Run & Expected Output
Execute the test script directly from your terminal:
```bash
python code/day-57/websocket_frame_codec_and_unmasker.py
```

Expected terminal output:
```text
=================================================================
Testing Day 57: WebSocket Frame Codec and Unmasker
=================================================================
[PASS] Handshake Sec-WebSocket-Accept verified: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
[PASS] Server->Client unmasked text frame encoded and decoded (19 bytes)
[PASS] Client->Server masked frame successfully verified and XOR unmasked.
[PASS] 16-bit extended length frame (500 bytes) verified.
[PASS] Control frame PING successfully encoded and decoded.

ALL DAY 57 WEBSOCKET CODEC TESTS PASSED (100% SUCCESS)!
```

## 5. Common Python Errors & Troubleshooting
- **`ValueError: Incomplete frame`**:
  *Cause*: The input byte buffer is shorter than the declared frame header length or payload length.
  *Fix*: In network streaming, buffer incoming chunks until `len(data) >= expected_length`.
- **Garbled Text Output on Client Frames**:
  *Cause*: Forgetting to apply the 4-byte XOR unmasking algorithm to client frames.
  *Fix*: Apply `payload[i] ^ masking_key[i % 4]` before parsing payload as text.
- **Incorrect Handshake Key**:
  *Cause*: Adding whitespace or failing to UTF-8 encode before calling `hashlib.sha1`.
  *Fix*: Call `.strip()` and `.encode("utf-8")` on the combined string.
- **`UnicodeDecodeError` on Close or Ping Frames**:
  *Cause*: Attempting to decode binary control frames as UTF-8 text strings.
  *Fix*: Only decode payloads when `frame.opcode == WebSocketOpcode.TEXT`.

## 6. Beginner Exercises & Challenges
1. **Echo Server Loop**: Write an asynchronous or threaded TCP loop using Python's `socket` library that performs the upgrade handshake and echoes back any incoming text frames.
2. **Fragmentation Reassembler**: Implement support for fragmented messages where the first frame has `fin=False`, intermediate frames have `opcode=0x0` (Continuation), and the final frame has `fin=True`.
3. **Ping-Pong Auto-Responder**: Write a helper function that inspects incoming frames and automatically generates a matching `PONG` frame whenever a `PING` is received.
4. **Mask Key Generator**: Write a utility using Python's `os.urandom(4)` that generates cryptographically secure 4-byte masking keys for client frames.
