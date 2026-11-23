# Day 03 Lab: Address Resolution Protocol (ARP) & Cache Simulator in Python

> **Welcome to Day 3!** When your computer wants to send an email to IP `192.168.1.15`, the network card cannot send an IP packet directly onto the wire. It MUST know the physical hardware address (**MAC Address**) of the destination card.
> How does your computer find the MAC address? By shouting over the local network using **ARP (Address Resolution Protocol)**!

---

## 🎯 What Does This Lab Do?
`arp_cache_simulator.py` simulates how your operating system discovers hardware addresses:
1. **Cache Lookup**: Before sending any network packet, the OS checks its local memory (**The ARP Table**) to see if it already knows the MAC address.
2. **Cache Miss & Broadcast**: If the IP is not in memory, the OS broadcasts an ARP Request to `FF:FF:FF:FF:FF:FF` shouting: *"Who has 192.168.1.15? Tell 192.168.1.100!"*
3. **Unicast Reply & Caching**: The owner of that IP hears the shout and replies directly: *"That is me! My MAC is A4:C3:F0:12:34:56!"* The OS caches this so future packets don't waste network bandwidth shouting!

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python arp_cache_simulator.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Dictionaries as Memory Caches
* In Python, a dictionary is ideal for caching:
  ```python
  self.arp_table = {}
  ```
* When an IP is discovered, we save it:
  ```python
  self.arp_table["192.168.1.15"] = "A4:C3:F0:12:34:56"
  ```
* On the next packet, checking `if "192.168.1.15" in self.arp_table:` takes $O(1)$ constant time (instant lookup!).

### 2. The `self` Keyword in Python Classes
* In Python classes, functions are called **methods**.
* The first parameter of every method is `self`.
* `self` refers to **this specific instance of the simulator**, allowing methods to share data like `self.arp_table` across multiple function calls.

---

## 🔍 Code Walkthrough

```python
class ARPCacheSimulator:
    def __init__(self):
        self.network_devices = {
            "192.168.1.1": "00:1A:2B:3C:4D:5E",
            "192.168.1.15": "A4:C3:F0:12:34:56"
        }
        self.arp_table = {} # Starts empty

    def resolve_ip_to_mac(self, target_ip):
        # Step 1: Check cache (Cache Hit)
        if target_ip in self.arp_table:
            print("CACHE HIT! Found in table.")
            return self.arp_table[target_ip]

        # Step 2: Cache Miss -> Broadcast on network
        print("CACHE MISS! Shouting broadcast to FF:FF:FF:FF:FF:FF...")
        resolved_mac = self.network_devices[target_ip]

        # Step 3: Cache the answer for future packets!
        self.arp_table[target_ip] = resolved_mac
        return resolved_mac
```

---

## 📋 Expected Terminal Output
```text
==================================================
   DAY 3 LAB: ARP PROTOCOL & CACHE SIMULATION     
==================================================

[QUERY] Need to send frame to IP: 192.168.1.15
  --> [CACHE MISS] IP 192.168.1.15 is NOT in local ARP table.
  --> [BROADCAST] Shouting to FF:FF:FF:FF:FF:FF: 'Who has 192.168.1.15? Tell my MAC!'
  --> [UNICAST REPLY] Device with IP 192.168.1.15 heard the shout and replied: My MAC is A4:C3:F0:12:34:56!
  --> Cached mapping in local table: 192.168.1.15 -> A4:C3:F0:12:34:56

[QUERY] Need to send frame to IP: 192.168.1.15
  --> [CACHE HIT] Found in local ARP table: 192.168.1.15 -> A4:C3:F0:12:34:56 (No network broadcast needed!)
==================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: What happens when you query an IP that does NOT exist on the local network (e.g. `192.168.1.99`)? Run the script to see how the OS handles Host Unreachable!
2. **Challenge 2**: On your real computer, open PowerShell or Command Prompt and run `arp -a`. You will see your real computer's live ARP table!
