# Day 59: HPACK Architecture: Header Compression, Static/Dynamic Tables, and Huffman Coding

In typical modern web applications, HTTP request headers average between 500 bytes and 2 Kilobytes in size (dominated by repetitive cookies, User-Agent strings, and authorization tokens). While HTTP/2 multiplexed payloads into binary frames, transmitting repetitive textual headers on every single stream would consume massive bandwidth. However, standard compression algorithms like gzip were banned due to cryptographic side-channel attacks (**CRIME** and **BREACH**). **HPACK** (RFC 7541) was engineered specifically to provide secure, memory-bounded, differential header compression. This masterclass examines the 61-entry Static Table, FIFO Dynamic Tables, variable-length integer encoding, and Canonical Huffman Trees.

---

## 1. Why Standard GZIP Was Banned: The CRIME Attack

In 2012, security researchers demonstrated the **CRIME** (Compression Ratio Info-leak Made Easy) attack against SPDY and TLS compression.

### How CRIME Worked
Gzip uses the DEFLATE algorithm, which pairs LZ77 dictionary matching with Huffman coding. If an input string contains duplicate substrings, LZ77 replaces occurrences with a short distance-length pointer, reducing total compressed ciphertext size.
An attacker injecting cross-origin JavaScript could append guesses to a secret cookie:
```text
Cookie: secret=A... -> Size: 42 bytes
Cookie: secret=B... -> Size: 42 bytes
Cookie: secret=C... -> Size: 41 bytes  <--- COMPRESSION DROP! Guess 'C' matched secret!
```
By observing the exact encrypted ciphertext size across TLS frames, attackers brute-forced high-entropy session cookies byte-by-byte in real time.

---

## 2. The HPACK Architecture: Two Tables & One Tree

HPACK completely eliminates the CRIME vulnerability by disallowing compression across different security boundaries. It compresses headers using three coordinated primitives:

```text
Incoming Header: ":method: GET"
       |
       +--> 1. Check STATIC TABLE (Pre-compiled 61 entries)
       |       Match found at Index 2! Emit 1-byte opcode: 0x82!
       |
       +--> 2. Check DYNAMIC TABLE (Sliding FIFO window of past headers)
       |       If custom header seen previously (e.g. "x-api-key"), emit index!
       |
       +--> 3. Literal Encoding via CANONICAL HUFFMAN TREE
               If header text not in tables, compress characters using static Huffman tree!
```

---

## 3. The HPACK Static Table (RFC 7541 Appendix A)

HPACK pre-defines 61 immutable, frequently used HTTP header fields known to all compliant clients and servers. A single 1-byte integer references both header name and value:

```text
Index    Header Name               Header Value
------------------------------------------------------
1        :authority                (Empty)
2        :method                   GET
3        :method                   POST
4        :path                     /
5        :path                     /index.html
6        :scheme                   http
7        :scheme                   https
8        :status                   200
...
14       :status                   500
...
```

If an HTTP/2 request has method `GET`, HPACK represents the entire `:method: GET` string as a single byte: `0x82` (`10000010_2`, where the top bit indicates an indexed representation, and the remaining 7 bits equal index 2). A 12-byte header collapses into **1 byte**!

---

## 4. The FIFO Dynamic Table Architecture

Headers not present in the static table (such as user cookies or custom API tokens) are inserted into the **Dynamic Table**.

### Sliding Window Mechanics
1. The dynamic table has a maximum memory capacity negotiated via `SETTINGS_HEADER_TABLE_SIZE` (default 4,096 bytes).
2. When a new header (e.g., `authorization: Bearer token123`) is encoded, it is inserted at Index 62 (directly following the 61 static entries).
3. Subsequent requests referencing this identical token simply transmit index `62`.
4. If newly added headers cause total byte memory to exceed the table capacity, the oldest entries at the tail of the table are evicted (**First-In, First-Out / FIFO**).

