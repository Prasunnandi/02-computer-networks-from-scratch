# Hands-On Lab: Day 14 - TCP Reset (RST) Packet Analyzer (`tcp_rst_analyzer.py`)

## 1. What Are We Building & Why Does It Matter?
Unlike a graceful `FIN` teardown, a TCP `RST` (Reset) packet is an emergency abort. It destroys the connection immediately with zero cleanup or `TIME_WAIT`.
A host emits a `RST` when:
1. A packet arrives for a port where no application is listening.
2. An application calls `close()` while unread data still sits in the receive buffer.
3. An abortive close is explicitly requested via the `SO_LINGER` socket option.

In this lab, we build `tcp_rst_analyzer.py` to evaluate network scenarios and determine whether an endpoint must emit a RST packet.

---

## 2. Python Concepts for Beginners
1. **Conditional Statements (`if / elif / else`)**:
   - Used to evaluate protocol rules and return decisions:
     ```python
     if target_port not in listening_ports:
         send_rst = True
     ```
2. **Boolean Flags**:
   - Using `True` and `False` to signal immediate actions.

---

## 3. Step-by-Step Code Walkthrough

```python
def analyze_rst_trigger(event_type: str, listening_ports: list, target_port: int, has_unread_data: bool) -> dict:
    if event_type == "INCOMING_SYN" and target_port not in listening_ports:
        return {"emit_rst": True, "reason": f"Port {target_port} closed (ECONNREFUSED)"}

    if event_type == "SOCKET_CLOSE" and has_unread_data:
        return {"emit_rst": True, "reason": "Unread data in receive buffer (Abortive Close)"}

    return {"emit_rst": False, "reason": "Graceful operation"}
```
- Identifies the exact conditions where the Linux kernel generates RST frames.

---

## 4. How to Run the Script

```bash
cd code/day-14
python tcp_rst_analyzer.py
```

### Expected Output
```
Scenario 1: Connect to port 8080 (Listening: [80, 443])
  Result: Emit RST = True (Port 8080 closed -> Connection Refused)

Scenario 2: Closing socket with 4096 unread bytes in buffer
  Result: Emit RST = True (Data loss prevention -> Abortive Close)

Scenario 3: Normal close with empty receive queue
  Result: Emit RST = False (Graceful FIN exchange initiated)
```

---

## 5. Beginner Exercises to Try
1. Add a scenario simulating an invalid sequence number arriving outside the sliding window.
2. Add a scenario checking for firewall RST injection.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

