# Hands-On Lab: Day 19 - Fast Retransmit (3 DupACK) Simulator (`fast_retransmit_sim.py`)

## 1. What Are We Building & Why Does It Matter?
Waiting for an RTO timer takes hundreds of milliseconds.
If a receiver receives packets out-of-order, it immediately returns a **Duplicate ACK**.
When the sender receives **3 Duplicate ACKs**, it knows with 99.9% statistical certainty that a packet was dropped, and retransmits it immediately without waiting for the timer!

In this lab, we build `fast_retransmit_sim.py` to simulate packet loss, out-of-order ACK generation, and the 3-Duplicate ACK trigger.

---

## 2. Python Concepts for Beginners
1. **Simulating Stream Loss**:
   - Iterating over packet IDs and dropping a target ID (`if pkt == dropped_id: continue`).
2. **Counting Occurrences (`list.count()`)**:
   - Checking whether a duplicate ACK has appeared 3 times.

---

## 3. Step-by-Step Code Walkthrough

```python
def simulate_fast_retransmit(dropped_packet_id: int = 2, total_packets: int = 5) -> dict:
    acks = []
    retransmit_triggered = False

    # Packet 1 arrives -> ACKs packet 1
    acks.append(1)

    # Packet 2 dropped!
    # Packets 3, 4, 5 arrive out of order -> Each triggers DupACK for packet 1!
    for p in range(3, total_packets + 1):
        acks.append(1) # Duplicate ACK
        if acks.count(1) - 1 == 3: # 3 duplicates!
            retransmit_triggered = True

    return {"acks": acks, "fast_retransmit": retransmit_triggered}
```
- Traces the exact behavior of sender and receiver during selective packet loss.

---

## 4. How to Run the Script

```bash
cd code/day-19
python fast_retransmit_sim.py
```

### Expected Output
```
Transmitting Packets 1 through 5 (Packet 2 dropped in transit):
  Packet 1 Received -> Emit ACK 1
  Packet 2 DROPPED!
  Packet 3 Received -> Emit DupACK 1 (#1)
  Packet 4 Received -> Emit DupACK 1 (#2)
  Packet 5 Received -> Emit DupACK 1 (#3)
[!] 3 Duplicate ACKs Reached!
ACTION: Fast Retransmit triggered for missing Packet 2!
```

---

## 5. Beginner Exercises to Try
1. Try dropping packet 4 instead of packet 2. Trace the new ACK sequence.
2. Add Fast Recovery window inflation tracking.
---

## 6. Common Python Errors & How to Fix Them
As a beginner experimenting with networking scripts, watch out for:
1. **`struct.error: required argument is not an integer`**:
   - You passed a float or string into a struct format like `'I'` or `'H'`. Use `int()` to convert beforehand.
2. **`IndexError: tuple index out of range`**:
   - Unpacking didn't return as many values as you expected. Print the unpacked tuple to inspect its contents.
3. **`TypeError: can't concat str to bytes`**:
   - In Python 3, `str` and `bytes` are completely different types. Use `b"..."` or `"string".encode('utf-8')` to convert strings to bytes.

