# Day 17: Delayed ACKs & TCP_NODELAY vs TCP_CORK

## 1. Architectural Foundations: Nagle's Algorithm & Delayed ACKs

Two independent optimization algorithms designed in the 1980s create one of the most infamous performance traps in modern distributed systems: **The Nagle + Delayed ACK Deadlock**.

---

## 2. John Nagle's Algorithm (RFC 896 - 1984)

On early Arpanet telnet sessions, typing one character generated a 41-byte packet and a 40-byte ACK. Nagle's algorithm was created to coalesce small writes into full-sized segments:

```python
if unacknowledged_data_in_flight:
    if len(pending_data) >= MSS:
        send_segment()
    else:
        buffer_locally_and_wait_for_ack()
else:
    send_segment_immediately()
```
- If there is **no unacknowledged data in flight**, send immediately (even if $< MSS$).
- If there is **data in flight**, buffer outgoing bytes until either a full MSS is accumulated OR an ACK arrives from the receiver.

---

## 3. Delayed Acknowledgment (RFC 1122 - 1989)

Instead of sending an immediate 40-byte ACK packet for every single arriving segment, the receiver delays sending the ACK:
1. It waits up to **$40\text{ ms to } 200\text{ ms}$** in the hope that the local application will generate response data, allowing the ACK to be piggybacked for free.
2. If a second full-sized MSS segment arrives, an ACK is sent immediately (the "ACK Every Second Segment" rule).

---

## 4. The Catastrophic Interaction: The 40ms Deadlock

When an application performs multiple small writes (such as HTTP request headers followed by a small request body):

```
Client (Nagle Enabled)                                  Server (Delayed ACK Enabled)
  |                                                                |
  | -------- Packet 1: HTTP Headers (300 bytes) -----------------> |
  |                                                                | (Server receives packet)
  | [Client buffers Packet 2 (Body, 200 bytes)]                   | (Server waits up to 40ms
  | [Nagle prevents sending: unacked data in flight!]             |  to piggyback ACK)
  |                                                                |
  |                        *** DEADLOCK (40ms) ***                 |
  |                                                                |
  | <------- Server Delayed ACK Timer Expires (40ms later) -------- |
  |                                                                |
  | -------- Packet 2: HTTP Body (200 bytes) --------------------> |
```
- Client won't send Packet 2 until it receives an ACK for Packet 1.
- Server won't send an ACK for Packet 1 until its $40\text{ ms}$ timer expires!
- **Result: Every RPC or HTTP request suffers an unexplainable 40ms latency penalty!**

---

## 5. Remediation: `TCP_NODELAY` vs `TCP_CORK`

### Disabling Nagle with `TCP_NODELAY`:
```c
int one = 1;
setsockopt(sockfd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
```
Disables Nagle's algorithm completely. Segments are transmitted immediately over the wire regardless of size or in-flight unacknowledged data. **Mandatory for all modern low-latency services (gRPC, Redis, Microservices).**

### `TCP_CORK` (Linux) / `TCP_NOPUSH` (BSD):
Forces the kernel to aggressively buffer all writes until the cork is removed, ideal for prepending HTTP headers before streaming large files with `sendfile()`:
```c
int one = 1, zero = 0;
setsockopt(sockfd, IPPROTO_TCP, TCP_CORK, &one, sizeof(one)); // Cork the socket
write(sockfd, http_headers, header_len);
sendfile(sockfd, file_fd, NULL, file_size);
setsockopt(sockfd, IPPROTO_TCP, TCP_CORK, &zero, sizeof(zero)); // Uncork & flush!
```
