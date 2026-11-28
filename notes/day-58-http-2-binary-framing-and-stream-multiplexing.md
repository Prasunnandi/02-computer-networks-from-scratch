# Day 58: HTTP/2 Architecture: Binary Framing Layer, Stream Multiplexing, and Flow Control

While HTTP/1.1 kept connections open using `keep-alive`, it remained fundamentally bound to sequential text-based message exchanges, forcing browsers to open multiple parallel TCP connections to mitigate Head-of-Line (HoL) blocking. **HTTP/2** (RFC 7540, RFC 9113) represents the most significant architectural evolution of web transport since 1999. By introducing a formal **Binary Framing Layer**, HTTP/2 enables true bidirectional multiplexing of thousands of independent request-response streams over a single shared TCP socket, eliminating application-layer HoL blocking, reducing connection setup overhead, and implementing stream prioritization and credit-based flow control.

---

## 1. The Core Paradigm Shift: Text Lines to Binary Frames

HTTP/1.1 serialized messages as ASCII character streams delimited by Carriage Return and Line Feed (`

`). Parsing ASCII requires byte-by-byte scanning for newlines, leading to parsing ambiguities, whitespace vulnerabilities, and high CPU serialization overhead.

HTTP/2 decomposes every message into an interleaved sequence of standardized **Binary Frames**:

```text
HTTP/1.1 Architecture:
+--------------------------------------------------+
|      Application Layer (HTTP Text Syntax)        |
+--------------------------------------------------+
|           Transport Layer (TCP Socket)           |
+--------------------------------------------------+

HTTP/2 Architecture:
+--------------------------------------------------+
|      Application Layer (HTTP Semantics: GET...)  |
+--------------------------------------------------+
|    BINARY FRAMING LAYER (Streams & Frames)       |  <--- Multiplexing Engine
+--------------------------------------------------+
|           Transport Layer (TCP Socket)           |
+--------------------------------------------------+
```

---

## 2. Anatomy of the 9-Byte HTTP/2 Frame Header

Every frame in HTTP/2 begins with an immutable, fixed-width 9-byte (72-bit) binary header followed by a variable-length payload:

```text
 +-----------------------------------------------+
 |                 Length (24)                   |
 +---------------+---------------+---------------+
 |   Type (8)    |   Flags (8)   |
 +-+-------------+---------------+-------------------------------+
 |R|                 Stream Identifier (31)                      |
 +=+=============================================================+
 |                   Frame Payload (0...)                      ...
 +---------------------------------------------------------------+
```

### Binary Header Field Breakdown
1. **Length (24 bits)**: Unsigned integer indicating payload length in bytes (Default maximum $2^{14} = 16,384$ bytes; expandable up to $2^{24}-1 = 16,777,215$ bytes via `SETTINGS_MAX_FRAME_SIZE`). The 9-byte header itself is excluded from this length.
2. **Type (8 bits)**: The functional role of the frame:
   - `0x00`: `DATA` (Payload message bytes)
   - `0x01`: `HEADERS` (Compressed request/response metadata)
   - `0x02`: `PRIORITY` (Stream weight and dependency hierarchy)
   - `0x03`: `RST_STREAM` (Immediate termination of a stream)
   - `0x04`: `SETTINGS` (Connection parameter negotiation)
   - `0x05`: `PUSH_PROMISE` (Server push notification)
   - `0x06`: `PING` (Round-trip time measurement & heartbeat)
   - `0x07`: `GOAWAY` (Graceful connection teardown notification)
   - `0x08`: `WINDOW_UPDATE` (Credit-based flow control)
3. **Flags (8 bits)**: Frame-specific boolean modifiers (e.g. `END_STREAM = 0x01`, `END_HEADERS = 0x04`).
4. **R (1 bit)**: Reserved bit (must remain 0).
5. **Stream Identifier (31 bits)**: Uniquely identifies the stream to which the frame belongs.
   - Stream `0x0`: Reserved exclusively for control frames affecting the entire connection (`SETTINGS`, `PING`, connection-level `WINDOW_UPDATE`).
   - Odd-numbered Streams (`1, 3, 5...`): Initiated by the client.
   - Even-numbered Streams (`2, 4, 6...`): Initiated by the server (Server Push).

