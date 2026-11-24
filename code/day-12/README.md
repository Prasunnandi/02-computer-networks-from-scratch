# Hands-On Lab: Day 12 - TCP 3-Way Handshake Simulator (`handshake_simulator.py`)

## 1. What Are We Building & Why Does It Matter?
Before two computers can transmit data over TCP, they must synchronize starting sequence numbers and verify that packets can travel in both directions. This is the **3-Way Handshake**:
1. Client sends `SYN` (Synchronize) with its Initial Sequence Number ($ISN_c$).
2. Server responds with `SYN + ACK` ($ISN_s$, and acknowledges $ISN_c + 1$).
3. Client returns `ACK` (acknowledging $ISN_s + 1$).

In this lab, we build `handshake_simulator.py`, an Object-Oriented simulator modeling the client and server state transitions (`CLOSED` -> `SYN_SENT` -> `SYN_RECEIVED` -> `ESTABLISHED`).

---

## 2. Python Concepts for Beginners
1. **Object State Tracking**:
   - The `TCPEndpoint` class stores internal state in instance attributes: `self.state = "CLOSED"`.
2. **F-Strings (`f"..."`)**:
   - Used to embed variables inside strings: `f"[{self.name}] Transitioned to {self.state}"`.
3. **Simulating Networks via Method Calls**:
   - Sending a packet is simulated by calling a method on the receiving object: `server.receive_syn(packet)`.

---

## 3. Step-by-Step Code Walkthrough

```python
class TCPEndpoint:
    def __init__(self, name: str, isn: int):
        self.name = name
        self.isn = isn
        self.state = "CLOSED"
        self.peer_isn = None
        self.next_seq = isn

    def initiate_handshake(self) -> dict:
        self.state = "SYN_SENT"
        syn_pkt = {"flags": ["SYN"], "seq": self.isn, "ack": 0}
        self.next_seq += 1 # SYN consumes 1 sequence number
        return syn_pkt
```
- In TCP, control flags like `SYN` and `FIN` consume **1 sequence number**, even though they carry 0 bytes of payload!
- The server receives the SYN:
  - Validates `packet["seq"]`.
  - Sets `self.state = "SYN_RECEIVED"`.
  - Generates `SYN+ACK` with `ack = packet["seq"] + 1`.

---

## 4. How to Run the Script

```bash
cd code/day-12
python handshake_simulator.py
```

### Expected Output
```
[Client] Transitioned from CLOSED -> SYN_SENT
  --> Emitted SYN: seq=1000, ack=0
[Server] Received SYN -> Transitioned from LISTEN -> SYN_RECEIVED
  <-- Emitted SYN+ACK: seq=5000, ack=1001
[Client] Received SYN+ACK -> Transitioned from SYN_SENT -> ESTABLISHED
  --> Emitted final ACK: ack=5001
[Server] Received final ACK -> Transitioned from SYN_RECEIVED -> ESTABLISHED
=== 3-WAY HANDSHAKE COMPLETE: Full Duplex Connection Active ===
```

---

## 5. Beginner Exercises to Try
1. Modify the client to send an invalid ACK number in step 3. Verify that the server detects the mismatch and refuses to transition to `ESTABLISHED`.
2. Print the final `next_seq` for both client and server.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

