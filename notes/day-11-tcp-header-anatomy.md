# Day 11: TCP Header Anatomy & Control Flags

## 1. Architectural Foundations: The Transmission Control Protocol (TCP)
The Transmission Control Protocol (defined in RFC 793, updated in RFC 9293) provides a reliable, ordered, full-duplex, connection-oriented byte-stream abstraction over the inherently unreliable, best-effort, packet-switched Internet Protocol (IP).

Unlike UDP, which is a thin multiplexing wrapper around IP, TCP encapsulates a complex distributed state machine inside every endpoint. At the heart of this abstraction lies the TCP header.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Data |           |U|A|P|R|S|F|                               |
| Offset| Reserved  |R|C|S|S|Y|I|            Window             |
|       |           |G|K|H|T|N|N|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |        Urgent Pointer         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options                    |    Padding    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             data                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

---

## 2. Field-by-Field Architectural Anatomy

### 1. Source Port & Destination Port (16 bits each)
Identifies the sending and receiving application endpoints. Combined with the source and destination IP addresses and protocol number (6), this forms the **TCP 5-Tuple**:
$$\text{5-Tuple} = (\text{SrcIP}, \text{SrcPort}, \text{DstIP}, \text{DstPort}, \text{Protocol}=6)$$
This tuple uniquely demultiplexes incoming segments to their respective kernel socket control blocks.

### 2. Sequence Number (32 bits)
Identifies the byte offset of the first data byte in this segment relative to the Initial Sequence Number (ISN).
- If the `SYN` flag is set (1), this field contains the ISN, and the first data byte will be at $\text{ISN} + 1$.
- In established data transfer, sequence numbers count **bytes**, not packets!

### 3. Acknowledgment Number (32 bits)
Valid only if the `ACK` flag is set. It contains the value of the **next sequence number the receiver is expecting to receive**.
TCP acknowledgments are **strictly cumulative**: an ACK of $N$ asserts that all bytes from $\text{ISN} + 1$ up to $N - 1$ have been successfully received and placed into the receive queue.

### 4. Data Offset / Header Length (4 bits)
Specifies the length of the TCP header in **32-bit (4-byte) words**.
- Minimum value: `5` ($5 \times 4 = 20\text{ bytes}$, when no options are present).
- Maximum value: `15` ($15 \times 4 = 60\text{ bytes}$, allowing up to 40 bytes of options).

### 5. Control Flags (9 bits in modern RFCs)
From most significant to least significant:
1. **NS (Nonce Sum)**: RFC 3540 ECN-nonce protection against malicious receiver concealment of marked packets.
2. **CWR (Congestion Window Reduced)**: RFC 3168 flag sent by sender indicating it reacted to ECE and reduced its congestion window.
3. **ECE (ECN-Echo)**: RFC 3168 flag. If `SYN=1`, indicates ECN capability. If `SYN=0`, indicates router encountered congestion (CE codepoint in IP header).
4. **URG (Urgent)**: Indicates that the Urgent Pointer field is valid.
5. **ACK (Acknowledgment)**: Indicates that the Acknowledgment Number field is valid. Set on all packets after initial SYN.
6. **PSH (Push)**: Informs receiver to push buffered data immediately to the application layer rather than waiting for buffers to fill.
7. **RST (Reset)**: Aborts connection immediately due to unrecoverable error or invalid state.
8. **SYN (Synchronize)**: Synchronizes sequence numbers to initiate a connection.
9. **FIN (Finish)**: Sender has reached end-of-transmission and requests connection termination.

### 6. Window Size (16 bits)
The number of bytes the receiver is currently willing to accept, beginning with the byte specified in the Acknowledgment Number.
Without the Window Scale option, maximum window size is $2^{16} - 1 = 65,535\text{ bytes}$ (64 KB).

### 7. Checksum (16 bits)
Mandatory 16-bit ones' complement sum covering:
1. The IPv4 or IPv6 **Pseudo-Header** (Source IP, Destination IP, Protocol 6, TCP Length).
2. The entire TCP Header.
3. The TCP Data payload.

### 8. Urgent Pointer (16 bits)
Points to the sequence number of the byte following urgent data (used historically by telnet for interrupt signals). Largely obsolete in modern protocols.

---

## 3. TCP Options: TLV Architecture
If $\text{Data Offset} > 5$, the remaining bytes up to 60 bytes consist of variable-length options structured using **Type-Length-Value (TLV)** encoding:

