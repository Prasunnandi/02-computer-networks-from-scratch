# Day 57: The WebSocket Protocol (RFC 6455): HTTP Upgrade Handshake, Binary Framing, and Client Masking

HTTP is fundamentally a request-response protocol driven by the client: the server cannot push data to the client without the client first querying the server. While techniques like HTTP long-polling and Server-Sent Events (SSE) provided half-duplex workarounds, modern real-time interactive systems (financial tickers, collaborative whiteboards, multiplayer gaming, chat) demand low-latency, full-duplex communication over a single persistent socket. The **WebSocket Protocol** (RFC 6455) resolves this by executing an initial HTTP handshake to upgrade the connection, followed by bidirectional binary framing with minimal 2-byte overhead.

---

## 1. The HTTP 101 Switching Protocols Handshake

A WebSocket connection begins its lifecycle as a standard HTTP/1.1 request over TCP port 80 or 443. The client initiates an **Upgrade** handshake:

```text
Client Handshake Request:
GET /chat HTTP/1.1


Host: server.example.com


Upgrade: websocket


Connection: Upgrade


Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==


Sec-WebSocket-Version: 13





```

### The Cryptographic Accept Derivation Formula
To prove to the client that the server understands the WebSocket protocol (and is not an errant caching proxy echoing headers), the server must calculate the `Sec-WebSocket-Accept` header.

The server takes the client's `Sec-WebSocket-Key` string, appends the RFC 6455 globally unique identifier (GUID) constant `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`, computes the SHA-1 cryptographic digest, and encodes the resulting 20-byte hash in Base64:

$$\text{GUID} = \text{"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"}$$

$$\text{Accept} = \text{Base64}\left(\text{SHA1}\left(\text{Sec-WebSocket-Key} \parallel \text{GUID}\right)\right)$$

```text
Server Handshake Response:
HTTP/1.1 101 Switching Protocols


Upgrade: websocket


Connection: Upgrade


Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=





```
Upon transmission of the trailing `



`, the HTTP parser is completely detached from the TCP socket. The socket immediately enters pure WebSocket binary framing mode.

---

## 2. WebSocket Binary Framing Layer Architecture

