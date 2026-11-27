# Day 45: Layer 2 DHCP Snooping Switch Simulator Lab Tutorial

Welcome to Day 45 of Computer Networks from Scratch. Today, you will build an enterprise Layer 2 security engine that enforces DHCP Snooping, blocks rogue DHCP servers, and builds a dynamic binding database.

---

## 1. What Are We Building & Why Does It Matter?

Because DHCP messages are unauthenticated broadcasts, any malicious device connected to a switch port can respond to client `DHCPDISCOVER` packets. A rogue DHCP server can:
- Assign itself as the default gateway to perform Man-In-The-Middle (MITM) traffic interception.
- Hand out malicious DNS server IPs to hijack user domains (DNS spoofing).
- Hand out invalid IPs to cause a localized Denial of Service (DoS).

**DHCP Snooping** solves this by:
1. Classifying switch ports as **Trusted** (uplinks connected to verified network servers) or **Untrusted** (edge ports connected to end users).
2. Dropping all server messages (`DHCPOFFER`, `DHCPACK`, `DHCPNAK`) received on untrusted ports.
3. Building a **DHCP Snooping Binding Table** recording the valid `[MAC, IP, VLAN, Interface, Lease]` mappings.
4. Enforcing packet rate limits on untrusted ports to prevent DHCP starvation attacks.

---

## 2. Python Concepts for Beginners

### A. Security Classification with Enums
Enums provide readable, type-safe security state definitions:
```python
import enum

class PortTrust(enum.Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"
```

### B. Sliding-Window Rate Limiting
Maintain a list of request timestamps and filter out entries older than 1 second:
```python
history = [t for t in history if current_time - t < 1.0]
if len(history) >= max_limit:
    return False  # Rate limit exceeded
```

### C. Integrating Security Databases
The snooping table provides the ground truth used by downstream features like IP Source Guard and Dynamic ARP Inspection (DAI):
```python
is_valid = binding_table[src_mac].ip_address == src_ip
```

---

## 3. Step-by-Step Code Walkthrough

1. **`PortTrust` & `BindingEntry`**: Defines port security trust levels and database records.
2. **`DHCPSnoopingSwitch`**:
   - `_check_rate_limit()`: Drops traffic if an untrusted access port emits more than N DHCP packets per second.
   - `process_packet()`:
     - Applies rate limiting.
     - Inspects message type: if type is `OFFER` (2) or `ACK` (5) and port is `UNTRUSTED`, logs a security alert and drops the frame.
     - If type is `ACK` (5) on a `TRUSTED` port, extracts network parameters and inserts a new record into `self.binding_db`.
   - `verify_source_ip()`: Validates packets against the binding database, verifying that the IP has not been spoofed and the lease has not expired.
3. **`main()` Test Suite**: Validates client discovery, rogue offer suppression, binding database creation, IP spoofing prevention, and starvation attack rate-limiting.

---

## 4. How to Run & Expected Output

Execute the script with Python 3:
```bash
python code/day-45/dhcp_snooping_switch_simulator.py
```

Expected output:
```text
=== Day 45: Layer 2 DHCP Snooping Switch Simulator ===
[*] Test 1 Passed: Client DISCOVER on untrusted Gi0/2 allowed (Packet forwarded)
[*] Test 2 Passed: Rogue OFFER on Gi0/3 blocked (SECURITY ALERT: Blocked rogue DHCP reply (type 2) on untrusted port Gi0/3)
[*] Test 3 Passed: Legitimate ACK on trusted Gi0/1 accepted. Learned binding: 00:11:22:33:44:01 -> 192.168.10.55 on VLAN 10
[*] Test 4 Passed: IP Source Guard successfully validated legitimate and rejected spoofed IP
[*] Test 5 Passed: DHCP starvation attack rate-limited (Rate limit exceeded on untrusted port Gi0/2)
All DHCP Snooping Switch assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`KeyError` in port lookup**: Ensure all switch interfaces are registered in `self.ports`. Provide a default fallback to `PortTrust.UNTRUSTED` for unconfigured ports.
- **Timestamp Arithmetic Errors**: Always use relative floating-point timestamps (seconds) consistently when calculating `expiry_timestamp`.

---

## 6. Beginner Exercises & Challenges

1. **Implement Dynamic ARP Inspection (DAI)**: Write an `inspect_arp()` method that intercepts ARP packets and drops gratuitous ARP replies if the sender IP and MAC do not match the snooping database.
2. **Add Port Error-Disable Mode**: Modify rate limiting so that if an untrusted port violates the rate limit 3 times, its status is changed to `ERR_DISABLE` and all traffic is dropped.
3. **Export Binding Database to CSV**: Add a method to dump the active DHCP snooping table to a CSV file.
