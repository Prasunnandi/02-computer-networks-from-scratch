# Day 08 Lab: ICMP Protocol & Custom Traceroute Simulator in Python

> **Welcome to Day 8!** Ever wonder what happens when you type `ping google.com` or run `traceroute`?
> Neither routers nor servers have a special "traceroute protocol". Traceroute is an ingenious trick using the **IPv4 TTL expiration** and **ICMP (Internet Control Message Protocol)**. In this lab, you will build an end-to-end traceroute simulator in Python!

---

## 🎯 What Does This Lab Do?
`custom_traceroute.py` demonstrates:
1. **ICMP Binary Encoding**: Packs 8-byte ICMP headers with dynamic 16-bit checksums:
   - `Type 8, Code 0`: Echo Request (`ping` sent)
   - `Type 0, Code 0`: Echo Reply (`ping` received)
   - `Type 11, Code 0`: Time Exceeded (TTL hit 0 at an intermediate router!)
2. **Hop-by-Hop Discovery**: Sends probes starting with `TTL = 1`, then `TTL = 2`, discovering each intermediate router along the route.
3. **Firewall Drop Handling**: Shows how routers that drop ICMP appear as `* * *` (timeout).

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python custom_traceroute.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Class Constants
* In Python, variables defined directly inside a class with all-caps names are called **constants**:
  ```python
  class ICMPPacket:
      TYPE_ECHO_REPLY = 0
      TYPE_DEST_UNREACHABLE = 3
      TYPE_ECHO_REQUEST = 8
      TYPE_TIME_EXCEEDED = 11
  ```
* This makes code readable: writing `ICMPPacket.TYPE_ECHO_REQUEST` is much clearer than remembering the magic number `8`!

### 2. Packing Binary ICMP Headers: `!BBHHH`
* `B` (1 byte): Type
* `B` (1 byte): Code
* `H` (2 bytes): 16-bit Checksum
* `H` (2 bytes): Identifier
* `H` (2 bytes): Sequence Number
* Total: Exactly 8 bytes!

### 3. Simulating Route Topology with Objects
* We create a list of Python objects to represent routers on the path from your home to Google:
  ```python
  simulated_topology = [
      SimulatedNetworkRouter("192.168.1.1", "home-gateway.local", hop_delay_ms=0.8),
      SimulatedNetworkRouter("10.240.0.1", "isp-edge-node.net", hop_delay_ms=2.1),
      SimulatedNetworkRouter("142.250.190.46", "dns.google", hop_delay_ms=4.2)
  ]
  ```

---

## 🔍 Code Walkthrough

```python
# The Traceroute Probing Loop:
for ttl in range(1, max_hops + 1):
    target_node = self.route_path[ttl - 1]
    
    # If this is an intermediate router:
    # Router decrements TTL to 0 and replies with Time Exceeded (Type 11)!
    if not is_final_destination:
        reply = ICMPPacket.encode(ICMPPacket.TYPE_TIME_EXCEEDED, 0, ident=1234, seq=ttl)
    else:
        # Reached target server: Server replies with Echo Reply (Type 0)!
        reply = ICMPPacket.encode(ICMPPacket.TYPE_ECHO_REPLY, 0, ident=1234, seq=ttl)
```

---

## 📋 Expected Terminal Output
```text
============================================================
DAY 08 LAB: ICMP PROTOCOL ENCODER & TRACEROUTE SIMULATOR
============================================================

[1] Encoding ICMP Echo Request (Type 8)...
    Decoded: Type=8, Code=0, ValidChecksum=True
    [PASS] ICMP Echo Request packed and validated successfully.

[2] Executing Simulated Traceroute to 142.250.190.46 (dns.google)...

HOP  IP ADDRESS         HOSTNAME                       RTT        STATUS
--------------------------------------------------------------------------------
1    192.168.1.1        home-gateway.local             1.6 ms     TTL_EXPIRED (ICMP Time Exceeded)
2    10.240.0.1         isp-edge-node.net              5.8 ms     TTL_EXPIRED (ICMP Time Exceeded)
3    198.51.100.42      transit-backbone.tier1.com     18.8 ms    TTL_EXPIRED (ICMP Time Exceeded)
4    *                  *                              * * *      TIMEOUT (* * *)
5    142.250.190.46     dns.google                     37.2 ms    REACHED_TARGET (Echo Reply)

    [PASS] Traceroute successfully discovered topology, simulated firewall drop, and terminated at destination.
============================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: Look at Hop 4 in the output above. Why did it display `* * *`? (Answer: The router at Hop 4 had `drops_icmp=True` configured to simulate a security firewall).
2. **Challenge 2**: On your real machine, open PowerShell and run `tracert 8.8.8.8` to see real Internet routers between your computer and Google!
