# Day 53: HTTP Headers, Content Encodings, and Chunked Transfer Encoding Mechanics

HTTP headers represent the metadata control plane of web communication. Beyond basic request routing, headers negotiate character sets, language localization, content compression, and transport framing. In HTTP/1.0, servers were forced to buffer entire dynamic responses in memory before transmission to calculate the `Content-Length` header. HTTP/1.1 resolved this with **Chunked Transfer Encoding** (`Transfer-Encoding: chunked`), allowing servers to stream dynamic content of arbitrary size across persistent sockets. This masterclass dissects header formatting, compression ratios, hex-encoded chunk framing, and HTTP Request Smuggling vulnerabilities.

---

## 1. HTTP/1.1 Message Framing: Content-Length vs Chunked Transfer

A receiver on a TCP socket streams an unstructured byte stream. To know where one HTTP response ends and the next begins, the receiver relies on one of two framing mechanisms:

### 1. `Content-Length: <bytes>`
The header explicitly specifies the exact length of the payload in integer bytes:
```text
HTTP/1.1 200 OK


Content-Type: text/html


Content-Length: 13





<h1>Hello</h1>
```
The client reads headers until `



`, then reads exactly 13 bytes from the socket.

### 2. `Transfer-Encoding: chunked`
When content is generated dynamically (database streaming, real-time telemetry, template rendering), the server cannot predict the total byte count in advance. Setting an incorrect `Content-Length` causes premature connection truncation or socket hang.
Under `chunked` encoding, the message body is sliced into a series of chunks.

```text
[Chunk Size in Hex]


[Raw Chunk Data Bytes]


...
0


[Optional Trailing Headers]





```

---

## 2. Chunked Framing Protocol Specification (RFC 9112 Section 7.1)

Each chunk begins with an ASCII hexadecimal string representing the chunk size, followed by `

` (`0x0D 0x0A`), followed by the raw chunk data, followed by another `

`. The entire body terminates with a zero-length chunk (`0



`).

```text
HTTP/1.1 200 OK


Transfer-Encoding: chunked


Content-Type: text/plain





7


Mozilla


9


Developer


7


Network


0





```

### Deconstructed Binary Stream Representation
```text
Hex Offset:   Bytes (ASCII / Hex)               Interpretation
-------------------------------------------------------------------------
0000:         37 0D 0A                          Chunk 1 Size: 7 bytes
0003:         4D 6F 7A 69 6C 6C 61 0D 0A        Data: "Mozilla

"
000C:         39 0D 0A                          Chunk 2 Size: 9 bytes
000F:         44 65 76 65 6C 6F 70 65 72 0D 0A  Data: "Developer

"
001B:         37 0D 0A                          Chunk 3 Size: 7 bytes
001E:         4E 65 74 77 6F 72 6B 0D 0A        Data: "Network

"
0027:         30 0D 0A 0D 0A                    Terminator: "0



"
```

### Kernel & Proxy C Struct Framing Representation
In high-performance reverse proxies (e.g., NGINX, HAProxy) and Linux kernel socket filters, streaming chunks are tracked using formal state structures:

```c
struct http_chunk_parser {
    uint64_t chunk_size;        /* 64-bit parsed payload length in bytes */
    uint32_t bytes_remaining;   /* Bytes left to drain for current chunk */
    uint16_t state;             /* Finite state machine state indicator */
    uint8_t  is_last_chunk;     /* 1-bit boolean flag: final chunk (size 0) */
    uint8_t  has_trailers;      /* 1-bit boolean flag: post-chunk trailers */
} __attribute__((packed));
```

Field Alignment Breakdown:
- `chunk_size` (8 bytes): Parsed unsigned hexadecimal length of the payload block.
- `bytes_remaining` (4 bytes): Decremented as socket `recv()` drains payload bytes.
- `state` (2 bytes): Tracks parser position (CHUNK_SIZE, CHUNK_DATA, CHUNK_CRLF, TRAILERS).
- `is_last_chunk` (1 byte): Flag indicating receipt of `0\r\n`.
- `has_trailers` (1 byte): Flag indicating trailing RFC metadata headers follow chunk 0.
- Total memory footprint: exactly 16 bytes per active connection.

### Framing Overhead Mathematics
Given $K$ chunks of sizes $S_1, S_2, \dots, S_K$, the framing overhead introduced by chunked encoding is:

$$\text{Overhead} = 5 + \sum_{i=1}^{K} \left( \text{len}(\text{hex}(S_i)) + 4 \right) \text{ bytes}$$

Where $4$ represents the two `

` delimiters per chunk, and $5$ represents the terminating `0



`.

---

## 3. Content Encodings & Compression Ratios

