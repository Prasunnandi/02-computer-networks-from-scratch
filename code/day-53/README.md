# Day 53: HTTP Chunked Transfer Codec & Smuggling Detector Lab Tutorial

Welcome to Day 53 of Computer Networks from Scratch. Today, you will build an RFC 9112 Chunked Transfer Encoding serializer and streaming parser, alongside a security auditor detecting HTTP Request Smuggling (CL.TE and TE.CL desync) vulnerabilities.

---

## 1. What Are We Building & Why Does It Matter?

When a web server generates dynamic responses (e.g. streaming database records or real-time templates), it cannot predict the final `Content-Length` in advance.

HTTP/1.1 resolved this with **Chunked Transfer Encoding** (`Transfer-Encoding: chunked`):
- Payloads are split into chunks.
- Each chunk begins with its byte size in hexadecimal followed by `
`.
- The transmission concludes with a zero-length chunk (`0

`).

However, if a front-end proxy prioritizes `Content-Length` while a back-end server prioritizes `Transfer-Encoding`, attackers can perform **HTTP Request Smuggling**, injecting hidden requests directly into other users' persistent connections.

In this lab, you implement both the binary chunk codec and the smuggling detector.

---

## 2. Python Concepts for Beginners

### A. Formatting Integers as Hexadecimal (`:X`)
Format integer sizes into uppercase hexadecimal strings:
```python
size = 255
hex_str = f"{size:X}"  # 'FF'
```

### B. Byte Buffer Manipulation (`bytearray`)
Build binary streams incrementally using mutable byte arrays:
```python
stream = bytearray()
stream.extend(b"5\r\nHello\r\n")
stream.extend(b"0\r\n\r\n")
result_bytes = bytes(stream)
```

### C. Parsing Hexadecimal Strings (`int(s, 16)`)
Convert hex strings back into integer values:
```python
chunk_size = int("1A", 16)  # 26 in decimal
```

---

## 3. Step-by-Step Code Walkthrough

1. **`DecodedChunkMessage` Dataclass**: Stores the reconstructed body bytes and trailing headers.
2. **`ChunkedTransferCodec` Class**:
   - `encode_chunk()`: Wraps data in `<hex_size>
<data>
`.
   - `encode_stream()`: Loops through chunks, appends the terminating `0

` marker and optional trailers.
   - `decode_stream()`: Reads hexadecimal sizes, slices raw data bytes, verifies trailing `
` delimiters, and stops on zero.
3. **`RequestSmugglingDetector` Class**:
   - `audit_headers()`: Inspects header dictionaries. If both `Content-Length` and `Transfer-Encoding` are present simultaneously, it generates a critical security alert.
4. **`main()` Test Suite**: Validates serialization formatting, round-trip decoding, multi-kilobyte stream handling, and smuggling attack interception.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-53/chunked_transfer_codec_and_smuggling_detector.py
```

Expected output:
```text
=== Day 53: HTTP Chunked Transfer Codec & Request Smuggling Detector ===
[*] Serialized Chunked Stream Length: 46 bytes
[*] Test 1 Passed: Encoded stream formatted with valid hex sizes and terminating 0


[*] Test 2 Passed: Decoded stream payload matches original: 'Hello, Chunked World!'
[*] Test 3 Passed: Large multi-kilobyte streaming chunks decoded perfectly
[*] Test 4 Passed: Smuggling detector successfully flagged CL.TE desync: CRITICAL SECURITY ALERT: Both Content-Length (13) and Transfer-Encoding (chunked) present! Request Smuggling Risk!
[*] Test 5 Passed: Clean headers accepted: Headers compliant with RFC 9112
All HTTP Chunked Transfer & Smuggling Detector assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`ValueError: invalid literal for int() with base 16`**: Ensure you strip trailing whitespace and chunk extensions (e.g. `;ext=val`) before converting the size line to integer.
- **Off-By-One Buffer Slicing**: Remember that `
` occupies exactly 2 bytes (`0x0D 0x0A`). Always advance offsets by `+ 2`.

---

## 6. Beginner Exercises & Challenges

1. **Support Chunk Extensions**: Extend `decode_stream()` to parse and store chunk extensions (name-value pairs appended after semicolons).
2. **Implement Trailing Header Parsing**: Add logic extracting trailing headers (e.g. cryptographic checksums like `X-Checksum: sha256`) following the `0` chunk.
3. **Stream Memory Generator**: Convert `decode_stream()` into a Python generator yielding chunks incrementally to prevent loading huge files into memory all at once.