```
+-------------+-------------+-----------------------------+
| Option-Kind | Option-Len  | Option-Data (Value)         |
|   (1 byte)  |  (1 byte)   | (Option-Len - 2 bytes)      |
+-------------+-------------+-----------------------------+
```

### Essential Modern Options
| Kind | Length | Name | Description |
| :--- | :--- | :--- | :--- |
| **0** | 1 | **End of Option List (EOL)** | Halts options parsing. Pads to 32-bit boundary. |
| **1** | 1 | **No-Operation (NOP)** | 1-byte pad used to align subsequent options on 4-byte boundaries. |
| **2** | 4 | **Maximum Segment Size (MSS)** | Advertised maximum payload bytes sender can receive (e.g. 1460). Only in `SYN`. |
| **3** | 3 | **Window Scale (WSopt)** | Shift count (0-14) to multiply Window Size by $2^S$ (RFC 7323). Only in `SYN`. |
| **4** | 2 | **SACK Permitted** | Advertises selective acknowledgment capability. Only in `SYN`. |
| **5** | Variable | **SACK (Selective ACK)** | Lists up to 4 non-contiguous blocks of received sequence numbers. |
| **8** | 10 | **Timestamps (TSopt)** | Timestamp Value (TSval, 4B) and Echo Reply (TSecr, 4B) for precise RTT and PAWS. |

---

## 4. Production Masterclass: Compilable C TCP Packet Parser

Save as `tcp_parser.c` and compile with `gcc -Wall -Wextra -O2 tcp_parser.c -o tcp_parser`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <arpa/inet.h>

#pragma pack(push, 1)
typedef struct {
    uint16_t src_port;
    uint16_t dst_port;
    uint32_t seq_num;
    uint32_t ack_num;
    uint8_t  data_offset_and_reserved; // 4 bits offset, 4 bits reserved/flags
    uint8_t  flags;                    // CWR, ECE, URG, ACK, PSH, RST, SYN, FIN
    uint16_t window_size;
    uint16_t checksum;
    uint16_t urgent_ptr;
} tcp_header_t;
#pragma pack(pop)

void parse_tcp_options(const uint8_t *options_buf, size_t options_len) {
    printf("  [+] Parsing %zu bytes of TCP Options:\\n", options_len);
    size_t offset = 0;

    while (offset < options_len) {
        uint8_t kind = options_buf[offset];

        if (kind == 0) { // EOL
            printf("    |-- Kind 0: End of Option List (EOL)\\n");
            break;
        }
        if (kind == 1) { // NOP
            printf("    |-- Kind 1: NOP (No-Operation Padding)\\n");
            offset++;
            continue;
        }

        if (offset + 1 >= options_len) break;
        uint8_t len = options_buf[offset + 1];
        if (len < 2 || offset + len > options_len) {
            printf("    |-- [!] Malformed Option Kind %u (Length %u)\\n", kind, len);
            break;
        }

        switch (kind) {
            case 2: { // MSS (Length 4)
                if (len == 4) {
                    uint16_t mss = ntohs(*(const uint16_t *)(options_buf + offset + 2));
                    printf("    |-- Kind 2: Maximum Segment Size (MSS) = %u bytes\\n", mss);
                }
                break;
            }
            case 3: { // Window Scale (Length 3)
                if (len == 3) {
                    uint8_t shift = options_buf[offset + 2];
                    printf("    |-- Kind 3: Window Scale = %u (Multiplier: %u)\\n", shift, 1 << shift);
                }
                break;
            }
            case 4: { // SACK Permitted (Length 2)
                printf("    |-- Kind 4: SACK Permitted\\n");
                break;
            }
            case 8: { // Timestamps (Length 10)
                if (len == 10) {
                    uint32_t tsval = ntohl(*(const uint32_t *)(options_buf + offset + 2));
                    uint32_t tsecr = ntohl(*(const uint32_t *)(options_buf + offset + 6));
                    printf("    |-- Kind 8: Timestamps (TSval=%u, TSecr=%u)\\n", tsval, tsecr);
                }
                break;
            }
            default:
                printf("    |-- Kind %u: Unknown Option (Length %u)\\n", kind, len);
                break;
        }
        offset += len;
    }
}

