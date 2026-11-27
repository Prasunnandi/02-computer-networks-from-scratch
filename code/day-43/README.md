# Day 43: DHCP Dynamic Lease Renewal & Rebinding Timer Engine Lab Tutorial

Welcome to Day 43 of Computer Networks from Scratch. Today, you will build an RFC 2131 compliant lease timer engine that orchestrates T1 unicast renewal, T2 broadcast rebinding, and IP expiration.

---

## 1. What Are We Building & Why Does It Matter?

DHCP IP addresses are never permanently assigned. Instead, they are leased for a finite duration (e.g., 24 hours, 7 days). To prevent network disruption, the client continuously maintains its lease using two internal timers:
1. **T1 Timer (0.50 * Lease Duration)**: At 50% elapsed time, the client unicasts a `DHCPREQUEST` directly to the server that granted the lease.
2. **T2 Timer (0.875 * Lease Duration)**: If the original server fails to respond by 87.5% elapsed time, the client assumes the server is dead and broadcasts `DHCPREQUEST` to any available DHCP server on the subnet.
3. **Lease Expiration (1.00 * Lease Duration)**: If no server responds before 100% elapsed time, the client must immediately release the IP address and halt all network traffic.

In this lab, you implement this timer state engine and simulate real-world failure scenarios including primary server outages and total network loss.

---

## 2. Python Concepts for Beginners

### A. Python Properties (`@property`)
The `@property` decorator allows a method to be accessed like an attribute, calculating dynamic values on the fly:
```python
class LeaseContract:
    def __init__(self, start_time: float, lease_duration: float):
        self.start_time = start_time
        self.lease_duration = lease_duration

    @property
    def t1_time(self) -> float:
        return self.start_time + (self.lease_duration * 0.50)
```

### B. Tuple Unpacking in Return Values
Functions can return multiple values bundled as tuples:
```python
state, action_message = engine.simulate_tick(current_time=60.0, server_reachable=False)
```

### C. State Machine Assertions
Use `assert` statements to formally verify state transitions:
```python
assert engine.state == LeaseState.RENEWING
```

---

## 3. Step-by-Step Code Walkthrough

1. **`LeaseState` Enum**: Represents the RFC 2131 lifecycle states (`BOUND`, `RENEWING`, `REBINDING`, `EXPIRED`).
2. **`LeaseContract` Dataclass**: Stores client IP, lease server IP, start timestamp, and calculates `t1_time`, `t2_time`, and `expire_time`.
3. **`DHCPLeaseTimerEngine`**:
   - `evaluate_state()`: Compares current time against threshold formulas. Priority order: `expire_time` > `t2_time` > `t1_time`.
   - `simulate_tick()`: Executes scheduled polling. If in `RENEWING`, attempts unicast renewal with the originating server. If in `REBINDING`, attempts broadcast rebinding with backup servers.
4. **`main()` Test Suite**:
   - Scenario 1: Demonstrates successful T1 renewal resetting the contract timestamp.
   - Scenario 2: Demonstrates failure of the primary server triggering T2 broadcast rebinding.
   - Scenario 3: Demonstrates total server unavailability leading to complete lease expiration.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-43/dhcp_lease_timer_engine.py
```

Expected output:
```text
=== Day 43: DHCP Dynamic Lease Renewal & Rebinding Timer Engine ===
[*] Scenario 1 Passed: T1 Unicast Renewal reset lease at t=50.0s
[*] Scenario 2 Passed: T2 Rebind successfully recovered via broadcast backup server
[*] Scenario 3 Passed: Lease expired at t=105s, IP reclaimed
All DHCP Lease Timer Engine assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`TypeError: unsupported operand type(s) for +: 'float' and 'NoneType'`**: Ensure all timestamp fields (`start_time`, `lease_duration`) are initialized with non-null numeric values.
- **Clock Drift / Out-of-Order Ticks**: If `current_time` jumps backwards (e.g. system time synchronization via NTP), `evaluate_state()` may report invalid transitions. In production systems, monotonic timers (`time.monotonic()`) must be used instead of wall-clock time.

---

## 6. Beginner Exercises & Challenges

1. **Implement Exponential Backoff Retries**: Update `simulate_tick()` to retransmit renewal requests at intervals of 4s, 8s, 16s with random jitter as specified in RFC 2131 Section 4.1.
2. **Add DHCPNAK Handling**: If a client attempts to renew or rebind on a foreign subnet, the server sends a `DHCPNAK`. Add logic where a `DHCPNAK` immediately transitions the client to `EXPIRED`.
3. **Persist Leases to JSON**: Add a serialization method that saves active lease contracts to a local JSON file to simulate client reboot persistence.
