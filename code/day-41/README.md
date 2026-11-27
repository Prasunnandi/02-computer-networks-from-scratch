# Day 41: DHCP DORA State Machine Lab Tutorial

Welcome to Day 41 of Computer Networks from Scratch. Today, you will build an RFC 2131 compliant Dynamic Host Configuration Protocol (DHCP) state machine that automates host IP configuration across local area networks.

---

## 1. What Are We Building & Why Does It Matter?

When an operating system connects to an Ethernet switch or Wi-Fi access point, it possesses no IP address, subnet mask, default gateway, or DNS server. Without these parameters, layer 3 IPv4 packet routing is impossible.

DHCP resolves this through the four-step **DORA** handshake:
1. **DISCOVER**: The unconfigured client broadcasts an all-ones broadcast packet (`255.255.255.255`) searching for available DHCP servers.
2. **OFFER**: One or more DHCP servers reserve an available IP from their pool and broadcast or unicast an offer.
3. **REQUEST**: The client selects one offer and broadcasts its choice, notifying the selected server and releasing reservations on competing servers.
4. **ACK**: The selected server commits the binding to persistent storage and issues the final acknowledgment with configuration options.

In this lab, you implement both the Client Finite State Machine (`INIT -> SELECTING -> REQUESTING -> BOUND`) and the Server address allocation pool from scratch.

---

## 2. Python Concepts for Beginners

### A. Python Enums for Finite State Machines (`enum.Enum`)
An enumeration restricts a variable to a predefined set of symbolic names, preventing invalid states:
```python
import enum

class ClientState(enum.Enum):
    INIT = "INIT"
    SELECTING = "SELECTING"
    REQUESTING = "REQUESTING"
    BOUND = "BOUND"
```

### B. Bitwise Conversion Between IP Strings and 32-Bit Integers
To generate sequential IP ranges (e.g., `192.168.1.100` to `192.168.1.200`), convert dotted-quad strings to 32-bit unsigned integers:
```python
def ip_to_int(ip: str) -> int:
    octets = [int(x) for x in ip.split(".")]
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

def int_to_ip(val: int) -> str:
    return f"{(val >> 24) & 0xFF}.{(val >> 16) & 0xFF}.{(val >> 8) & 0xFF}.{val & 0xFF}"
```

### C. Data Classes (`@dataclass`)
Data classes automatically generate constructors, string representations, and equality checks:
```python
from dataclasses import dataclass

@dataclass
class DHCPMessage:
    op: int
    xid: int
    yiaddr: str
```

---

## 3. Step-by-Step Code Walkthrough

1. **`DHCPMessageType` & `ClientState`**: Enums capturing the RFC 2131 message codes and client state graph.
2. **`DHCPServer` Class**:
   - `_generate_pool()`: Precomputes the list of available IP addresses between start and end bounds.
   - `handle_discover()`: Inspects `msg.chaddr` (client MAC), checks existing leases or picks the next unassigned IP, reserves it in `pending_offers`, and returns `DHCPOFFER`.
   - `handle_request()`: Confirms the client chose this server via `server_id`, commits the lease to `self.leases`, clears pending reservations, and returns `DHCPACK`.
3. **`DHCPClient` Class**:
   - `start_discovery()`: Generates a cryptographically strong random 32-bit transaction ID (`xid`), enters `SELECTING`, and returns a `DHCPDISCOVER`.
   - `select_offer()`: Validates matching `xid`, transitions to `REQUESTING`, and emits `DHCPREQUEST`.
   - `handle_ack()`: Validates matching `xid`, populates assigned network parameters, and enters `BOUND`.
4. **`main()` Test Suite**: Executes end-to-end multi-client allocation and verifies sequential IP assignment.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-41/dhcp_dora_state_machine.py
```

Expected output:
```text
=== Day 41: DHCP DORA State Machine Simulator ===
[Step 1] Client sends DISCOVER: xid=0x5E21B904, MAC=00:1A:2B:3C:4D:5E
[Step 2] Server responds OFFER: Offered IP=192.168.1.100, Server=192.168.1.1
[Step 3] Client broadcasts REQUEST: Requested IP=192.168.1.100, Server=192.168.1.1
[Step 4] Server sends ACK: Client BOUND to 192.168.1.100 (Gateway: 192.168.1.1, DNS: 1.1.1.1)
[*] Second client allocated next sequential IP: 192.168.1.101
All DHCP DORA State Machine assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`AttributeError: 'NoneType' object has no attribute 'msg_type'`**: Occurs if `server.handle_discover()` returns `None` due to IP pool exhaustion. Ensure your pool range accommodates all concurrent clients.
- **`ValueError: invalid literal for int() with base 10`**: Occurs if an IP address string contains invalid characters or empty octets (e.g. `192.168..1`).
- **`AssertionError: Client xid mismatch`**: Happens when the client receives an offer or ACK corresponding to a different transaction ID. Verify `offer.xid == client.current_xid`.

---

## 6. Beginner Exercises & Challenges

1. **Simulate Multiple Competing DHCP Servers**: Instantiate two `DHCPServer` instances on the same network segment. Modify the client to receive offers from both and verify it only requests from the first received offer while freeing the second.
2. **Implement DHCPRELEASE**: Add a `release()` method to `DHCPClient` that sends a `DHCPRELEASE` message to the server, releasing its active lease before expiry.
3. **Address Pool Depletion Handling**: Initialize a server with a pool of only 2 IPs (`.100` to `.101`). Connect 3 clients and assert that the third client receives a `None` offer or `DHCPNAK`.
