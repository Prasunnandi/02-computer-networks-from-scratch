# Day 09: Transport Layer Foundations, Port Numbers, Demultiplexing & The Socket 5-Tuple

> **Zero External Dependency Guarantee**: This document is an encyclopedic, self-contained masterclass. It contains complete historical origins, real-world mental models, BSD socket API architectures, the 5-tuple demultiplexing hash table physics, ephemeral port exhaustion, `SO_REUSEPORT` kernel load balancing, SYN flood defenses (SYN Cookies), and FAANG staff-level interview questions. You do NOT need any textbook or external website.

---

## 1. Executive Summary & The Core Mental Model

The Network Layer (Layer 3 / IPv4) delivers packets **host-to-host**: it gets an IP datagram from physical Computer A to physical Computer B. However, a modern operating system runs hundreds of concurrent network programs simultaneously: a web browser, a database server, a background cloud sync daemon, a Spotify music stream, and an SSH session.

When an IP datagram arrives at the network card, Layer 3 cannot determine which application owns the data!

The Transport Layer (Layer 4) provides **process-to-process communication** through the abstraction of **Port Numbers** and **Multiplexing / Demultiplexing**.

```
THE TRANSPORT LAYER DEMULTIPLEXING PIPELINE:
[ Network Card / IP Layer ] ---> Receives incoming IP Packet for 192.168.1.50
                                          |
                                          v (Layer 4 Demultiplexing Engine)
                    +---------------------+---------------------+
                    |                                           |
                    v Port 80                                   v Port 22
            +---------------+                           +---------------+
            | NGINX Web Srv |                           | OpenSSH Daemon|
            +---------------+                           +---------------+
```

---

## 2. Low-Level Protocol Mechanics: The Socket 5-Tuple

In the Linux kernel, every active network connection is identified by a unique mathematical **5-Tuple**:
$$\mathbf{5\text{-Tuple} = ( \text{Source IP}, \ \text{Source Port}, \ \text{Destination IP}, \ \text{Destination Port}, \ \text{Protocol} )}$$

```
THE 5-TUPLE COLLISION ELIMINATION PROOF:
A single web server listening on 0.0.0.0:80 can handle 1,000,000 concurrent clients!
Why?
Connection 1: (198.51.100.1, 54210, 203.0.113.5, 80, TCP)
Connection 2: (198.51.100.1, 54211, 203.0.113.5, 80, TCP)  <-- Different Source Port!
Connection 3: (198.51.100.2, 54210, 203.0.113.5, 80, TCP)  <-- Different Source IP!

Because each 5-tuple is globally unique, the kernel demultiplexes packets with ZERO ambiguity!
```

---

## 3. IANA Port Allocation Standards

Port numbers are 16-bit unsigned integers ($0$ to $65,535$), classified by the Internet Assigned Numbers Authority (IANA):

| Port Category | Numerical Range | Privilege Required | Typical Services & Examples |
| :--- | :---: | :---: | :--- |
| **System / Well-Known Ports**| $0 - 1023$ | **Root / Superuser (`CAP_NET_BIND_SERVICE`)** | Core internet daemons: `22` (SSH), `25` (SMTP), `53` (DNS), `80` (HTTP), `443` (HTTPS). |
| **Registered Ports** | $1024 - 49151$ | Unprivileged Users | Standard applications: `3306` (MySQL), `5432` (PostgreSQL), `6379` (Redis), `8080` (HTTP Alt). |
| **Dynamic / Ephemeral Ports**| $49152 - 65535$| Assigned by Kernel | Temporary client ports allocated dynamically during `connect()`. Linux default: `32768 - 60999`. |

---

## 4. Kernel Demultiplexing Architecture: Hash Tables & `SO_REUSEPORT`

When a packet arrives from the network driver, the kernel does not search through open sockets linearly. Instead, it queries in-memory **Socket Hash Tables** (`net/ipv4/inet_hashtables.c`):
1. **Established Hash Table**: Evaluates full 4-tuple `(src_ip, src_port, dst_ip, dst_port)`. If matched, points directly to the `struct sock` instance.
2. **Listening Hash Table**: If no established connection matches, hashes destination port to find listening sockets.

