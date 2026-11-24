# Day 13: TCP 4-Way Teardown & TIME_WAIT 2MSL

## 1. Architectural Foundations: Connection Termination
Because TCP is a **full-duplex** protocol, each simplex direction of the connection must be shut down independently. A host signals that it has finished sending data by transmitting a segment with the `FIN` control bit set.

```
CLIENT (Active Close)                            SERVER (Passive Close)
State: ESTABLISHED                               State: ESTABLISHED
      |                                                |
      | 1. App calls close()                           |
      | ------------- FIN (seq=u) -------------------> |
      |                                                | State: CLOSE_WAIT
State: FIN_WAIT_1                                      |
      | <------------ ACK (ack=u+1) ------------------ | 2. Kernel returns EOF to app
      |                                                |
State: FIN_WAIT_2                                      |
      |                                                | 3. App finishes & calls close()
      | <------------ FIN (seq=w, ack=u+1) ----------- |
      |                                                | State: LAST_ACK
State: TIME_WAIT                                       |
      | ------------- ACK (ack=w+1) -----------------> |
      |                                                | State: CLOSED
      | [Waits 2 * MSL (e.g. 60 seconds)]              |
      v                                                v
State: CLOSED
```

---

## 2. Active Close vs Passive Close State Transitions

### The Active Close Sequence
The endpoint that initiates the termination:
1. `ESTABLISHED` $\xrightarrow{\text{close() / send FIN}}$ `FIN_WAIT_1`.
2. `FIN_WAIT_1` $\xrightarrow{\text{receive ACK}}$ `FIN_WAIT_2` (half-closed: cannot send, can still receive).
3. `FIN_WAIT_2` $\xrightarrow{\text{receive FIN}}$ `TIME_WAIT`.
4. `TIME_WAIT` $\xrightarrow{\text{timer expires (2MSL)}}$ `CLOSED`.

### The Passive Close Sequence
The endpoint that receives the initial FIN:
1. `ESTABLISHED` $\xrightarrow{\text{receive FIN / send ACK}}$ `CLOSE_WAIT`.
   - The kernel delivers an EOF (0 bytes) to userspace `read()`.
2. `CLOSE_WAIT` $\xrightarrow{\text{userspace calls close() / send FIN}}$ `LAST_ACK`.
3. `LAST_ACK` $\xrightarrow{\text{receive final ACK}}$ `CLOSED`.

---

## 3. Mathematical Proof & Necessity of the 2MSL TIME_WAIT State
The **Maximum Segment Lifetime (MSL)** is the maximum time a packet can exist within an IP network before being discarded by router TTL expiration. RFC 793 specifies $MSL = 120\text{ seconds}$; modern Linux kernels hardcode $MSL = 60\text{ seconds}$, making:
$$2MSL = 2 \times 60\text{s} = 120\text{ seconds} \quad (\text{or } 60\text{s in TCP_TIMEWAIT_LEN})$$

There are **two critical mathematical reasons** why the active closer MUST remain in `TIME_WAIT` for $2MSL$:

### Reason 1: Reliable Termination of the Full-Duplex Channel
Consider if Client sent the final `ACK` and transitioned directly to `CLOSED`:
- If that final `ACK` is lost in transit, Server retransmits its `FIN`.
- If Client is already `CLOSED`, it responds with a `RST`!
- Server treats `RST` as an abnormal communication abort rather than a clean termination.
By remaining in `TIME_WAIT` for $2MSL$, Client can reliably retransmit the final `ACK` if Server's retransmitted `FIN` arrives.

### Reason 2: Quenching Stale Duplicate Segments (Preventing Incarnation Corruption)
Suppose Client and Server open a connection on $(IP_c, Port_c, IP_s, Port_s)$. A data packet with `seq = 5000` is delayed in a malfunctioning router queue.
The connection terminates. Immediately, the client opens a **new incarnation** of the connection using the exact same ephemeral port $(Port_c)$.
If $2MSL$ did not elapse:
The delayed segment from the old connection finally emerges and arrives at Server. Because sequence numbers overlap, Server accepts the old packet as valid current data, fatally corrupting the new stream!
$2MSL$ guarantees that all packets belonging to the old connection have died in transit before that 4-tuple can be reused.

---

## 4. Production Masterclass: Compilable C Socket Lifecycle Inspector

Save as `tcp_lifecycle.c` and compile with `gcc -Wall -Wextra -O2 tcp_lifecycle.c -o tcp_lifecycle`:

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>

void print_tcp_info(int sock_fd, const char *label) {
    struct tcp_info info;
    socklen_t len = sizeof(info);

    if (getsockopt(sock_fd, IPPROTO_TCP, TCP_INFO, &info, &len) == 0) {
        const char *state_str = "UNKNOWN";
        switch (info.tcpi_state) {
            case TCP_ESTABLISHED: state_str = "TCP_ESTABLISHED"; break;
            case TCP_SYN_SENT:    state_str = "TCP_SYN_SENT"; break;
            case TCP_SYN_RECV:    state_str = "TCP_SYN_RECV"; break;
            case TCP_FIN_WAIT1:   state_str = "TCP_FIN_WAIT1"; break;
            case TCP_FIN_WAIT2:   state_str = "TCP_FIN_WAIT2"; break;
            case TCP_TIME_WAIT:   state_str = "TCP_TIME_WAIT"; break;
            case TCP_CLOSE:       state_str = "TCP_CLOSE"; break;
            case TCP_CLOSE_WAIT:  state_str = "TCP_CLOSE_WAIT"; break;
            case TCP_LAST_ACK:    state_str = "TCP_LAST_ACK"; break;
            case TCP_LISTEN:      state_str = "TCP_LISTEN"; break;
            case TCP_CLOSING:     state_str = "TCP_CLOSING"; break;
        }
        printf("[%s] Kernel Socket State: %s (State ID: %u)\\n", label, state_str, info.tcpi_state);
    }
}

