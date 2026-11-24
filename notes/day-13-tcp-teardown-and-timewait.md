# Day 13: TCP 4-Way Teardown & TIME_WAIT 2MSL

## 1. Architectural Foundations: Connection Teardown

Because TCP is a **full-duplex byte stream**, each direction of data transfer operates independently. Closing a TCP connection requires closing each simplex direction independently. This is typically accomplished via a **4-Way Teardown**.

```
    Client (Active Closer)                              Server (Passive Closer)
        ESTABLISHED                                           ESTABLISHED
             |                                                     |
(Step 1)     | ------------------ FIN (seq=u) -------------------> | CLOSE_WAIT
  FIN_WAIT_1 |                                                     |
             |                                                     |
(Step 2)     | <----------------- ACK (ack=u+1) ------------------ |
  FIN_WAIT_2 |                                                     |
             |           [Server Can Still Send Data!]             |
             |                                                     |
(Step 3)     | <----------------- FIN (seq=w, ack=u+1) ----------- | LAST_ACK
  TIME_WAIT  |                                                     |
             |                                                     |
(Step 4)     | ------------------ ACK (ack=w+1) -----------------> | CLOSED
             |                                                     |
     [Wait 2MSL = 60s]
             |
          CLOSED
```

---

## 2. Step-by-Step State Transition Analysis

1. **Active Closer Calls `close()`**: Sends `FIN (seq=u)`. Transitions to `FIN_WAIT_1`.
2. **Passive Closer Receives `FIN`**: Kernel immediately sends `ACK (ack=u+1)`. Transitions to `CLOSE_WAIT`. Active closer enters `FIN_WAIT_2`.
   - **Half-Closed State**: The active closer can no longer *write* data, but it can still *read* data sent by the server!
3. **Passive Closer Finishes Sending Data**: Calls `close()`. Sends `FIN (seq=w)`. Transitions to `LAST_ACK`. Active closer receives `FIN`, sends `ACK (ack=w+1)`, and enters **`TIME_WAIT`**.
4. **Passive Closer Receives Final `ACK`**: Instantly transitions to `CLOSED` and destroys the socket.

---

## 3. The Mystery & Mathematics of the `TIME_WAIT` State

The endpoint that performs the **Active Close** must remain in the `TIME_WAIT` state for **$2 \times MSL$** (Maximum Segment Lifetime), which in Linux is fixed at **60 seconds** ($MSL = 30\text{ seconds}$).

Why must the socket remain trapped in `TIME_WAIT` for 60 seconds?

### Reason 1: Ensuring Reliable Final ACK Delivery
Suppose Step 4 (`ACK`) is lost in transit across the internet:
- The server (in `LAST_ACK`) will timeout and retransmit its `FIN` packet.
- If the client transitioned immediately to `CLOSED`, it would reply to the retransmitted `FIN` with a `RST` (Reset) packet, tricking the server into believing an abnormal network abort occurred!
- Because the client is in `TIME_WAIT`, it receives the retransmitted `FIN` and cleanly retransmits the final `ACK`.

### Reason 2: Preventing Stale Duplicate Packet Corruption
In IP networks, packets can be delayed, buffered in router queues, and delivered out-of-order minutes later.
- If a connection closed instantly, and a new connection was established between the exact same 5-tuple (`client_ip, client_port, server_ip, server_port`), a wandering, delayed duplicate segment from the *old* connection could arrive and be injected into the *new* connection's data stream, corrupting data!
- Waiting $2 \times MSL$ guarantees that all duplicate segments belonging to the previous incarnation have expired and been discarded by router TTL limits.

### Production Socket Exhaustion & `SO_REUSEADDR`
On high-throughput HTTP reverse proxies handling 50,000 requests/second, thousands of sockets accumulate in `TIME_WAIT`, exhausting the client's ephemeral port pool (`net.ipv4.ip_local_port_range`). 
Remediations include:
- `net.ipv4.tcp_tw_reuse = 1` (Safely reuses `TIME_WAIT` sockets for outgoing connections if timestamps increase).
- Enabling HTTP/1.1 Keep-Alive or HTTP/2 connection pooling to eliminate frequent handshake/teardown cycles.