### Dynamic Table Entry Size Calculation
The size of an entry in the dynamic table is defined as the length of the name in bytes, plus the length of the value in bytes, plus a fixed overhead of **32 bytes** to account for internal pointer bookkeeping:

$$\text{Entry Size} = \text{len}(\text{Name}) + \text{len}(\text{Value}) + 32 \text{ bytes}$$

---

### HPACK Dynamic Table Entry C Struct
In HTTP/2 protocol engines (such as nghttp2 and kernel-level QUIC transports), the dynamic table maintains an array of header field descriptors:

```c
struct hpack_table_entry {
    uint32_t index;                /* Dynamic table 1-based index */
    uint32_t name_len;             /* Length of header name in bytes */
    uint32_t val_len;              /* Length of header value in bytes */
    uint8_t  never_indexed:1;      /* Bitfield: 1 if marked sensitive (never index) */
    uint8_t  is_huffman_encoded:1; /* Bitfield: 1 if string data is Huffman compressed */
    uint8_t  reserved_bits:6;      /* Reserved bits for alignment */
    uint8_t  padding[3];           /* 32-bit boundary alignment */
    char     *name_ptr;            /* Pointer to dynamic name buffer */
    char     *val_ptr;             /* Pointer to dynamic value buffer */
} __attribute__((packed));
```

Field Alignment Breakdown:
- `index` (4 bytes): Monotonically assigned slot index within the active sliding window.
- `name_len` & `val_len` (4 bytes each): Explicit buffer boundary lengths.
- Bitfields (1 byte total): Flags for RFC 7541 sensitive headers and Huffman state.
- Buffer Pointers (8 bytes each on 64-bit platforms): Direct references to allocated character arrays.
- Memory Overhead: Matches RFC 7541 Section 4.1 rule adding exactly 32 bytes of accounting overhead per entry.

---

## 5. Variable-Length Integer Representation (RFC 7541 Section 5.1)

HPACK integers are used to represent table indices and string lengths. An integer is serialized using a prefix of $N$ bits ($1 \le N \le 8$).

### The Integer Encoding Algorithm
If the integer value $I$ fits within $2^N - 1$, it is placed directly into the $N$-bit prefix:

$$I < 2^N - 1 \implies \text{Store directly in } N \text{ bits}$$

If $I \ge 2^N - 1$:
1. All $N$ prefix bits are set to 1.
2. The value is decremented by $2^N - 1$.
3. The remainder is encoded as a series of 7-bit bytes, where the 8th (top) bit is set to 1 on all continuation bytes, and set to 0 on the final byte.

---

## 6. Compilable C Implementation: HPACK Variable-Length Integer Decoder

Compile with: `gcc -O2 -Wall -Wextra hpack_int_decoder.c -o hpack_int_decoder`

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

/* Decodes an HPACK variable-length integer given an N-bit prefix */
uint32_t decode_hpack_integer(const uint8_t *buf, size_t len, int prefix_bits, size_t *bytes_read) {
    if (len == 0 || prefix_bits < 1 || prefix_bits > 8) return 0;

    uint8_t mask = (1 << prefix_bits) - 1;
    uint32_t value = buf[0] & mask;
    *bytes_read = 1;

    /* If value is less than 2^N - 1, integer was fully contained in prefix */
    if (value < mask) {
        return value;
    }

    /* Multi-byte continuation decoding */
    uint32_t m = 0;
    while (*bytes_read < len) {
        uint8_t byte = buf[*bytes_read];
        (*bytes_read)++;

        value += (byte & 0x7F) << m;
        m += 7;

        /* If top bit is 0, this was the final byte */
        if ((byte & 0x80) == 0) {
            break;
        }
    }

    return value;
}

