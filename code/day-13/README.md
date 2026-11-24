# Hands-On Lab: Day 13 - TCP 4-Way Teardown & TIME_WAIT Simulator (`tcp_state_machine_sim.py`)

## 1. What Are We Building & Why Does It Matter?
Because TCP connections are full-duplex (data flows simultaneously in both directions), terminating a connection cleanly requires shutting down each direction independently. This is done with a 4-way exchange:
`FIN` -> `ACK` -> `FIN` -> `ACK`.

The party that initiates the close enters the famous **`TIME_WAIT`** state for 2 Maximum Segment Lifetimes (2MSL, typically 60 seconds).
In this lab, we build `tcp_state_machine_sim.py` to trace state transitions across both endpoints during teardown and verify the 2MSL timer calculation.

---

## 2. Python Concepts for Beginners
1. **Lists of Dictionaries as Event Logs**:
   - We track sequential protocol events in a list: `log.append({"step": 1, "action": "FIN", ...})`.
2. **Iteration with `for ... in`**:
   - Loops through the logged events and prints formatted trace tables.

---

## 3. Step-by-Step Code Walkthrough

```python
def simulate_tcp_teardown(client_seq: int = 1500, server_seq: int = 8200) -> list:
    log = []
    # 1. Client calls close() -> Active Close
    log.append({"sender": "Client", "state": "FIN_WAIT_1", "flags": ["FIN"], "seq": client_seq})

    # 2. Server receives FIN -> Passive Close
    log.append({"sender": "Server", "state": "CLOSE_WAIT", "flags": ["ACK"], "ack": client_seq + 1})

    # 3. Client receives ACK
    log.append({"sender": "Client", "state": "FIN_WAIT_2"})

    # 4. Server application finishes and calls close()
    log.append({"sender": "Server", "state": "LAST_ACK", "flags": ["FIN"], "seq": server_seq})

    # 5. Client receives FIN and enters TIME_WAIT
    log.append({"sender": "Client", "state": "TIME_WAIT", "flags": ["ACK"], "ack": server_seq + 1, "duration_sec": 60})
    return log
```
- Walks through each state: `FIN_WAIT_1`, `CLOSE_WAIT`, `FIN_WAIT_2`, `LAST_ACK`, and `TIME_WAIT`.

---

## 4. How to Run the Script

```bash
cd code/day-13
python tcp_state_machine_sim.py
```

### Expected Output
```
Step 1: Client -> FIN (seq=1500) | State: FIN_WAIT_1
Step 2: Server -> ACK (ack=1501) | State: CLOSE_WAIT (App notified of EOF)
Step 3: Client receives ACK      | State: FIN_WAIT_2 (Half-closed)
Step 4: Server -> FIN (seq=8200) | State: LAST_ACK
Step 5: Client -> ACK (ack=8201) | State: TIME_WAIT (2MSL Timer = 60s)
Step 6: Server receives ACK      | State: CLOSED
Step 7: 2MSL Timer Expires       | Client State: CLOSED
```

---

## 5. Beginner Exercises to Try
1. Try changing `client_seq` to `9999`. Notice how `ack` numbers in the log adjust automatically.
2. Add a simulation of simultaneous close (both parties send FIN at the same time).
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

