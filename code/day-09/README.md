# Day 09 Lab: 5-Tuple Demultiplexing & Ephemeral Port Exhaustion in Python

> **Welcome to Day 9!** When you open 10 tabs to Google, all 10 tabs connect to the exact same server IP (`142.250.190.46`) on the exact same port (`443`).
> How does your computer know which Google search result belongs to Tab 1 and which belongs to Tab 2?
> Through the **Socket 5-Tuple**! In this lab, you will learn how the Linux kernel routes packets to the right application window in nanoseconds.

---

## 🎯 What Does This Lab Do?
`port_scanner_and_demux.py` demonstrates:
1. **The 5-Tuple**: Proving how $\langle \text{SrcIP}, \text{SrcPort}, \text{DstIP}, \text{DstPort}, \text{Protocol} \rangle$ uniquely separates connections.
2. **Kernel Hash Demultiplexing**: Routing incoming HTTP packets directly to the matching client socket queue with zero cross-talk.
3. **Ephemeral Port Exhaustion (`EADDRNOTAVAIL`)**: Simulating how high-throughput microservices run out of outbound ports when TCP sockets get stuck in `TIME_WAIT`!

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python port_scanner_and_demux.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Tuples as Dictionary Keys
* In Python, lists `[1, 2]` cannot be dictionary keys because lists can change (mutable).
* But **tuples** `(1, 2)` are immutable and can be used as dictionary keys!
* We use the entire 5-tuple as the dictionary lookup key:
  ```python
  key = (src_ip, src_port, dst_ip, dst_port, protocol)
  self.table[key] = []
  ```
  This allows $O(1)$ instantaneous packet demultiplexing!

### 2. Python Sets (`set()`)
* A set only stores unique elements:
  ```python
  self.active_allocated_ports = set()
  self.active_allocated_ports.add(32768)
  ```
* Checking `if port in self.active_allocated_ports:` takes $O(1)$ constant time.

### 3. Simulating Time with `time.time()`
* `time.time()` returns the current timestamp in seconds.
* To simulate a 2-second `TIME_WAIT` lock:
  ```python
  self.time_wait_ports[port] = time.time() + 2.0
  ```
  After 2 seconds elapse, the port is recycled and ready for reuse!

---

## 🔍 Code Walkthrough

```python
# 1. Two clients connect to the same server IP & Port (443):
client_a = Socket5Tuple("192.168.1.10", 51000, "93.184.216.34", 443, "TCP")
client_b = Socket5Tuple("192.168.1.20", 51000, "93.184.216.34", 443, "TCP")

# 2. Kernel demultiplexes incoming packets to isolated queues:
demux.demux_packet(client_a, b"HTML for Client A")
demux.demux_packet(client_b, b"HTML for Client B")

# Result: Client A's queue receives ONLY Client A's data!
```

---

## 📋 Expected Terminal Output
```text
============================================================
DAY 09 LAB: 5-TUPLE DEMULTIPLEXING & PORT EXHAUSTION ENGINE
============================================================

[1] Testing Kernel 5-Tuple Demultiplexing...
    Registered Socket A: <192.168.1.10:51000 -> 93.184.216.34:443 [TCP]>
    Registered Socket B: <192.168.1.20:51000 -> 93.184.216.34:443 [TCP]>
    Socket A Queue: [b'HTTP/1.1 GET /index.html [Client A]']
    Socket B Queue: [b'HTTP/1.1 GET /dashboard.html [Client B]']
    [PASS] Packets cleanly routed to isolated sockets with zero cross-talk.

[2] Simulating Ephemeral Port Exhaustion (EADDRNOTAVAIL)...
    Allocating ports until pool is saturated...
    - Allocated Port: 32768
    - Allocated Port: 32769
    - Allocated Port: 32770
    - Allocated Port: 32771
    - Allocated Port: 32772
    Expected Failure Caught: [Errno 99] Cannot assign requested address (EADDRNOTAVAIL: Ephemeral port pool exhausted!)
    [PASS] OS accurately simulated Ephemeral Port Exhaustion.

[3] Releasing ports into TIME_WAIT state...
    Reclaimed and re-allocated Port after TIME_WAIT: 32768
    [PASS] TIME_WAIT lifecycle and socket recycling successfully verified.
============================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: Look at Step [1]. Why didn't Client A and Client B collide even though both used port `51000`? (Answer: Because their Source IP addresses were different: `192.168.1.10` vs `192.168.1.20`!).
2. **Challenge 2**: How does HTTP Keep-Alive prevent `TIME_WAIT` port exhaustion? (Answer: It reuses existing open TCP sockets instead of creating and closing a new socket on every click!).