int main(void) {
    // Construct a synthetic 32-byte TCP SYN packet with Options (MSS, SACK, WSopt)
    uint8_t packet[32];
    memset(packet, 0, sizeof(packet));

    tcp_header_t *hdr = (tcp_header_t *)packet;
    hdr->src_port = htons(54321);
    hdr->dst_port = htons(443);
    hdr->seq_num = htonl(1000000000);
    hdr->ack_num = htonl(0);
    hdr->data_offset_and_reserved = (8 << 4); // 8 * 4 = 32 bytes header
    hdr->flags = 0x02;                        // SYN flag set
    hdr->window_size = htons(65535);
    hdr->checksum = htons(0xABCD);
    hdr->urgent_ptr = htons(0);

    // Options: MSS (4B), SACK Permitted (2B), NOP (1B), Window Scale (3B), NOP (1B), EOL (1B) = 12B
    uint8_t *opt = packet + sizeof(tcp_header_t);
    // MSS = 1460 (0x05B4)
    opt[0] = 2; opt[1] = 4; opt[2] = 0x05; opt[3] = 0xB4;
    // SACK Permitted
    opt[4] = 4; opt[5] = 2;
    // NOP
    opt[6] = 1;
    // Window Scale = 7 (factor 128)
    opt[7] = 3; opt[8] = 3; opt[9] = 7;
    // Padding
    opt[10] = 1; opt[11] = 0;

    printf("====================================================\\n");
    printf("TCP PACKET HEADER DECODER\\n");
    printf("====================================================\\n");

    uint8_t data_offset_words = (hdr->data_offset_and_reserved >> 4);
    size_t header_len_bytes = data_offset_words * 4;

    printf("Source Port       : %u\\n", ntohs(hdr->src_port));
    printf("Destination Port  : %u\\n", ntohs(hdr->dst_port));
    printf("Sequence Number   : %u\\n", ntohl(hdr->seq_num));
    printf("Ack Number        : %u\\n", ntohl(hdr->ack_num));
    printf("Header Length     : %zu bytes (Data Offset = %u words)\\n", header_len_bytes, data_offset_words);
    printf("Flags             : 0x%02X [ %s%s%s%s%s%s%s%s]\\n",
           hdr->flags,
           (hdr->flags & 0x80) ? "CWR " : "",
           (hdr->flags & 0x40) ? "ECE " : "",
           (hdr->flags & 0x20) ? "URG " : "",
           (hdr->flags & 0x10) ? "ACK " : "",
           (hdr->flags & 0x08) ? "PSH " : "",
           (hdr->flags & 0x04) ? "RST " : "",
           (hdr->flags & 0x02) ? "SYN " : "",
           (hdr->flags & 0x01) ? "FIN " : "");
    printf("Window Size       : %u\\n", ntohs(hdr->window_size));
    printf("Checksum          : 0x%04X\\n", ntohs(hdr->checksum));

    if (header_len_bytes > sizeof(tcp_header_t)) {
        parse_tcp_options(packet + sizeof(tcp_header_t), header_len_bytes - sizeof(tcp_header_t));
    }

    return 0;
}
```

---

## 5. Production Post-Mortem: The VPN MTU Blackhole Disaster
### The Outage
A company transitioned its engineering workforce to a WireGuard / IPsec tunnel. Users reported that small SSH commands and Google searches worked perfectly, but any large git push, `npm install`, or file download stalled infinitely after sending 1-2 packets. No error was returned—the connection hung silently until socket timeout.

### Root Cause Analysis
1. Standard Ethernet MTU is **1500 bytes**.
2. Standard TCP MSS on local endpoints: $\text{MSS} = 1500 - 20\text{ (IP)} - 20\text{ (TCP)} = 1460\text{ bytes}$.
3. When encapsulated inside an IPsec/WireGuard tunnel, the tunnel adds 60 to 80 bytes of outer IP and cryptographic headers.
4. The actual maximum MTU inside the tunnel is $1500 - 80 = 1420\text{ bytes}$.
5. When the server transmitted a full 1460-byte payload inside a 1500-byte IP packet with the **Don't Fragment (DF)** bit set, the VPN gateway dropped the packet because it exceeded the tunnel MTU!
6. The VPN gateway attempted to send an ICMP Type 3 Code 4 (`Destination Unreachable, Fragmentation Needed`) back to the server, but an over-zealous enterprise firewall blocked all ICMP traffic. The sender never learned of the drop, creating a **Path MTU Discovery (PMTUD) Black Hole**!

### Architectural Remediation: TCP MSS Clamping
Instead of relying on ICMP, configure the gateway router to perform **TCP MSS Clamping**:
```bash
# Intercept all TCP SYN packets traversing the tunnel and rewrite their MSS option to 1360
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
# OR explicitly clamp:
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
```
This rewrites the Option Kind 2 (MSS) field in-flight during the 3-way handshake, forcing both client and server to negotiate segment payloads that never exceed the tunnel's physical MTU.