Unlike textual HTTP, WebSocket traffic is structured into discrete binary frames defined by an extensible binary header ranging from 2 to 14 bytes in length:

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
```

### Deconstructing the Binary Header Fields
- **FIN (1 bit)**: Indicates if this is the final fragment of a message (1 = Final, 0 = Fragmented).
- **RSV1, RSV2, RSV3 (1 bit each)**: Reserved for protocol extensions (e.g., `permessage-deflate` compression). Must be 0 unless negotiated.
- **Opcode (4 bits)**:
  - `0x0`: Continuation Frame
  - `0x1`: Text Frame (UTF-8 encoded)
  - `0x2`: Binary Frame (Arbitrary binary blob)
  - `0x8`: Connection Close Handshake
  - `0x9`: Ping (Heartbeat keepalive)
  - `0xA`: Pong (Heartbeat response)
- **MASK (1 bit)**: Defines whether the payload data is obfuscated with a 4-byte XOR masking key. **Mandatory for all client-to-server frames!**
- **Payload Length (7 bits, 7+16 bits, or 7+64 bits)**:
  - $0 \le \text{Len} \le 125$: Actual length is the 7-bit value.
  - $\text{Len} == 126$: Following 16 bits represent unsigned integer length (up to 64 KB).
  - $\text{Len} == 127$: Following 64 bits represent unsigned 64-bit length (up to 16 Exabytes).

---

## 3. Mathematical XOR Client Masking & Middlebox Cache Poisoning Defense

RFC 6455 strictly mandates: **All frames transmitted from Client to Server must be masked. If an unmasked frame is received by a server, the server must close the connection immediately with status code 1002 (Protocol Error).**

### Why Are Client Frames Masked?
Masking is **not** encryption. Its sole purpose is to defeat **Middlebox Cache Poisoning Attacks**.
In the early days of WebSockets, malicious JavaScript running in a browser could open a raw WebSocket connection through an enterprise caching proxy. By sending raw byte sequences matching HTTP requests (`GET /bank_script.js HTTP/1.1`), the proxy was tricked into parsing the WebSocket body as a pipelined HTTP request, caching malicious code and serving it to other enterprise users.
By XORing the payload with a random 4-byte key on the client, the byte sequence on the wire is completely randomized, preventing transparent proxies from detecting embedded HTTP syntax.

### The XOR Masking Algorithm
Let $K = (K_0, K_1, K_2, K_3)$ be the 4-byte random masking key.
Let $P_i$ be the $i$-th byte of the original unmasked payload.
The masked wire byte $M_i$ is computed as:

$$M_i = P_i \oplus K_{i \pmod 4}$$

Because XOR is self-inverting ($A \oplus B \oplus B = A$), unmasking on the server executes the identical mathematical operation:

$$P_i = M_i \oplus K_{i \pmod 4}$$

---

## 4. Compilable C Implementation: WebSocket Frame Builder & Unmasker

Compile with: `gcc -O2 -Wall -Wextra ws_codec.c -o ws_codec`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

void unmask_payload(uint8_t *payload, size_t len, const uint8_t *mask_key) {
    for (size_t i = 0; i < len; i++) {
        payload[i] ^= mask_key[i % 4];
    }
}

int main(void) {
    const char *message = "Hello, WebSocket Full-Duplex World!";
    size_t msg_len = strlen(message);
    uint8_t mask_key[4] = { 0x1A, 0x2B, 0x3C, 0x4D };

    /* Construct Masked Client Text Frame (Opcode 0x1) */
    uint8_t wire_frame[256];
    wire_frame[0] = 0x81; /* FIN=1, Opcode=0x1 (Text) */
    wire_frame[1] = 0x80 | (uint8_t)msg_len; /* MASK=1, Length < 126 */

    /* Copy 4-byte Masking Key */
    memcpy(wire_frame + 2, mask_key, 4);

    /* Copy and mask payload */
    uint8_t *frame_payload = wire_frame + 6;
    for (size_t i = 0; i < msg_len; i++) {
        frame_payload[i] = (uint8_t)message[i] ^ mask_key[i % 4];
    }

    size_t total_frame_size = 2 + 4 + msg_len;
    printf("Constructed RFC 6455 Client Frame (%zu total bytes on wire):\n", total_frame_size);
    for (size_t i = 0; i < total_frame_size; i++) {
        printf("%02X ", wire_frame[i]);
    }
    printf("\n\n");

    /* Server Unmasking Demonstration */
    printf("--- Server Receiver Processing ---\n");
    int fin = (wire_frame[0] >> 7) & 0x01;
    int opcode = wire_frame[0] & 0x0F;
    int is_masked = (wire_frame[1] >> 7) & 0x01;
    size_t rx_len = wire_frame[1] & 0x7F;

    printf("Header Decoded: FIN=%d, Opcode=0x%X, Masked=%d, PayloadLen=%zu\n",
           fin, opcode, is_masked, rx_len);

    uint8_t rx_mask[4];
    memcpy(rx_mask, wire_frame + 2, 4);

    uint8_t decoded_buf[256];
    memcpy(decoded_buf, wire_frame + 6, rx_len);
    unmask_payload(decoded_buf, rx_len, rx_mask);
    decoded_buf[rx_len] = '\0';

    printf("Server Decoded Payload String: \"%s\"\n", decoded_buf);
    return EXIT_SUCCESS;
}
```

---

## 5. Heartbeat Keepalive Mechanics: Ping and Pong Frames

Because WebSocket connections remain idle between asynchronous events, stateful firewalls and NAT routers drop connections after typical inactivity timeouts ($60$ to $300$ seconds).

WebSocket resolves this via native control frames:
- **Ping (`Opcode 0x9`)**: Emitted periodically by either peer with arbitrary application data.
- **Pong (`Opcode 0xA`)**: When a peer receives a Ping, it **must** return an identical Pong frame containing the exact payload bytes of the Ping frame as quickly as possible.
Control frames can be interleaved directly into the middle of fragmented data frames without interrupting transmission.
---

## 6. RFC 6455 Close Status Codes & Graceful Teardown Handshake

Terminating a WebSocket connection requires a coordinated two-way control frame exchange (`Opcode 0x8`):

1. Endpoint A transmits a `Close` frame containing a 2-byte unsigned integer status code and an optional UTF-8 reason string.
2. Endpoint B receives the Close frame and **must** echo back its own Close frame.
3. The underlying TCP socket is then closed cleanly via standard `FIN` handshake.

### Common RFC 6455 Close Codes
- **`1000` (Normal Closure)**: Purpose for which connection was established has completed.
- **`1001` (Going Away)**: Server shutdown or browser navigating away from page.
- **`1002` (Protocol Error)**: Peer violated binary framing rules (e.g., unmasked client frame).
- **`1003` (Unsupported Data)**: Received binary data when only text was negotiated.
- **`1006` (Abnormal Closure)**: Internal pseudo-code; connection dropped without receiving a Close frame (TCP reset, network drop).
