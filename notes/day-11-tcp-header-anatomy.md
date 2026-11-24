# Day 11: TCP Header Anatomy & Control Flags

## 1. Architectural Foundations: The Transmission Control Protocol (TCP)

While the Internet Protocol (IPv4/IPv6) provides a best-effort, connectionless, unreliable datagram delivery service, the **Transmission Control Protocol (TCP)** (specified in RFC 793 and modernized in RFC 9293) builds a reliable, full-duplex, ordered byte-stream abstraction on top of it.

To achieve this, every TCP segment carries an extensive header ranging from **20 bytes** (minimum, with no options) up to **60 bytes** (maximum, with 40 bytes of options).

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

## 2. Field-by-Field Decomposition & Bitfield Layouts

1. **Source Port (16 Bits)**: Port number of the sending endpoint ($0\text{ to } 65535$).
2. **Destination Port (16 Bits)**: Port number of the receiving endpoint.
3. **Sequence Number (32 Bits)**:
   - In a segment with `SYN=1`, this is the **Initial Sequence Number (ISN)**.
   - In a normal segment with `SYN=0`, this is the sequence number of the very first data byte in this segment.
4. **Acknowledgment Number (32 Bits)**:
   - Valid only when the `ACK` flag is set.
   - Contains the *next expected sequence number* the receiver expects to receive ($Last\text{ Received Byte } + 1$).
5. **Data Offset (Header Length) (4 Bits)**:
   - Number of 32-bit (4-byte) words in the TCP header.
   - Minimum value: $5$ ($5 \times 4 = 20\text{ bytes}$). Maximum value: $15$ ($15 \times 4 = 60\text{ bytes}$).
6. **Reserved (3 or 4 Bits)**: Must be zero.
7. **Control Flags (9 Bits total in modern RFCs)**:
   - **`NS` (Nonce Sum - RFC 3540)**: ECN Concealment Protection.
   - **`CWR` (Congestion Window Reduced - RFC 3168)**: Set by sender to acknowledge an ECN notification.
   - **`ECE` (ECN-Echo - RFC 3168)**: Set by receiver if router experienced network congestion.
   - **`URG` (Urgent)**: Urgent pointer field is valid.
   - **`ACK` (Acknowledgment)**: Acknowledgment field is valid (set on almost every packet after handshake).
   - **`PSH` (Push)**: Informs receiver to push buffered data to user-space application immediately without waiting for full buffers.
   - **`RST` (Reset)**: Aborts connection due to error, crash, or non-existent port.
   - **`SYN` (Synchronize)**: Synchronizes sequence numbers during connection establishment.
   - **`FIN` (Finish)**: Sender has finished transmitting data; initiates connection teardown.
8. **Window Size (16 Bits)**: Number of bytes the receiver's receive buffer can currently accept for flow control.
9. **Checksum (16 Bits)**: Mandatory Internet Checksum computed over the TCP Header, Payload, and a 12-byte **IPv4 Pseudo-Header**.
10. **Urgent Pointer (16 Bits)**: Offset added to Sequence Number pointing to urgent out-of-band data (rarely used today).
11. **Options (0 to 40 Bytes)**: Variable-length extensions (MSS, Window Scale, SACK, Timestamps).

---

## 3. Dissecting Common TCP Options

Options are encoded in Type-Length-Value (**TLV**) format:

```
+---------------+---------------+-------------------------------+
|  Option Kind  | Option Length |          Option Data          |
|    (1 byte)   |    (1 byte)   |      (Length - 2 bytes)       |
+---------------+---------------+-------------------------------+
```

- **Kind 0 (End of Option List - EOL)**: 1 byte. Marks the end of options.
- **Kind 1 (No-Operation - NOP)**: 1 byte. Used for 4-byte boundary padding.
- **Kind 2 (Maximum Segment Size - MSS)**: 4 bytes. Advertises maximum segment payload sender can receive (e.g. $1460\text{ bytes}$ for Ethernet). Sent only during `SYN`.
- **Kind 3 (Window Scale - WSCALE)**: 3 bytes. Scales the 16-bit Window field by $2^{\text{shift}}$, allowing window buffers up to $1\text{ GB}$ on high-BDP links.
- **Kind 4 (SACK Permitted)**: 2 bytes. Advertises support for Selective Acknowledgments.
- **Kind 8 (Timestamps)**: 10 bytes. Carries `TSval` (sender clock) and `TSecr` (echo reply), used for exact RTT measurement and PAWS (Protection Against Wrapped Sequences).