int main(void) {
    printf("====================================================\\n");
    printf("TCP CONNECTION TERMINATION & HALF-CLOSE INSPECTOR\\n");
    printf("====================================================\\n");

    int sv[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) < 0) {
        perror("socketpair");
        return 1;
    }

    printf("[+] Created connected full-duplex socket pair (sv[0] <-> sv[1])\\n");

    // Write data from 0 to 1
    write(sv[0], "PING", 4);
    char buf[16];
    read(sv[1], buf, 4);

    printf("[+] Step 1: Performing Half-Close on sv[0] using shutdown(SHUT_WR)...\\n");
    // Sends FIN on sv[0] without closing read channel!
    shutdown(sv[0], SHUT_WR);

    // Reading on sv[1] will now yield EOF (0 bytes)
    ssize_t n = read(sv[1], buf, sizeof(buf));
    printf("[+] sv[1] read returned %zd bytes (EOF received cleanly)\\n", n);

    printf("[+] Step 2: sv[1] can STILL transmit data back to sv[0] (Half-Open)...\\n");
    write(sv[1], "PONG_REPLY", 10);
    n = read(sv[0], buf, sizeof(buf));
    buf[n] = '\\0';
    printf("[+] sv[0] successfully read '%s' despite having shutdown writing!\\n", buf);

    close(sv[0]);
    close(sv[1]);
    printf("[+] Both sockets closed.\\n");
    return 0;
}
```

---

## 5. Production Post-Mortem: Reverse-Proxy TIME_WAIT Port Exhaustion
### The Outage
A high-throughput Envoy / Nginx API gateway forwarding requests to internal upstream microservices collapsed. Client requests failed with:
`connect() failed (99: Cannot assign requested address) while connecting to upstream`

### Root Cause Analysis
Every time Nginx opened an HTTP/1.0 or non-keepalive connection to the backend, it initiated the active close after forwarding the response.
- As the active closer, Nginx transitioned every socket into `TIME_WAIT` for 60 seconds.
- The Linux ephemeral port range (`net.ipv4.ip_local_port_range`) had:
  $$65535 - 32768 = 32,767 \text{ available ports}$$
- At 600 requests/second with 60-second `TIME_WAIT`:
  $$\text{Concurrent TIME_WAIT sockets} = 600 \times 60 = 36,000 \text{ sockets!}$$
All 32,767 ephemeral ports were exhausted. Any subsequent `connect()` call threw `EADDRNOTAVAIL`!

### Architectural Fixes
1. **Enable HTTP Keep-Alive**: Reuse backend connections so handshakes and teardowns never occur per request:
   ```nginx
   upstream backend {
       server 10.0.1.10:8080;
       keepalive 500;
   }
   ```
2. **Enable Kernel TIME_WAIT Reuse**:
   ```bash
   sysctl -w net.ipv4.tcp_tw_reuse=1
   ```
   Allows reusing `TIME_WAIT` sockets for outgoing connections if timestamps (RFC 7323) prove the new connection is strictly newer than the dead segment.---

## 6. Simultaneous Close State Machine (The CLOSING State)
A rare but fully specified corner case occurs when both endpoints call `close()` simultaneously, transmitting `FIN` segments concurrently across the network:

```
HOST A                                                           HOST B
State: ESTABLISHED                                               State: ESTABLISHED
      |                                                                |
      | --- 1. Sends FIN (seq=x) ----      ---- 1. Sends FIN (seq=y) - |
      |                              \    /                            |
State: FIN_WAIT_1                     \  /                       State: FIN_WAIT_1
      |                                \/                              |
      | <--- Receives FIN (seq=y) -----/\----- Receives FIN (seq=x) -> |
      |                                                                |
State: CLOSING                                                   State: CLOSING
      | --- 2. Sends ACK (ack=y+1) --      ---- 2. Sends ACK (ack=x+1) |
      |                              \    /                            |
      |                               \/                               |
      | <--- Receives ACK ------------/\------ Receives ACK ---------> |
      |                                                                |
State: TIME_WAIT                                                 State: TIME_WAIT
      | [Waits 2MSL]                                                   | [Waits 2MSL]
      v                                                                v
State: CLOSED                                                    State: CLOSED
```

### The CLOSING State Dynamics
1. Both endpoints transmit `FIN` from `ESTABLISHED` and enter `FIN_WAIT_1`.
2. Instead of receiving an `ACK` for their own `FIN`, each endpoint receives a `FIN` from the peer.
3. Both endpoints acknowledge the peer's `FIN` and transition into `CLOSING`.
4. When each endpoint receives the `ACK` acknowledging its original `FIN`, both transition into `TIME_WAIT` for the full 2MSL duration before finally entering `CLOSED`.

---

## 7. SO_REUSEADDR vs SO_REUSEPORT Kernel Mechanics
When a server crashes or restarts, its previous listening port may remain bound in `TIME_WAIT` for up to 120 seconds, causing immediate restarts to fail with `bind: Address already in use` (`EADDRINUSE`).

- **`SO_REUSEADDR`**: Allows a socket to bind to a local address/port that is currently in `TIME_WAIT` state, provided the existing socket is not active. This is mandatory for resilient backend service restarts:
  ```c
  int enable = 1;
  setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable));
  ```
- **`SO_REUSEPORT`**: Introduced in Linux 3.9, allows multiple distinct processes or threads to bind to the exact same IP and port simultaneously. The Linux kernel load-balances incoming connection requests across the listening sockets via 4-tuple hashing, eliminating accept mutex lock contention in multi-core web servers (e.g. Nginx worker processes).