---

## 3. Bidirectional Multiplexing & Interleaving

In HTTP/2, multiple logical streams are interleaved across the physical wire simultaneously. A 50-Megabyte file download on Stream 1 does not delay or block a critical 200-byte API response on Stream 3.

```text
Single Underlying TCP Wire:
[ Stream 1: HEADERS ] -> [ Stream 3: HEADERS ] -> [ Stream 1: DATA (Chunk 1) ] ->
[ Stream 3: DATA (Complete) ] -> [ Stream 1: DATA (Chunk 2) ] -> ...
```

Both endpoints reconstruct complete messages by demultiplexing frames based on the 31-bit Stream ID.

---

## 4. Credit-Based Flow Control (`WINDOW_UPDATE`)

TCP already implements flow control via its sliding window. However, because HTTP/2 multiplexes dozens of streams over a single TCP socket, TCP flow control cannot prevent one fast stream from starving other concurrent streams within the application buffer.

### The Two-Tier Window Engine
HTTP/2 implements hop-by-hop flow control at two distinct levels:
1. **Connection-level Flow Control**: Regulates total bytes across all streams combined (Stream ID = 0).
2. **Stream-level Flow Control**: Regulates bytes transferred on each individual stream.

Both peers begin with a default credit window of $65,535$ bytes (`SETTINGS_INITIAL_WINDOW_SIZE`).
When peer A transmits $N$ bytes of `DATA` frames, its available window credit decreases:

$$W_{\text{remaining}} = W_{\text{current}} - N$$

If $W_{\text{remaining}} == 0$, peer A **must cease transmitting** `DATA` frames on that stream until peer B issues a `WINDOW_UPDATE` frame granting additional credits ($W_{\text{new}} = W_{\text{current}} + \Delta$).

---

## 5. Compilable C Implementation: HTTP/2 Binary Frame Header Parser

Compile with: `gcc -O2 -Wall -Wextra h2_frame_parser.c -o h2_frame_parser`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>

#define H2_FRAME_HEADER_SIZE 9

typedef struct {
    uint32_t length;
    uint8_t  type;
    uint8_t  flags;
    uint32_t stream_id;
} h2_frame_header_t;

int parse_h2_header(const uint8_t *buf, h2_frame_header_t *out_hdr) {
    /* Extract 24-bit length (Network Byte Order) */
    out_hdr->length = (buf[0] << 16) | (buf[1] << 8) | buf[2];
    out_hdr->type = buf[3];
    out_hdr->flags = buf[4];

    /* Extract 31-bit stream ID (Mask out reserved top bit) */
    uint32_t raw_stream;
    memcpy(&raw_stream, buf + 5, 4);
    out_hdr->stream_id = ntohl(raw_stream) & 0x7FFFFFFF;

    return 0;
}

const char *get_frame_type_name(uint8_t type) {
    switch (type) {
        case 0x00: return "DATA";
        case 0x01: return "HEADERS";
        case 0x02: return "PRIORITY";
        case 0x03: return "RST_STREAM";
        case 0x04: return "SETTINGS";
        case 0x05: return "PUSH_PROMISE";
        case 0x06: return "PING";
        case 0x07: return "GOAWAY";
        case 0x08: return "WINDOW_UPDATE";
        default:   return "UNKNOWN";
    }
}

