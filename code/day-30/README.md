# Hands-On Lab: Day 30 Milestone - Userspace TCP Sliding Window Engine (`milestone_tcp_engine.py`)

## 1. What Are We Building & Why Does It Matter?
Welcome to the **Day 30 Capstone Milestone** for Computer Networks!
Over the past 30 days, we studied the theory of:
- Framing and checksums (Days 2, 6)
- Transport 5-tuple demultiplexing and UDP (Days 9, 10)
- Sequence numbers and 3-way handshakes (Days 11, 12)
- Flow control sliding windows (Day 15)
- Retransmission timeouts and Fast Recovery (Days 18, 19, 23)
- Congestion control algorithms (Days 21, 22, 24, 25, 26)

In this milestone project, we combine all these pieces into a complete, working **Userspace TCP Sliding Window Engine** (`milestone_tcp_engine.py`).
Our engine features:
1. **Packet Framing**: Real packet headers with Sequence numbers, Cumulative ACKs, Flags, and 16-bit One's Complement Checksums.
2. **Sender Sliding Window Buffer**: Enforces inflight byte limits, transmits new data, and slides the left window edge (`snd_una`) forward on cumulative ACKs.
3. **Lossy Network Channel**: Injects probabilistic packet drops to test resilience.
4. **Out-of-Order Reassembly**: The receiver buffers future segments and cleanly delivers a contiguous byte stream to the application layer.
5. **Retransmission Timeout (RTO)**: Automatically recovers dropped packets without deadlock.

---

## 2. Python Concepts for Beginners
1. **The `bytearray` Type**:
   - `bytes` in Python is immutable (cannot be modified after creation).
   - `bytearray` is mutable! You can append chunks with `self.received_data.extend(chunk)`. Once finished, convert back with `bytes(self.received_data)`.
2. **Dictionary Key Removal (`del dict[key]`)**:
   - When a cumulative ACK arrives, `del self.in_flight[seq]` frees memory for all acknowledged packets.
3. **Random Number Generation (`random.random()`)**:
   - `random.random()` returns a float between `0.0` and `1.0`.
   - `if random.random() < 0.25:` triggers an event with exactly 25% probability.
   - `random.seed(42)` ensures the test produces identical results every time you run it.

---

## 3. Step-by-Step Code Walkthrough

### The Sender Sliding Window
```python
def send_available(self) -> List[TCPPacket]:
    packets = []
    while (self.snd_nxt - self.snd_una) + self.mss <= self.window_size and self.snd_nxt < len(self.data_buffer):
        chunk = self.data_buffer[self.snd_nxt : self.snd_nxt + self.mss]
        pkt = TCPPacket(seq=self.snd_nxt, ..., checksum=compute_checksum(chunk), payload=chunk)
        self.in_flight[pkt.seq] = pkt
        packets.append(pkt)
        self.snd_nxt += len(chunk)
    return packets
```
- `self.snd_una` is the oldest unacknowledged byte (left edge of window).
- `self.snd_nxt` is the next byte to be sent (right edge of in-flight data).
- The difference `(self.snd_nxt - self.snd_una)` is the number of unacknowledged bytes in flight. As long as this is less than `self.window_size`, the sender blasts packets into the network without waiting!

### The Receiver Out-of-Order Reassembly
```python
if pkt.seq == self.rcv_nxt:
    self.received_data.extend(pkt.payload)
    self.rcv_nxt += len(pkt.payload)
    # Drain contiguous buffered packets
    while self.rcv_nxt in self.reassembly_buffer:
        data = self.reassembly_buffer.pop(self.rcv_nxt)
        self.received_data.extend(data)
        self.rcv_nxt += len(data)
elif pkt.seq > self.rcv_nxt:
    self.reassembly_buffer[pkt.seq] = pkt.payload
```
- If Packet 4 arrives before Packet 0, the receiver does not crash or corrupt the file; it stores Packet 4 in `reassembly_buffer`.
- As soon as Packet 0, 1, 2, and 3 arrive, the loop drains Packet 4 from the buffer and delivers all bytes in perfect order!

---

## 4. How to Run the Script

```bash
cd code/day-30
python milestone_tcp_engine.py
```

### Expected Output
```
====================================================
DAY 30 MILESTONE: USERSPACE TCP SLIDING WINDOW ENGINE
====================================================
Sending 46 bytes of data over lossy channel (Drop Rate = 25%)...

Step  | Sender Window [una, nxt]       | Action / Channel Event           | Receiver ACK
---------------------------------------------------------------------------
1     | [0  , 16 ]                     | Transmit Seq 0   (4B)             | ACK 4
1     | [0  , 16 ]                     | Transmit Seq 4   (4B)             | ACK 8
1     | [0  , 16 ]                     | *** PACKET DROP (Seq 8) ***      | ACK 8
1     | [0  , 16 ]                     | Transmit Seq 12  (4B)             | ACK 8
2     | [8  , 20 ]                     | Transmit Seq 16  (4B)             | ACK 8
3     | [8  , 20 ]                     | RTO RETRANSMIT Seq 8             | ACK 20
4     | [20 , 36 ]                     | Transmit Seq 20  (4B)             | ACK 24
...
---------------------------------------------------------------------------
Total Bytes Sent       : 46 bytes
Total Bytes Received   : 46 bytes
Retransmissions Triggered: 2
Reconstructed Payload  : HELLO_WORLD_TCP_SLIDING_WINDOW_MILESTONE_TEST!

[VERIFIED] Milestone 1 Userspace TCP Sliding Window Engine operating at 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting
1. **Window Stall Deadlock**:
   - If the sender transmits up to `window_size` and all packets are dropped, `send_available()` returns empty. The engine must invoke `on_timeout()` to kickstart retransmission.
2. **Corrupted Reassembly**:
   - If you append out-of-order packets directly into `self.received_data`, the file will be garbled. Always buffer out-of-order sequence numbers until the gap is filled.

---

## 6. Beginner Exercises & Challenges
1. **Corrupt Packet Payload**: In `simulate_network_transfer`, simulate bit flips by modifying `p.payload = b'FAIL'` on 10% of packets. Verify that the receiver detects bad checksums and discards them.
2. **Variable Window Size**: Allow the receiver to dynamically advertise smaller window sizes (`win_size`) to simulate an overwhelmed consumer thread.