To minimize bandwidth consumption, HTTP enables end-to-end payload compression negotiated via `Accept-Encoding` and `Content-Encoding`.

- **`gzip`**: LZ77 compression with 32-bit CRC (RFC 1952). Universally supported.
- **`deflate`**: Raw zlib format (RFC 1950).
- **`br` (Brotli)**: Modern dictionary-based algorithm developed by Google (RFC 7932). Outperforms gzip by 15–25% on textual assets (HTML/CSS/JS).

### Shannon Entropy & Compression Limits
The theoretical compression limit of an HTTP document is governed by its Shannon entropy $H(X)$:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i) \quad \text{(bits per byte)}$$

$$\text{Minimum Compressed Size} = \frac{N \times H(X)}{8} \text{ bytes}$$

High-entropy data (JPEG, PNG, MP4, encrypted binaries) already have $H(X) \approx 8\text{ bits/byte}$. Enabling `Content-Encoding: gzip` on image or video assets increases CPU load and actually *expands* file size due to compression container headers!

---

## 4. Compilable C Implementation: Streaming Chunked HTTP Parser

Compile with: `gcc -O2 -Wall -Wextra chunk_parser.c -o chunk_parser`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void parse_chunked_stream(const char *stream, size_t len) {
    size_t offset = 0;
    int chunk_index = 1;

    printf("=== Beginning Chunked Stream Decoding ===\n");

    while (offset < len) {
        /* Read Hexadecimal Chunk Size */
        char *endptr;
        unsigned long chunk_size = strtoul(stream + offset, &endptr, 16);

        /* Advance past hex size and following 

 */
        char *crlf = strstr(stream + offset, "\r\n");
        if (!crlf) {
            fprintf(stderr, "Malformed chunk framing: missing CRLF after size.\n");
            break;
        }
        offset = (crlf - stream) + 2;

        /* Check for terminating chunk (size 0) */
        if (chunk_size == 0) {
            printf("[End of Stream]: Received terminating chunk 0.\n");
            break;
        }

        /* Verify buffer boundaries */
        if (offset + chunk_size > len) {
            fprintf(stderr, "Chunk data overflows input buffer!\n");
            break;
        }

        /* Extract and display chunk payload */
        printf("Chunk #%d (Size: %lu bytes): \"", chunk_index++, chunk_size);
        fwrite(stream + offset, 1, chunk_size, stdout);
        printf("\"\n");

        /* Advance offset past chunk data and trailing 

 */
        offset += chunk_size + 2;
    }
}

int main(void) {
    /* Simulated HTTP/1.1 raw chunked wire stream */
    const char wire_data[] = 
        "5\r\nHello\r\n"
        "2\r\n, \r\n"
        "6\r\nWorld!\r\n"
        "0\r\n\r\n";

    parse_chunked_stream(wire_data, sizeof(wire_data) - 1);
    return EXIT_SUCCESS;
}
```

---

## 5. Security Vulnerability: HTTP Request Smuggling (CL.TE & TE.CL Desync)

When an architecture pairs a front-end reverse proxy (e.g. NGINX, Cloudflare) with a back-end application server (e.g. Apache, Tomcat) over a persistent connection, a catastrophic vulnerability occurs if the two systems disagree on whether to prioritize `Content-Length` (CL) or `Transfer-Encoding` (TE).

### The CL.TE Desync Attack
- The **Front-end** prioritizes `Content-Length`.
- The **Back-end** prioritizes `Transfer-Encoding`.

```text
Attacker Sends Smuggled Request:
POST / HTTP/1.1


Host: target.com


Content-Length: 13


Transfer-Encoding: chunked





0





GPOST /admin HTTP/1.1


```

1. **Front-End Processing**: Reads `Content-Length: 13`. It counts 13 bytes (`0



` + `GPOST `), concludes the request is complete, and forwards the entire stream over the persistent TCP socket to the back-end.
2. **Back-End Processing**: Reads `Transfer-Encoding: chunked`. It sees `0



` and terminates the first request immediately.
3. **The Poisoned Queue**: The remaining unread bytes (`GPOST /admin HTTP/1.1

`) remain sitting in the back-end TCP socket buffer!
4. **Victim Interception**: When a legitimate user's request arrives on the same persistent socket (`GET /index.html HTTP/1.1`), the back-end concatenates it:
```text
GPOST /admin HTTP/1.1

GET /index.html HTTP/1.1
```
The victim's credentials execute the attacker's unauthorized administrative action!

### Remediation
1. Enforce strict HTTP/2 or HTTP/3 multiplexing between front-end and back-end proxies.
2. Configure edge proxies to strip or reject requests containing both `Transfer-Encoding` and `Content-Length`.