int main(void) {
    /* Simulated 9-byte raw HTTP/2 HEADERS frame header:
       Length = 32 bytes (0x000020)
       Type = 0x01 (HEADERS)
       Flags = 0x05 (END_STREAM | END_HEADERS)
       Stream ID = 1 (Client request 1: 0x00000001) */
    uint8_t raw_frame[9] = {
        0x00, 0x00, 0x20,  /* Length: 32 bytes */
        0x01,              /* Type: HEADERS */
        0x05,              /* Flags: END_STREAM (0x1) | END_HEADERS (0x4) */
        0x00, 0x00, 0x00, 0x01 /* Stream ID: 1 */
    };

    h2_frame_header_t hdr;
    parse_h2_header(raw_frame, &hdr);

    printf("=== Decoded HTTP/2 Binary Frame Header ===\n");
    printf("Payload Length: %u bytes\n", hdr.length);
    printf("Frame Type:     0x%02X (%s)\n", hdr.type, get_frame_type_name(hdr.type));
    printf("Flags:          0x%02X\n", hdr.flags);
    printf("Stream ID:      %u (%s-initiated)\n", hdr.stream_id, (hdr.stream_id % 2) ? "Client" : "Server");

    return EXIT_SUCCESS;
}
```

---

## 6. Production Post-Mortem: The HTTP/2 Rapid Reset DDoS Attack (CVE-2023-44487)

### Incident Overview
In October 2023, cloud infrastructure providers (Cloudflare, Google Cloud, AWS) reported the largest distributed denial-of-service attack in internet history, peaking at over **398 million requests per second**. The vector exploited an architectural design flaw in HTTP/2 stream management known as *Rapid Reset*.

### The Attack Mechanism
1. The client opens an HTTP/2 connection.
2. It transmits a `HEADERS` frame to open Stream 1.
3. **Immediately**, without waiting for a server response, the client transmits an `RST_STREAM` frame for Stream 1.
4. The client repeats this loop millions of times over a single TCP connection (`Stream 1 -> RST`, `Stream 3 -> RST`, `Stream 5 -> RST`).
5. **The Asymmetry**: For the client, generating `HEADERS` and `RST_STREAM` consumes negligible CPU and bandwidth. However, for the origin server, receiving `HEADERS` triggers expensive upstream routing, TLS session tracking, database queries, and thread dispatching before the `RST` cancels it.
6. Server CPUs collapsed under the strain of allocating and tearing down millions of concurrent in-memory stream state machines.

### Industry Remediation
1. **RST_STREAM Rate Limiting**: Servers and proxies enforce strict quotas on the maximum allowable ratio of `RST_STREAM` frames per second (e.g. dropping connections if more than 100 resets occur consecutively).
2. **Immediate Pipeline Teardown**: Optimize kernel event loops to prune canceled streams before dispatching backend workers.
---

## 7. The Rise and Fall of HTTP/2 Server Push (`PUSH_PROMISE`)

RFC 7540 originally introduced **Server Push** allowing the server to proactively send resources to the client before the client requested them (e.g. sending `style.css` along with `index.html`).

### The Protocol Mechanics
1. The server transmits a `PUSH_PROMISE` frame (`Type 0x05`) on the client's request stream (Stream 1).
2. The `PUSH_PROMISE` reserves a new even-numbered stream ID (e.g. Stream 2) and contains the anticipated request headers (`:path: /style.css`).
3. The server then pushes `HEADERS` and `DATA` on Stream 2.

### Why Server Push Was Deprecated
In practice, Server Push proved disastrous:
- **Cache Inefficiency**: The server cannot inspect client-side browser cache state. It frequently pushed 500 KB stylesheets that the browser already had cached, wasting cellular bandwidth.
- **Race Conditions**: Browsers often requested the asset *before* the `PUSH_PROMISE` arrived, causing redundant transfers.
- **Removal**: In 2022, Chrome and major browser engines disabled HTTP/2 Server Push by default, replacing it with `103 Early Hints` (`Link: </style.css>; rel=preload`).
---

## 8. Stream State Machine Transitions (RFC 7540 Section 5.1)

Every individual stream in HTTP/2 transitions across well-defined lifecycle states:
```text
                       +--------+
               send PP |        | recv PP
              +--------|  idle  |--------+
              |        |        |        |
              v        +--------+        v
          +-------+                  +-------+
          |reserved|                  |reserved|
          | (local)|                  |(remote)|
          +-------+                  +-------+
              |                          |
              v                          v
          +-------+                  +-------+
          | open  |                  | open  |
          +-------+                  +-------+
              |                          |
              +------------+-------------+
                           |
                           v
                       +--------+
                       | closed |
                       +--------+
```
Transmitting an `RST_STREAM` or exchanging frames marked with `END_STREAM` transitions the stream into the terminal `closed` state, reclaiming stream identifier resources.
