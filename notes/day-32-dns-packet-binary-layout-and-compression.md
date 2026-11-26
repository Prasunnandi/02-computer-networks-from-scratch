# Day 32: DNS Packet Binary Layout & Name Compression

## 1. Architectural Foundations: RFC 1035 Wire Format
Unlike modern text-based protocols (like HTTP/1.1 or JSON REST APIs), the Domain Name System was designed in 1987 to operate with minimal byte overhead over low-speed 56 Kbps links.
Every DNS query and response is an exact binary bitstream transmitted over UDP port 53.

A complete DNS message consists of five distinct sections:
```
+---------------------------------------------------+
|                  Header (12 bytes)                |
+---------------------------------------------------+
|               Question Section                    |
+---------------------------------------------------+
|                Answer Section                     |
+---------------------------------------------------+
|              Authority Section                    |
+---------------------------------------------------+
|             Additional Section                    |
+---------------------------------------------------+
```

---

## 2. The 12-Byte DNS Header Layout
The DNS header is fixed at exactly 12 bytes (96 bits) with the following bitfield layout:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Transaction ID (16)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|QR|   Opcode  |AA|TC|RD|RA| Z |AD|CD|           RCODE          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    QDCOUNT (Question Count)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     ANCOUNT (Answer Count)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    NSCOUNT (Authority Count)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    ARCOUNT (Additional Count)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Detailed Flag Definitions:
- **`ID` (16 bits)**: Identifier assigned by the client to match queries with incoming responses.
- **`QR` (1 bit)**: `0` = Query, `1` = Response.
- **`Opcode` (4 bits)**: `0` = Standard Query (`QUERY`), `1` = Inverse Query (`IQUERY`), `2` = Server Status (`STATUS`).
- **`AA` (1 bit)**: Authoritative Answer. Set if the responding server owns the zone.
- **`TC` (1 bit)**: Truncated. Set if message exceeded 512 bytes over UDP! (Triggers fallback to TCP).
- **`RD` (1 bit)**: Recursion Desired. Set by client if resolver should recursively query upstream.
- **`RA` (1 bit)**: Recursion Available. Set by server if it supports recursive lookups.
- **`Z` (1 bit)**: Reserved zero bit.
- **`AD` (1 bit)**: Authentic Data (DNSSEC). Verified by cryptographic signature.
- **`CD` (1 bit)**: Checking Disabled (DNSSEC). Tells resolver to skip local validation.
- **`RCODE` (4 bits)**: Return Code:
  - `0` = `NOERROR` (Success)
  - `1` = `FORMERR` (Format Error)
  - `2` = `SERVFAIL` (Server Failure)
  - `3` = `NXDOMAIN` (Non-Existent Domain)
  - `5` = `REFUSED` (Query Refused by Policy)

---

## 3. Label Wire Encoding & Domain Name Compression
Domain names in DNS are NOT stored as dot-delimited strings (`"google.com"`).
Instead, they are encoded as a series of **length-prefixed labels**:
- Each label starts with a 1-byte length integer, followed by the raw ASCII characters.
- The root domain is represented by a terminating zero byte (`0x00`).

Example: `"www.google.com"`
```
[0x03] 'w' 'w' 'w' [0x06] 'g' 'o' 'o' 'g' 'l' 'e' [0x03] 'c' 'o' 'm' [0x00]
```

### RFC 1035 Name Compression (Pointer Offsets)
In a typical DNS response (e.g. multiple `A` and `NS` records), the domain name `example.com` would be repeated dozens of times, quickly blowing past the 512-byte UDP limit.
To prevent redundancy, RFC 1035 specifies **DNS Pointer Compression**:
If the top two bits of a length byte are set to `11` (`0xC0`), the remaining 14 bits represent an **offset pointer** from the start of the DNS message!

```
+---------------------------------------------------------------+
| 1  1 |               14-bit Byte Offset                       |
+---------------------------------------------------------------+
```
- `0xC00C`: Jump to byte offset `12` (the start of the Question section).
- When a parser encounters `0xC0`, it pauses reading, seeks to offset `12`, reads the labels from there, and seamlessly reconstructs the full domain name!

---

