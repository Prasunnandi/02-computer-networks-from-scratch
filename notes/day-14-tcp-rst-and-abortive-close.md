# Day 14: TCP Reset (RST) Flag & Abortive Close

## 1. Architectural Foundations: The Reset (RST) Flag

While `FIN` performs an orderly, graceful connection shutdown with guaranteed buffer drainage, the **Reset (`RST`) flag** is TCP's panic button. It triggers an **Abortive Close**:
- All unread data in socket receive buffers is instantly discarded.
- Pending outbound data in send buffers is discarded.
- No `ACK` is expected or sent in return.
- The connection is instantly vaporized from memory, bypassing the `TIME_WAIT` state entirely.

---

## 2. Common Scenarios That Trigger a TCP Reset

### Scenario 1: Port Closed (Connection Refused)
When a client sends a `SYN` to a server on a destination port where no application is listening (`ECONNREFUSED`):
- The server kernel checks its TCP listener table.
- Finding no matching `struct sock`, the kernel generates an immediate `RST, ACK` packet with $ack = seq + 1$.

```
Client                                                  Server (Port 8080 Closed)
  |                                                                |
  | -------------- SYN (seq=1000, port=8080) --------------------> |
  |                                                                |
  | <------------- RST, ACK (seq=0, ack=1001) -------------------- |
  v                                                                v
Connection Refused (ECONNREFUSED)                            Socket Destroyed
```

### Scenario 2: Half-Open Connection Recovery (Host Crash & Reboot)
If a server crashes, loses power, and reboots while a client is connected:
- The client, unaware of the server's reboot, sends a data segment using the old sequence numbers.
- The rebooted server has no memory of this connection.
- It immediately returns a `RST` packet, causing the client application to fail with `ECONNRESET` (**Connection reset by peer**).

### Scenario 3: Unread Data in Socket Receive Buffer
If a server closes a socket (`close(fd)`) while unread data still sits in its socket receive buffer:
- The kernel treats this as a data loss bug in the application.
- Instead of sending a graceful `FIN`, the kernel aborts with a `RST` to notify the client that its sent data was never processed!

---

## 3. Programming Abortive Closes with `SO_LINGER`

In C network programming, an application can deliberately force an abortive `RST` close to bypass `TIME_WAIT` using the `SO_LINGER` socket option:

```c
#include <sys/socket.h>

struct linger sl;
sl.l_onoff = 1;  // Enable non-standard linger behavior
sl.l_linger = 0; // Linger timeout = 0 seconds (Immediate abort)

// Set socket option:
setsockopt(sockfd, SOL_SOCKET, SO_LINGER, &sl, sizeof(sl));

// When close() is called, kernel sends RST instead of FIN!
close(sockfd);
```

> [!WARNING]
> Forcing `SO_LINGER` to 0 to eliminate `TIME_WAIT` is a dangerous anti-pattern. It breaks TCP's reliable delivery semantics and can cause wandering duplicate packets to corrupt future connections.
