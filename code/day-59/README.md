# Day 59: HPACK Header Compression Engine for HTTP/2

## 1. What Are We Building & Why Does It Matter?
In HTTP/1.1, request headers are sent as redundant, uncompressed ASCII text on every single transaction. A web client sending cookies, user-agent strings, and security headers might upload 1,000 to 2,000 bytes of headers for a request that downloads a 200-byte JSON response. Standard compression algorithms like GZIP/DEFLATE could not be used directly on HTTP headers due to the **CRIME (Compression Ratio Info-leak Made Easy)** security vulnerability, which allowed attackers to snoop secret session cookies by observing ciphertext sizes.

To solve this securely, HTTP/2 introduced **HPACK (RFC 7541)**. HPACK uses two complementary tables to eliminate header redundancy:
1. **Static Table**: A fixed pre-defined lookup table of 61 common HTTP headers (such as `:method: GET`, `:status: 200`, `content-type`, etc.).
2. **Dynamic Table**: A sliding-window FIFO buffer shared between client and server that dynamically records new headers encountered during the session.

Repeated headers are compressed down to a single byte index. In this lab, we build an RFC 7541 variable-length integer codec, a dynamic table with byte-budget FIFO eviction, and a header encoder/decoder.

## 2. Python Concepts for Beginners
Here are the foundational Python concepts demonstrated in this project:

- **Bitwise Shifting for Variable-Length Integers**:
  When an integer exceeds the prefix bit capacity ($2^N - 1$), HPACK encodes the remainder in 7-bit chunks with the high bit (0x80) indicating continuation:
  ```python
  value -= max_prefix
  while value >= 128:
      result.append((value & 0x7F) | 0x80)
      value >>= 7
  result.append(value)
  ```
- **FIFO Queues with List Insert and Pop**:
  The HPACK dynamic table inserts newest entries at index 0 and evicts oldest entries from the tail using `.pop()`:
  ```python
  entries.insert(0, (name, value))
  oldest = entries.pop()
  ```
- **Byte Overhead Accounting**:
  RFC 7541 Section 4.1 specifies that every dynamic table entry incurs 32 bytes of memory overhead in addition to string lengths:
  ```python
  entry_size = len(name) + len(value) + 32
  ```

## 3. Step-by-Step Code Walkthrough
1. **`STATIC_TABLE`**: Contains all 61 standard entries defined in Appendix A of RFC 7541.
2. **`HpackIntegerCodec`**:
   - `encode(value, prefix_bits)`: Encodes integer values with arbitrary bit prefix sizes (5-bit, 6-bit, 7-bit).
   - `decode(data, prefix_bits, offset)`: Reconstructs integers from continuation bytes.
3. **`HpackDynamicTable`**:
   - Tracks `max_size` and `current_size`.
   - `add(name, value)`: Automatically evicts oldest entries when adding new headers to prevent exceeding the memory limit.
4. **`HpackCodec`**:
   - `lookup_index()`: Checks the static table first, then searches the dynamic table for full or name-only matches.
   - `encode_header()`: If an exact match is found, produces an Indexed Header Field (starts with bit 1). If new, produces a Literal with Incremental Indexing (starts with 01) and adds it to the dynamic table.
   - `decode_header()`: Parses wire bytes and resolves indices back to name/value pairs.

## 4. How to Run & Expected Output
Run the unit test suite directly from your terminal:
```bash
python code/day-59/hpack_header_compression_engine.py
```

Expected terminal output:
```text
=================================================================
Testing Day 59: HPACK Header Compression Engine
=================================================================
[PASS] Integer 10 (5-bit prefix) encoded as 0a and verified.
[PASS] Integer 1337 (5-bit prefix) encoded as 1f9a0a (3 bytes) and verified.
[PASS] Static table index 2 (:method: GET) compressed into single byte 0x82.
[PASS] Custom header incrementally indexed into dynamic table (42 bytes).
[PASS] Repeated header compressed from 42 bytes down to 1 byte(s) via dynamic table.
[PASS] Dynamic table FIFO eviction enforced: size is 99 <= 120 bytes.

ALL DAY 59 HPACK TESTS PASSED (100% SUCCESS)!
```

## 5. Common Python Errors & Troubleshooting
- **`IndexError: Dynamic table index out of range`**:
  *Cause*: Requesting an index that was evicted due to table size limits.
  *Fix*: Synchronize table sizes between encoder and decoder using RFC 7541 dynamic table size update frames.
- **Off-by-One Table Indexing**:
  *Cause*: RFC 7541 indices are 1-based (static table 1..61, dynamic table 62+), while Python lists are 0-based.
  *Fix*: Subtract 1 when indexing into `STATIC_TABLE` (`STATIC_TABLE[idx - 1]`).
- **Buffer Underflow on Integer Decoding**:
  *Cause*: Slicing past the end of the byte array when continuation bits are set.
  *Fix*: Check `offset + consumed < len(data)` before reading subsequent bytes.

## 6. Beginner Exercises & Challenges
1. **Huffman String Encoding**: Implement RFC 7541 Appendix B canonical Huffman table compression for header string values.
2. **Never-Indexed Headers**: Add support for the `Literal Header Field Never Indexed` pattern (starts with `0001`), used for security-critical headers like passwords or credit card numbers.
3. **Table Memory Usage Inspector**: Create a debugging function that prints the current contents of the dynamic table along with individual byte allocations and eviction warnings.
