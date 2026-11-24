# Day 12: TCP 3-Way Handshake & Sequence Numbers

## 1. Architectural Foundations: Connection Establishment

Before two endpoints can exchange stream data over TCP, they must synchronize sequence numbers, agree on buffer sizes, and establish bidirectional state. This is accomplished via the **TCP 3-Way Handshake**.

```
      Client (Active Opener)                            Server (Passive Opener)
             CLOSED                                              LISTEN
                |                                                   |
 (Step 1)       | ------------ SYN (seq=x, MSS=1460, WSCALE=7) ---> | SYN_RCVD
   SYN_SENT     |                                                   |
                |                                                   |
 (Step 2)       | <--- SYN-ACK (seq=y, ack=x+1, MSS=1460, WSCALE=7) |
  ESTABLISHED   |                                                   |
                |                                                   |
 (Step 3)       | ---------------- ACK (seq=x+1, ack=y+1) --------> | ESTABLISHED
                |                                                   |
     [Data Exchange: HTTP/TLS]                          [Data Exchange: HTTP/TLS]
```

---

## 2. Step-by-Step Packet Exchange Analysis

### Step 1: The `SYN` Packet (Client $\to$ Server)
- Flags: `SYN=1, ACK=0`.
- Sequence Number: $x$ (Client Initial Sequence Number - $ISN_C$).
- Acknowledgment Number: $0$ (Unused).
- Options: MSS, SACK Permitted, Window Scale factor.
- State: Client transitions from `CLOSED` to `SYN_SENT`.

### Step 2: The `SYN-ACK` Packet (Server $\to$ Client)
- Flags: `SYN=1, ACK=1`.
- Sequence Number: $y$ (Server Initial Sequence Number - $ISN_S$).
- Acknowledgment Number: $x + 1$ (Acknowledges receipt of client's SYN byte).
- State: Server allocates connection buffer in **SYN Backlog** and transitions from `LISTEN` to `SYN_RCVD`.

### Step 3: The `ACK` Packet (Client $\to$ Server)
- Flags: `SYN=0, ACK=1`.
- Sequence Number: $x + 1$.
- Acknowledgment Number: $y + 1$ (Acknowledges receipt of server's SYN byte).
- State: Client transitions to `ESTABLISHED`. Server moves connection from SYN Backlog to **Accept Queue** and transitions to `ESTABLISHED`.

> [!NOTE]
> Even though a `SYN` packet carries $0$ bytes of user data payload, **the SYN flag logically consumes exactly 1 sequence number**! This ensures that the SYN packet itself can be reliably acknowledged by $ack = seq + 1$.

---

## 3. The Security & Mathematics of Initial Sequence Numbers (ISN)

In early TCP implementations (RFC 793), the $ISN$ was generated using a simple linear clock: $ISN = (ISN + 250,000) \pmod{2^{32}}$ every second.
This created a catastrophic vulnerability: **TCP Blind Spoofing & Connection Hijacking (Kevin Mitnick / Tsutomu Shimomura 1994)**. An off-path attacker could predict the exact $ISN$ of a trusted host and forge packets.

### Modern RFC 6528 Cryptographic ISN Generation
Modern Linux kernels generate Initial Sequence Numbers using a cryptographically secure pseudorandom function:

$$ISN = M + \text{PRF}_{K}(\text{Client IP}, \text{Client Port}, \text{Server IP}, \text{Server Port}) \pmod{2^{32}}$$

Where:
- $M$ is a 4-microsecond monotonic hardware clock counter.
- $\text{PRF}_K$ is a cryptographic Pseudo-Random Function (such as SipHash or SHA-256) keyed with a secret 128-bit key $K$ generated at boot.
This ensures that sequence numbers are unpredictable to attackers while maintaining temporal uniqueness across 5-tuple incarnations.

---

## 4. SYN Flood Denial of Service & SYN Cookies

In a standard handshake, when a server receives a `SYN`, it allocates a stateful socket structure (`struct sock`) in kernel RAM. An attacker spoofing random source IPs can flood millions of `SYN` packets per second without ever sending the completing `ACK`. The server's **SYN Backlog** overflows, causing it to drop legitimate connections.

### The Solution: SYN Cookies (`net.ipv4.tcp_syncookies = 1`)
When the SYN backlog fills up, the Linux kernel stops allocating state in RAM. Instead, it encodes all connection state directly inside the 32-bit $ISN_S$ sent back in the `SYN-ACK`:

```
 31             26 25             23 22                            0
+-----------------+-----------------+-------------------------------+
| Slow Clock Counter| Encoded MSS Index| Cryptographic MAC Hash        |
|     (6 Bits)    |     (3 Bits)    |           (23 Bits)           |
+-----------------+-----------------+-------------------------------+
```
When the client replies with Step 3 (`ACK`), its acknowledgment number equals $ISN_S + 1$. The server subtracts $1$, verifies the 23-bit cryptographic hash, unpacks the MSS, and instantiates the connection socket **without ever having stored memory for the initial SYN**!