## 4. Compilable C Program: Packing and Unpacking DNS Packets
```c
/*
 * dns_packet_dissector.c - Dissects a raw 12-byte DNS header and question
 * Compile: gcc -O2 -Wall dns_packet_dissector.c -o dns_packet_dissector
 */
#include <stdio.h>
#include <stdint.h>
#include <arpa/inet.h>

typedef struct __attribute__((packed)) {
    uint16_t id;
    uint16_t flags;
    uint16_t qdcount;
    uint16_t ancount;
    uint16_t nscount;
    uint16_t arcount;
} dns_header_t;

int main(void) {
    /* Sample raw DNS query for "google.com" (Type A, Class IN) */
    unsigned char wire_query[] = {
        0x1A, 0x2B,             /* Transaction ID: 0x1A2B */
        0x01, 0x00,             /* Flags: RD=1 (Standard Query) */
        0x00, 0x01,             /* QDCOUNT = 1 */
        0x00, 0x00,             /* ANCOUNT = 0 */
        0x00, 0x00,             /* NSCOUNT = 0 */
        0x00, 0x00,             /* ARCOUNT = 0 */
        /* Question Section: */
        0x06, 'g', 'o', 'o', 'g', 'l', 'e',
        0x03, 'c', 'o', 'm',
        0x00,                   /* Null terminator */
        0x00, 0x01,             /* Type: A (1) */
        0x00, 0x01              /* Class: IN (1) */
    };

    dns_header_t *hdr = (dns_header_t *)wire_query;
    uint16_t id = ntohs(hdr->id);
    uint16_t flags = ntohs(hdr->flags);
    uint16_t qd = ntohs(hdr->qdcount);

    printf("=========================================\n");
    printf("RFC 1035 DNS BINARY PACKET DISSECTION\n");
    printf("=========================================\n");
    printf("Transaction ID : 0x%04X (%u)\n", id, id);
    printf("Query/Response : %s\n", (flags & 0x8000) ? "RESPONSE" : "QUERY");
    printf("Opcode         : %u (Standard Query)\n", (flags >> 11) & 0x0F);
    printf("Recursion Des  : %s\n", (flags & 0x0100) ? "YES (RD=1)" : "NO");
    printf("Question Count : %u\n", qd);

    /* Parse Question Labels */
    unsigned char *ptr = wire_query + sizeof(dns_header_t);
    printf("Decoded Domain : ");
    while (*ptr != 0) {
        uint8_t len = *ptr++;
        for (int i = 0; i < len; i++) {
            putchar(*ptr++);
        }
        if (*ptr != 0) putchar('.');
    }
    putchar('\n');
    ptr++; /* Skip null byte */

    uint16_t qtype = ntohs(*(uint16_t *)ptr);
    ptr += 2;
    uint16_t qclass = ntohs(*(uint16_t *)ptr);
    printf("Query Type     : %u (%s)\n", qtype, (qtype == 1) ? "A (IPv4)" : "OTHER");
    printf("Query Class    : %u (%s)\n", qclass, (qclass == 1) ? "IN (Internet)" : "OTHER");
    printf("=========================================\n");

    return 0;
}
```

---

## 5. Production War Story: The DNS Pointer Compression Infinite Loop Vulnerability
In 2020, security researchers audited open-source embedded DNS stub resolvers (including `uClibc` and older `dnsmasq` versions).
They discovered a catastrophic denial-of-service vulnerability (**CVE-2020-13576**):
What happens if a malicious DNS server returns a packet containing:
Offset `0x10`: `0xC010` (A compression pointer pointing to itself!)?
Naively written parsers followed the offset:
- Read byte at `0x10` $	o$ offset is `0x10` $	o$ jump to `0x10` $	o$ jump to `0x10`...
The parser entered an **infinite recursive loop**, consuming 100% CPU and freezing routers, IoT devices, and smart appliances worldwide.
Modern RFC-compliant DNS parsers strictly track a `pointer_jumps` counter (capping jumps at 8 to 16) and verify that pointer targets only jump **backwards** to previously parsed offsets.
---

## 6. Hexdump Byte-by-Byte Wire Analysis
Let's analyze a real 29-byte DNS query for `google.com` (Type A) byte by byte:

```
Offset  Hex Data                               ASCII / Field
0000:   A1 B2                                  Transaction ID = 0xA1B2
0002:   01 00                                  Flags: RD=1 (Standard Query)
0004:   00 01                                  QDCOUNT = 1 Question
0006:   00 00                                  ANCOUNT = 0 Answers
0008:   00 00                                  NSCOUNT = 0 Authorities
000A:   00 00                                  ARCOUNT = 0 Additionals
000C:   06 67 6F 6F 67 6C 65                   Length 6, "google"
0013:   03 63 6F 6D                            Length 3, "com"
0017:   00                                     Length 0 (Root null terminator)
0018:   00 01                                  QTYPE = 1 (Type A)
001A:   00 01                                  QCLASS = 1 (Class IN)
```

---

## 7. Wire Parsing Algorithms: Handling Cyclic Pointer Attacks
When writing a high-performance DNS packet dissector, a critical security check is preventing cyclic pointer graphs:
```c
int decompress_name(const uint8_t *packet, size_t packet_len, size_t offset, char *out, size_t out_len) {
    size_t jumps = 0;
    size_t max_jumps = 16;
    size_t out_pos = 0;

    while (offset < packet_len) {
        uint8_t len = packet[offset];
        if (len == 0) { offset++; break; } /* End of name */

        if ((len & 0xC0) == 0xC0) { /* Pointer detected */
            if (offset + 1 >= packet_len) return -1;
            uint16_t ptr = ((len & 0x3F) << 8) | packet[offset + 1];
            if (++jumps > max_jumps || ptr >= offset) return -1; /* Prevent cyclic jump */
            offset = ptr;
            continue;
        }

        offset++;
        if (out_pos + len + 1 >= out_len || offset + len > packet_len) return -1;
        memcpy(out + out_pos, packet + offset, len);
        out_pos += len;
        out[out_pos++] = '.';
        offset += len;
    }
    out[out_pos ? out_pos - 1 : 0] = '\0';
    return 0;
}
```
---

## 8. Comprehensive Wireshark & CLI Packet Diagnostics
```bash
# Capture raw DNS query and response packets with full hex/ASCII payload:
tcpdump -i eth0 -nn -X "udp port 53"

# Wireshark display filter for compressed DNS pointer labels:
# dns.flags.response == 1 && frame matches "\xc0"

# Verify DNS packet format using dig with raw buffer inspection:
dig +qr +hexdump example.com A
```

---

## 9. Production Verification Checklist & Architecture Audit
- [ ] Ensure all custom DNS parsing engines enforce a strict maximum jump limit (max 16) on compression pointers to prevent cyclic loop denial of service.
- [ ] Verify that incoming response Transaction IDs strictly match outgoing query IDs.
- [ ] Confirm that all DNS header multi-byte fields (`id`, `flags`, `qdcount`, `ancount`) are properly converted using `ntohs()` and `htons()`.
