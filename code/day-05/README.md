# Day 05 Lab: Network Address Translation (NAT) Router Simulator in Python

> **Welcome to Day 5!** In your home or office, you might have 20 devices (laptops, phones, smart TVs) connected to Wi-Fi. Yet your Internet Service Provider (ISP) gave your home only **ONE single public IPv4 address**!
> How do all 20 devices browse the web at the same time without their downloads colliding? Through the magic of **NAT (Network Address Translation)**!

---

## 🎯 What Does This Lab Do?
`nat_simulator.py` simulates how a home Wi-Fi router translates traffic:
1. **Outbound Rewriting (SNAT)**: When your laptop (`192.168.1.10:45000`) sends a message to Google (`142.250.190.46:443`), the router changes the source IP to its own public IP (`203.0.113.1`) and assigns a unique external port (`50000`).
2. **Stateful Connection Tracking**: The router records this mapping in its internal memory:
   $$\text{Port } 50000 \longleftrightarrow (192.168.1.10, 45000)$$
3. **Inbound Demultiplexing (DNAT)**: When Google replies to `203.0.113.1:50000`, the router looks up Port 50000, rewrites the destination back to `192.168.1.10:45000`, and forwards the packet directly to your laptop!

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python nat_simulator.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Stateful Tracking with Dictionaries
* The router must remember who sent which packet so it can route the reply back to the right person.
* In Python, we use a dictionary mapping the external port to a tuple:
  ```python
  self.nat_table[50000] = ("192.168.1.10", 45000)
  ```

### 2. Incrementing Port Counters
* Each new outgoing connection gets a new port:
  ```python
  ext_port = self.next_external_port
  self.next_external_port += 1
  ```
* This ensures that two laptops opening connections at the exact same second get distinct external port numbers (`50000` and `50001`).

---

## 🔍 Code Walkthrough

```python
class NATRouterSimulator:
    def __init__(self, public_ip="203.0.113.1"):
        self.public_ip = public_ip
        self.nat_table = {}
        self.next_external_port = 50000

    def send_outbound_packet(self, private_ip, private_port, dst_ip, dst_port, payload):
        ext_port = self.next_external_port
        self.next_external_port += 1
        
        # Save mapping
        self.nat_table[ext_port] = (private_ip, private_port)
        
        # Return rewritten packet
        return {"src_ip": self.public_ip, "src_port": ext_port, "payload": payload}

    def receive_inbound_packet(self, inbound_packet):
        target_port = inbound_packet["dest_port"]
        
        # Reverse lookup in NAT table!
        if target_port in self.nat_table:
            private_ip, private_port = self.nat_table[target_port]
            print(f"Forwarding back to internal device: {private_ip}:{private_port}")
```

---

## 📋 Expected Terminal Output
```text
==================================================
   DAY 5 LAB: NAT (PORT OVERLOAD) ROUTER SIMULATOR
==================================================

[OUTBOUND PACKET CREATED]
  Internal Origin : 192.168.1.10:45000
  NAT Rewriting   : Source changed to 203.0.113.1:50000 (NAT table updated!)
  Destination     : 142.250.190.46:443
  Payload         : 'GET /index.html'

[INBOUND PACKET RECEIVED FROM INTERNET]
  Public Target   : 203.0.113.1:50000
  NAT Table Match : Port 50000 belongs to 192.168.1.10:45000!
  Forwarding      : Packet delivered to laptop successfully.
==================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: What happens if an external hacker on the Internet tries to send a packet directly to `203.0.113.1:54321` when no device on your internal network opened port 54321? (Answer: The router drops it because it's not in the NAT table—NAT acts as a natural incoming firewall!).
2. **Challenge 2**: What is "Port Forwarding" in video gaming? (Answer: Telling your router in advance: *"Permanently map external port 25565 to my gaming PC so friends can connect to my Minecraft server!"*).
