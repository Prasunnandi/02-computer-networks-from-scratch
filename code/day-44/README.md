# Day 44: DHCP Relay Agent Cross-Subnet Forwarder Lab Tutorial

Welcome to Day 44 of Computer Networks from Scratch. Today, you will build an RFC 3046 compliant DHCP Relay Agent with Option 82 injection and hop count loop suppression.

---

## 1. What Are We Building & Why Does It Matter?

Because DHCP client requests are broadcast (`255.255.255.255`), Layer 3 routers drop them by default to prevent broadcast storms. Without a relay mechanism, organizations would need a separate physical DHCP server on every single VLAN and subnet.

A **DHCP Relay Agent** (such as Cisco IP Helper or ISC `dhcrelay`):
1. Listens for client broadcasts on local interfaces.
2. Injects its own interface IP into the `giaddr` (Gateway IP Address) header field.
3. Appends **Option 82** (Relay Agent Information: Circuit ID and Remote ID) to identify the client's switch port.
4. Unicasts the packet across the corporate WAN to a centralized DHCP server cluster.
5. On receiving replies, strips Option 82 and broadcasts or unicasts the configuration back onto the client's local wire.

---

## 2. Python Concepts for Beginners

### A. Sub-Option Nesting with `struct`
Option 82 contains inner TLVs:
```python
import struct

sub_option_1 = struct.pack("!BB", 1, len(circuit_id)) + circuit_id.encode("ascii")
```

### B. Interface Dictionary Mapping
Use dictionaries to map hardware interfaces to assigned gateway IP addresses:
```python
interface_ips = {
    "eth1": "192.168.10.1",
    "eth2": "192.168.20.1"
}
```

### C. Dictionary Popping (`dict.pop`)
Remove an option while extracting its contents:
```python
raw_opt82 = pkt.options.pop(82)
```

---

## 3. Step-by-Step Code Walkthrough

1. **`RelayPacket` Dataclass**: Captures the essential header fields (`op`, `xid`, `hops`, `giaddr`, `chaddr`, `options`).
2. **`DHCPRelayAgent` Class**:
   - `encode_option_82()`: Serializes Circuit ID (Sub-option 1) and Remote ID (Sub-option 2).
   - `forward_client_request()`:
     - Validates incoming interface.
     - Enforces `hops < 16` to terminate routing loops.
     - Increments `hops`.
     - Populates `giaddr` with the relay's local interface IP so the upstream server knows which IP pool to draw from.
     - Appends Option 82 and forwards unicast to `upstream_server_ip`.
   - `forward_server_reply()`:
     - Decodes and strips Option 82.
     - Matches `giaddr` to locate the target local interface.
3. **`main()` Test Suite**: Verifies client request forwarding, Option 82 injection/stripping, and hop-limit drop behavior.

---

## 4. How to Run & Expected Output

Execute the script with Python 3:
```bash
python code/day-44/dhcp_relay_agent_forwarder.py
```

Expected output:
```text
=== Day 44: DHCP Relay Agent Cross-Subnet Forwarder Simulator ===
[*] Client DISCOVER relayed to 10.0.0.5: giaddr=192.168.10.1, hops=1
[*] Injected Option 82: Circuit ID='vlan100-eth1', Remote ID='switch-core-01-00:11:22:33:44:55'
[*] Server OFFER stripped Option 82 and forwarded to subnet on eth1
[*] Hop count >= 16 loop detection successfully dropped packet
All DHCP Relay Agent assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`KeyError: 82`**: Occurs if attempting to strip Option 82 when the server failed to echo it back. Always check `if 82 in pkt.options:` before popping.
- **`IndexError` in sub-option parsing**: Occurs if the length byte in a nested TLV exceeds the buffer slice. Always validate `idx + 2 + sub_len <= len(raw)`.

---

## 6. Beginner Exercises & Challenges

1. **Track Hop Count History**: Maintain a list of all relay IP addresses that touched the packet in order to trace complex multi-hop relay topologies.
2. **Implement Rate Limiting**: Limit relay forwarding to 100 packets/sec per incoming interface to protect upstream centralized servers from DoS flooding.
3. **Add Option 82 Link Selection (Sub-option 5)**: Implement RFC 3527 Link Selection Sub-option allowing relays to specify a subnet pool distinct from `giaddr`.
