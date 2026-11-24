# Day 14: TCP Reset (RST) Flag & Abortive Close

## 1. Architectural Foundations: The Reset Control Flag
In standard TCP operation, connections terminate gracefully via the 4-way FIN exchange, ensuring all buffered data in both directions is delivered and acknowledged.

The **Reset (`RST`)** flag represents an abrupt, non-negotiable termination. A segment with `RST = 1`:
- Allocates zero acknowledgment or sequence tracking.
- Is **never acknowledged** by the receiver.
- Instantly tears down the connection, purging all kernel send and receive queues.

```
+----------------------------------------------------------------------------+
| When does a host emit a TCP RST?                                           |
+----------------------------------------------------------------------------+
| 1. Port Closed: A packet arrives for a port with no listening socket.      |
| 2. Half-Closed Data Arrival: Data arrives for a socket already shut down.   |
| 3. Unread Data Purge: Application calls close() with unread bytes in queue.|
| 4. SO_LINGER Abort: Application forces abortive close (zero TIME_WAIT).    |
| 5. Security Inspection: Firewall / DPI injects RST to kill policy violation|
+----------------------------------------------------------------------------+
```

---

## 2. Abortive Close with SO_LINGER
By default, calling `close(sock_fd)` in userspace triggers a graceful FIN exchange in the background. If userspace needs to drop a client immediately and avoid the 2MSL `TIME_WAIT` state, it configures `SO_LINGER`:

```c
struct linger {
    int l_onoff;  // 0 = disabled (default), 1 = enabled
    int l_linger; // Linger timeout in seconds
};
```
- If `l_onoff = 1` and `l_linger = 0`:
  1. Any unsent data in the send buffer is discarded.
  2. Any unread data in the receive buffer is discarded.
  3. The kernel transmits a `RST` segment immediately.
  4. The socket closes instantly and is freed from memory with **zero `TIME_WAIT`**.

---

## 3. TCP RST Injection Attacks & RFC 5961 Defenses
Historically, an attacker who knew the 4-tuple of a connection could spoof a packet with `RST = 1`. If the sequence number was anywhere within the receiver's current window, the receiver would instantly tear down the connection (used historically to hijack BGP sessions).

### RFC 5961 Blind Reset Defense
Modern TCP stacks implement RFC 5961:
1. If an incoming `RST` matches the **exact next expected sequence number** (`seq == RCV.NXT`), it is accepted and tears down the connection.
2. If `seq` is inside the window but does not match `RCV.NXT` exactly:
   - The receiver does NOT tear down the connection!
   - The receiver sends a **Challenge ACK** containing its exact current sequence and acknowledgment numbers.
   - If the sender was genuine, it responds with a valid RST matching the Challenge ACK. If the sender was an attacker guessing sequence numbers, the attack fails completely.

---

## 4. Production Masterclass: Compilable C Graceful vs Abortive Close

Save as `tcp_rst_demo.c` and compile with `gcc -Wall -Wextra -O2 tcp_rst_demo.c -o tcp_rst_demo`:

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

void demonstrate_abortive_close(int sock_fd) {
    struct linger sl;
    sl.l_onoff = 1;  // Enable linger
    sl.l_linger = 0; // Timeout 0 -> ABORTIVE CLOSE (sends RST)

    if (setsockopt(sock_fd, SOL_SOCKET, SO_LINGER, &sl, sizeof(sl)) < 0) {
        perror("setsockopt(SO_LINGER)");
    } else {
        printf("[+] Configured SO_LINGER(l_onoff=1, l_linger=0) on socket %d\\n", sock_fd);
    }
}

