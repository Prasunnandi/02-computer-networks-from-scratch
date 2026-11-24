# Day 16: Zero Window, Probes & Silly Window Syndrome

## 1. Architectural Foundations: The Zero Window State

When a receiving application fails to read data from its socket receive buffer as fast as the network delivers it, the buffer fills to capacity. To prevent buffer overflow and packet drops, the receiver advertises **`Window = 0`** (a **Zero Window Advertisement**) in its ACK packet.

Upon receiving `Window = 0`, the sender must **immediately halt all data transmission**.

---

## 2. The Zero Window Deadlock & The Persist Timer

Suppose a receiver advertises `Window = 0`. Later, the receiving application wakes up, reads $32\text{ KB}$ of data, and the kernel sends a **Window Update packet** advertising `Window = 32768`.

**What happens if this Window Update packet is lost in transit?**
- The sender is waiting for the receiver to open the window.
- The receiver is waiting for the sender to transmit new data.
- **Both endpoints deadlock indefinitely!**

### The Solution: Zero Window Probes (ZWP) & The Persist Timer
To prevent this catastrophic deadlock, TCP uses a dedicated **Persist Timer**. When the sender receives `Window = 0`, it arms its Persist Timer.
- When the timer expires, the sender transmits a **Zero Window Probe (ZWP)**: a segment containing exactly **1 byte of payload** (or $0$ bytes depending on implementation) with the sequence number of the next expected byte.
- The receiver is forced to reply with an ACK acknowledging the probe and advertising its current window size.
- If the window is still zero, the persist timer doubles (exponential backoff, e.g. $1\text{s}, 2\text{s}, 4\text{s}, 8\text{s}, \dots$ up to a maximum of $60\text{s}$) and repeats until the window opens.

---

## 3. Silly Window Syndrome (SWS): Pathological Efficiency Collapse

Silly Window Syndrome (SWS) is a pathological condition where data is exchanged in microscopic chunks (e.g. 1 byte at a time), collapsing network efficiency:
- Sending a 1-byte payload requires:
  - 20 bytes IP Header + 20 bytes TCP Header = **40 bytes of overhead for 1 byte of data!**
  - Overhead ratio = $\frac{40}{41} = 97.6\%$ wasted bandwidth!

### 3.1 Receiver-Side SWS Avoidance: Clark's Solution
David D. Clark's solution prevents the receiver from advertising small window increments:
**Do NOT advertise a window update until the available receive buffer space is AT LEAST:**
$$\min\left(\text{MSS}, \frac{\text{Total Receive Buffer Space}}{2}\right)$$
Until this threshold is met, the receiver continues advertising `Window = 0`.

### 3.2 Sender-Side SWS Avoidance: Nagle's Algorithm
The sender must avoid transmitting small packets if unacknowledged data is outstanding, buffering data locally until a full MSS can be transmitted.
