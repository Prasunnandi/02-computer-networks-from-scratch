# Day 04 Lab: IPv4 Subnetting & CIDR Calculator in Python

> **Welcome to Day 4!** In this lab, we dive into how the entire global Internet routes traffic: **IPv4 Subnetting & CIDR Notation** (like `192.168.1.0/24`). You will learn how routers use 32-bit binary arithmetic and bitwise AND masking to group computers into subnets.

---

## 🎯 What Does This Lab Do?
`subnet_calculator.py` takes any CIDR string (like `192.168.1.50/24`) and calculates:
1. **The Subnet Mask**: Translates `/24` into `255.255.255.0`.
2. **The Network Address**: The starting identifier of the subnet (`192.168.1.0`).
3. **The Broadcast Address**: The address used to shout to every device in this subnet (`192.168.1.255`).
4. **The Usable Host Range**: The exact IP range you can assign to laptops and servers (`192.168.1.1` to `192.168.1.254`).
5. **Total Usable Hosts**: Calculates $2^{(32 - \text{prefix})} - 2 = 254$ available IPs.

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python subnet_calculator.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. Packing 4 Bytes into a 32-Bit Integer
* An IPv4 address like `192.168.1.1` is made of four 8-bit numbers (octets).
* Computers don't think in dots; they think in one big 32-bit number!
* To combine four bytes into one 32-bit integer:
  ```python
  (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
  ```
  - Shift Octet 0 left by 24 bits (Bits 24–31)
  - Shift Octet 1 left by 16 bits (Bits 16–23)
  - Shift Octet 2 left by 8 bits (Bits 8–15)
  - Octet 3 sits in the lowest 8 bits (Bits 0–7)

### 2. Extracting Bytes with Bitwise AND (`& 0xFF`)
* To unpack the 32-bit integer back into dotted decimal format:
  ```python
  (ip_int >> 24) & 0xFF  # Grabs the first byte
  (ip_int >> 16) & 0xFF  # Grabs the second byte
  ```
* `& 0xFF` (which is `255` or binary `11111111`) acts as a cookie-cutter, cutting out exactly 8 bits.

### 3. Calculating Network ID with Bitwise AND (`&`)
* The core mathematical equation of Internet routing:
  $$\text{Network ID} = \text{IP Address} \ \& \ \text{Subnet Mask}$$
* In Python:
  ```python
  network_int = ip_int & netmask_int
  ```

---

## 🔍 Code Walkthrough

```python
def calculate_subnet(cidr_str):
    ip_part, prefix_part = cidr_str.split("/")
    prefix = int(prefix_part) # e.g. 24

    ip_int = ip_str_to_int(ip_part)
    
    # Generate netmask (shift 32 - prefix bits)
    netmask_int = ((0xFFFFFFFF << (32 - prefix))) & 0xFFFFFFFF

    # Network ID = IP & Mask
    network_int = ip_int & netmask_int

    # Wildcard = Inverse of Netmask
    wildcard_int = (~netmask_int) & 0xFFFFFFFF
    
    # Broadcast ID = Network ID | Wildcard
    broadcast_int = network_int | wildcard_int
    
    usable_hosts = 2 ** (32 - prefix) - 2
    return network_int, broadcast_int, usable_hosts
```

---

## 📋 Expected Terminal Output
```text
==================================================
   DAY 4 LAB: IPV4 SUBNET CALCULATOR             
==================================================
Subnet Analysis for: 192.168.1.50/24
--------------------------------------------------
IP Address        : 192.168.1.50
Subnet Mask       : 255.255.255.0
Network Address   : 192.168.1.0
Broadcast Address : 192.168.1.255
Usable Host Range : 192.168.1.1 - 192.168.1.254
Total Usable Hosts: 254
==================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: Run `calculate_subnet("10.0.0.1/8")`. How many usable hosts exist in a `/8` network? (Answer: Over 16 Million hosts!).
2. **Challenge 2**: Why do we subtract 2 when calculating usable hosts ($2^{\text{host bits}} - 2$)? (Answer: The first IP is reserved for the Network ID, and the last IP is reserved for Broadcast!).