```
SO_REUSEPORT KERNEL LOAD BALANCING:
Without SO_REUSEPORT:
  Single listening socket -> 1 CPU Core handles accept() queue -> CPU Bottleneck!

With SO_REUSEPORT (Linux 3.9+):
  Core 1: [ Process A: bind(:80) ] <---+
  Core 2: [ Process B: bind(:80) ] <---+--- Kernel hashes incoming 5-tuple
  Core 3: [ Process C: bind(:80) ] <---+    distributing clients evenly across all cores!
  Core 4: [ Process D: bind(:80) ] <---+
```

---

---

## 6. Complete Python Multi-Threaded Port Scanner & Demux Engine

```python
import socket
import concurrent.futures
import time

def scan_port(target_ip: str, port: int, timeout: float = 0.5) -> bool:
    # Attempt TCP 3-way handshake to verify if port is open
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        return result == 0

def fast_port_scan(target_ip: str, ports: list[int], max_threads: int = 100):
    print(f"[*] Initiating multi-threaded scan on {target_ip} ({len(ports)} ports)...")
    start = time.perf_counter()
    open_ports = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_port = {executor.submit(scan_port, target_ip, p): p for p in ports}
        for future in concurrent.futures.as_completed(future_to_port):
            p = future_to_port[future]
            try:
                if future.result():
                    open_ports.append(p)
                    print(f"    [+] Port {p:5d} is OPEN!")
            except Exception:
                pass

    elapsed = time.perf_counter() - start
    print(f"[*] Scan complete in {elapsed:.2f}s. Found {len(open_ports)} open ports.")
    return sorted(open_ports)

if __name__ == "__main__":
    test_ports = [21, 22, 23, 25, 53, 80, 443, 3306, 5432, 6379, 8080]
    fast_port_scan("127.0.0.1", test_ports)
```

## 7. Real-World Production War Stories

### 5.1 War Story 1: The Ephemeral Port Exhaustion Blackout
* **The Incident**: A high-throughput API gateway processing 5,000 requests per second suddenly began throwing:
  `Cannot assign requested address (EADDRNOTAVAIL)`
* **The Investigation**:
  ```bash
  # Check system ephemeral port range:
  cat /proc/sys/net/ipv4/ip_local_port_range
  # Output: 32768   60999 (28,231 ports available)

  # Check socket states:
  ss -s
  # Output: TCP: 28240 (estab 15, closed 0, timewait 28220)
  ```
* **The Root Cause**:
  - The microservice queried an internal authentication server without HTTP keep-alive connection reuse.
  - Every HTTP query created a new TCP socket, executed a transaction, and closed the connection.
  - In TCP, when an active endpoint closes a connection, the socket enters the **`TIME_WAIT`** state for **60 seconds** to ensure lingering packets on the network drain safely.
  - In less than 10 seconds, all 28,231 ephemeral ports were locked in `TIME_WAIT`, preventing any new outgoing connections!
* **The Fix**:
  1. Enabled TCP connection pooling.
  2. Configured `/proc/sys/net/ipv4/tcp_tw_reuse = 1` allowing the kernel to safely reuse `TIME_WAIT` sockets for outgoing requests.

---

## 8. Staff-Level Technical Interview Deep-Dives

### Question 1: What is the exact difference between `SO_REUSEADDR` and `SO_REUSEPORT`?
**Exhaustive Answer**:
* **`SO_REUSEADDR`**: Allows a server to bind to a local port that is currently occupied by a connection in the `TIME_WAIT` state. Essential for restarting server daemons immediately without waiting 2 minutes for sockets to drain.
* **`SO_REUSEPORT`**: Allows **multiple independent processes or threads** to bind to the **exact same IP address and port number simultaneously**! The Linux kernel maintains an array of listening sockets and distributes incoming connections evenly using a 5-tuple hash, eliminating single-thread accept locks!

---

## 9. Complete Verification Checklist (Zero Gaps)
- [ ] Diagram the 5 fields of the socket 5-tuple.
- [ ] What is the numerical range of IANA Well-Known vs Ephemeral ports?
- [ ] Explain how `TIME_WAIT` socket accumulation causes `EADDRNOTAVAIL` errors.
- [ ] How does `SO_REUSEPORT` enable multi-core scaling in Nginx and Envoy?