int main(void) {
    printf("====================================================\\n");
    printf("TCP ABORTIVE CLOSE & RST DEMONSTRATION\\n");
    printf("====================================================\\n");

    int fds[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, fds) < 0) {
        perror("socketpair");
        return 1;
    }

    // Configure fds[0] for abortive RST close
    demonstrate_abortive_close(fds[0]);

    printf("[+] Closing socket fds[0] with abortive close enabled...\\n");
    close(fds[0]); // Transmits RST

    // Attempting to read on fds[1] after RST
    char buf[64];
    ssize_t n = read(fds[1], buf, sizeof(buf));
    if (n < 0) {
        printf("[+] Expected Result: read() failed with: %s (errno=%d)\\n",
               strerror(errno), errno);
    } else {
        printf("[+] Read returned %zd bytes\\n", n);
    }

    close(fds[1]);
    return 0;
}
```

---

## 5. Production Post-Mortem: The Cloud Load Balancer Idle-Timeout Mystery
### The Outage
A payment processing backend reported sporadic `Connection reset by peer` errors during bank settlement reconciliation. The errors only occurred during batch processing jobs that had a 65-second computation delay between database queries.

### Root Cause Analysis
1. The cloud Network Load Balancer (NLB) maintained an **idle connection timeout of 60 seconds**.
2. When the backend service spent 65 seconds computing a financial ledger without transmitting data over the TCP connection, the NLB silently dropped the connection from its internal connection tracking state table.
3. At second 65, when the backend service attempted to write the final settlement confirmation, the NLB received a packet for a connection it no longer recognized.
4. The NLB returned a TCP `RST` to the backend, causing the database transaction to rollback with `ECONNRESET`.

### Remediation
1. **Enable TCP Keepalive**: Configure the socket to send periodic 0-byte keepalive probes every 15 seconds to keep the NLB state table alive:
   ```c
   int optval = 1;
   setsockopt(sock, SOL_SOCKET, SO_KEEPALIVE, &optval, sizeof(optval));
   int idle = 15;
   setsockopt(sock, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle));
   ```
2. Align NLB idle timeout to exceed application latency thresholds (e.g. 300 seconds).---

## 6. The POSIX Socket Error Taxonomy: ECONNRESET vs EPIPE vs ECONNREFUSED

Understanding which kernel layer generates which error code is critical for network debugging:

```
+----------------------------------------------------------------------------+
| Error Code      | Triggering Condition             | Protocol Layer Cause  |
+----------------------------------------------------------------------------+
| ECONNREFUSED    | Connect to a closed port         | Server sent RST       |
| ECONNRESET      | Read from a connection after RST | Peer reset connection |
| EPIPE           | Write to a connection after FIN  | Sent to broken pipe   |
| ETIMEDOUT       | No response to SYN or data       | RTO timer expired     |
| EHOSTUNREACH    | Router cannot route packet       | ICMP Type 3 Code 1    |
+----------------------------------------------------------------------------+
```

### The Subtle Difference Between EPIPE and ECONNRESET
1. **`EPIPE`**: If Peer calls `close()`, Peer sends a `FIN`. Your local kernel receives `FIN`.
   - If you call `write()` once, the kernel transmits the data. Peer responds with `RST` because its socket is closed.
   - If you call `write()` a second time on that socket, your process is delivered a `SIGPIPE` signal! If `SIGPIPE` is ignored (`SIG_IGN`), the `write()` syscall returns `-1` with `errno = EPIPE`.
2. **`ECONNRESET`**: If Peer forcibly resets the connection (e.g. crash or abortive close), your local socket receives a `RST`. Any subsequent attempt to `read()` from the socket returns `-1` with `errno = ECONNRESET`.

---

## 7. Packet Dissection of a Malicious TCP RST Injection
An attacker monitoring an unencrypted TCP connection can forge a raw packet with:
- Source IP & Port = Server IP & Port
- Destination IP & Port = Client IP & Port
- Flags = `0x04` (`RST`)
- Sequence Number = Target sequence number inside client's current receive window.

When the client network stack receives this forged packet, it immediately destroys the socket without notifying the server. Both sides lose sync. Modern mitigations require:
1. **TCP MD5 Signatures (RFC 2385)**: Used exclusively for BGP peering sessions.
2. **TCP Authentication Option (TCP-AO, RFC 5925)**: Cryptographic SHA-1/HMAC validation of every segment including RSTs.
3. **Transport Layer Security (TLS 1.3)**: Application-layer cryptographic framing preventing blind payload and teardown manipulation.
