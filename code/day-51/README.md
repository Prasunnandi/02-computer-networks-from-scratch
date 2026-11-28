# Day 51: HTTP/1.1 Persistent Connections & Pipelining Lab Tutorial

Welcome to Day 51 of Computer Networks from Scratch. Today, you will build an HTTP/1.1 persistent connection state machine, analyzing keep-alive connection reuse, idle timeouts, and Head-of-Line (HoL) blocking during request pipelining.

---

## 1. What Are We Building & Why Does It Matter?

In HTTP/1.0, every resource request required establishing a brand-new TCP socket (SYN, SYN-ACK, ACK), transferring one file, and tearing down the connection (FIN-ACK). This introduced devastating latency penalties.

HTTP/1.1 introduced two major transport features:
1. **Persistent Connections (`Connection: keep-alive`)**: The underlying TCP socket remains open across multiple sequential requests, eliminating 3-way handshakes.
2. **Pipelining**: Clients emit multiple requests back-to-back without waiting for intermediate responses.

However, pipelining suffers from **Head-of-Line (HoL) Blocking**: because HTTP/1.1 responses carry no stream identifiers, the server must deliver responses in the exact order requested. If the first request is slow, all subsequent fast responses are blocked.

In this lab, you simulate this exact transport dynamic in pure Python.

---

## 2. Python Concepts for Beginners

### A. FIFO Queues with Python Lists
Queue requests in first-in, first-out order to simulate an incoming TCP socket buffer:
```python
queue = []
queue.append(request)
next_request = queue.pop(0)
```

### B. Timestamp Simulation
Model real-world network and server processing delays by incrementing a simulated clock:
```python
current_time += request.processing_time_sec
```

### C. Default Dictionary Values (`field(default_factory=dict)`)
When defining dataclasses with mutable dictionaries, always use `default_factory` to prevent shared state bugs across instances:
```python
from dataclasses import dataclass, field

@dataclass
class HTTPRequest:
    headers: dict = field(default_factory=dict)
```

---

## 3. Step-by-Step Code Walkthrough

1. **`HTTPRequest` & `HTTPResponse` Dataclasses**: Encapsulates HTTP request attributes, methods, paths, and simulated processing latency.
2. **`HTTP11Connection` Class**:
   - `send_request_sequential()`: Verifies that the socket is open and idle timeout has not expired. Increments request counters and marks the connection closed if `Connection: close` is encountered.
   - `enqueue_pipelined_request()`: Buffers multiple pipelined requests into `self.pipelined_queue`.
   - `process_pipelined_stream()`: Processes the queue in strict sequential order. Demonstrates that fast downstream requests cannot be emitted until the preceding slow request completes.
3. **`main()` Test Suite**: Validates sequential socket reuse, idle timeout termination, and Head-of-Line blocking delay measurements.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-51/http11_persistent_connection_pipeline_sim.py
```

Expected output:
```text
=== Day 51: HTTP/1.1 Persistent Connection & Pipelining Simulator ===
[*] Test 1 Passed: First request completed on persistent connection (Socket Open)
[*] Test 2 Passed: Second request reused socket at t+2s without new TCP handshake
[*] Test 3 Passed: Idle timeout successfully terminated persistent socket
[*] Test 4 Passed: HoL blocking demonstrated: Fast asset (/logo.png) stalled until t=1002.01s
All HTTP/1.1 Persistent Connection assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **Socket State Bleed**: Ensure you check `self.is_open` before processing any incoming request to simulate a closed TCP connection.
- **Timestamp Arithmetic Errors**: Always compute the completion timestamp relative to the cumulative elapsed clock rather than `time.time()`.

---

## 6. Beginner Exercises & Challenges

1. **Implement `Max-Requests` Limit**: Update `send_request_sequential()` to inject `Connection: close` when `requests_served` reaches `max_requests`.
2. **Calculate Total Wire Latency**: Add a method comparing the total wall-clock time between non-persistent HTTP/1.0 and persistent HTTP/1.1 across 10 requests.
3. **Simulate Out-of-Order Execution**: Modify the engine to demonstrate what happens if a server attempts to return responses out-of-order without stream IDs.