int main(void) {
    /* Test Case: Integer 1337 encoded with a 5-bit prefix
       2^5 - 1 = 31.
       Byte 0: 5 prefix bits set to 1 (0x1F)
       Remainder = 1337 - 31 = 1306.
       1306 in 7-bit chunks: 1306 % 128 = 26 (0x1A), 1306 / 128 = 10 (0x0A).
       Byte 1: 0x1A | 0x80 = 0x9A
       Byte 2: 0x0A */
    uint8_t encoded_data[] = { 0x1F, 0x9A, 0x0A };
    size_t consumed = 0;

    uint32_t result = decode_hpack_integer(encoded_data, sizeof(encoded_data), 5, &consumed);

    printf("=== HPACK Variable-Length Integer Decoder ===\n");
    printf("Decoded Integer: %u (Consumed %zu bytes)\n", result, consumed);
    if (result == 1337) {
        printf("SUCCESS: Perfect RFC 7541 variable-length integer decoding!\n");
    }

    return EXIT_SUCCESS;
}
```

---

## 7. Production Post-Mortem: Dynamic Table Memory Exhaustion DoS

### Incident Overview
In early implementations of HTTP/2 reverse proxies, attackers exploited the HPACK dynamic table by opening thousands of concurrent multiplexed connections and transmitting massive random header strings designed to fill the 4,096-byte dynamic table on each stream.

### The Amplification Vector
1. Because the dynamic table is stateful, the server was forced to maintain a separate 4 KB memory allocation per active connection.
2. By holding 500,000 idle TCP connections open, attackers forced the reverse proxy cluster to allocate over **2 Gigabytes of non-pageable kernel slab memory** exclusively for dynamic tables.
3. System `kswapd` thrashing occurred, and the Linux OOM-killer terminated the proxy daemons.

### Remediation
1. Modern HTTP/2 servers restrict `SETTINGS_HEADER_TABLE_SIZE` to 0 or 512 bytes for untrusted ingress clients. Setting it to 0 completely disables the dynamic table while retaining static table and Huffman coding benefits.
---

## 8. HPACK Static Huffman Table Encoding Mechanics

When a header literal string cannot be matched to a table index, HPACK encodes it using a fixed, pre-computed **Canonical Huffman Code** (RFC 7541 Appendix B).

### Entropy Optimizations for Common Characters
The Huffman tree assigns shorter bit sequences to high-frequency ASCII characters in web headers:
- `'0'` (Digit 0): 5 bits (`00000`)
- `'a'` (Char a): 5 bits (`00011`)
- `'c'` (Char c): 5 bits (`00101`)
- `'-'` (Hyphen): 6 bits (`010110`)
- Rare symbols: up to 30 bits

```text
Uncompressed ASCII "custom-key": 10 bytes = 80 bits
HPACK Huffman Encoded Bitstream: 52 bits (35% bandwidth compression!)
```
The terminating boundary is padded with the highest-order bits of the EOS (End of String) symbol (`0x3FFFFFFF`), preventing ambiguous byte alignment.
---

## 9. Dynamic Table Size Update (RFC 7541 Section 6.3)

A client or server can dynamically change the maximum memory capacity of the dynamic table by transmitting a Dynamic Table Size Update header block:

```text
  0   1   2   3   4   5   6   7
+---+---+---+---+---+---+---+---+
| 0   0   1 |   Max size (5+)   |
+---+---+---+-------------------+
```
The top 3 bits are `001`. If the new capacity is lower than current byte utilization, the receiver immediately executes FIFO eviction of the oldest entries until memory usage is less than or equal to the new maximum size.
---

## 10. Canonical Huffman Tree Traversal Pseudocode

Decoding Huffman bitstreams requires traversing the binary tree from root to leaf:
```c
/* Canonical Huffman bit-by-bit decode loop */
uint32_t node = HUFFMAN_ROOT;
for (int i = 0; i < bit_count; i++) {
    int bit = (bitstream[i / 8] >> (7 - (i % 8))) & 1;
    node = huffman_tree[node].child[bit];
    if (huffman_tree[node].is_leaf) {
        emit_byte(huffman_tree[node].symbol);
        node = HUFFMAN_ROOT; /* Reset to root for next symbol */
    }
}
```
If the bitstream terminates on an incomplete interior node with non-EOS padding, the decoder rejects the frame as malformed.
