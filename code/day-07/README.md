# Day 07 Lab: IPv4 Packet Fragmentation & Reassembly in Python

> **Welcome to Day 7!** Standard Ethernet networks have a strict packet size limit called the **MTU (Maximum Transmission Unit)**, typically **1,500 bytes**.
> What happens when an application wants to send a 4,000-byte file? The router must dismantle it into smaller fragments! In this lab, you will learn the exact mathematics of IP fragmentation and destination reassembly.

---

## 🎯 What Does This Lab Do?
`fragmentation_simulator.py` demonstrates:
1. **The 8-Byte Alignment Rule**: Why the payload of every fragment (except the last) must be an exact multiple of 8 bytes ($1480 / 8 = 185$ blocks).
2. **Flag Control**:
   - `DF` (Don't Fragment): Tells routers never to fragment this packet.
   - `MF` (More Fragments): Tells the recipient that additional pieces are on the way.
3. **Out-of-Order Reassembly**: Proves that even if fragments arrive shuffled over the Internet, the destination host sorts them by `Fragment Offset` and reconstructs the original file with 100% byte fidelity!

---

## 🚀 How to Run the Code
Run the script in your terminal:
```bash
python fragmentation_simulator.py
```

---

## 💡 Python Concepts Used in This Script (For Beginners)

### 1. The `@property` Decorator
* Normally, a function is called like `obj.get_offset()`.
* Adding `@property` above a method lets you access it like a normal variable:
  ```python
  @property
  def byte_offset(self):
      return self.offset * 8
  ```
  Now you can simply write `frag.byte_offset` without parentheses!

### 2. Sorting Objects with Lambda Functions
* When fragments arrive out of order, we sort them by their offset using a tiny anonymous function (`lambda`):
  ```python
  sorted_frags = sorted(fragments, key=lambda f: f.byte_offset)
  ```
* This tells Python: *"Look at the `.byte_offset` attribute of each fragment and sort from smallest (0) to largest."*

### 3. Mutable Bytes with `bytearray`
* In Python, `bytes` are immutable (cannot be modified once created).
* `bytearray()` is a mutable array of bytes: you can continuously append new incoming data using `.extend(chunk)`.
* Calling `bytes(my_bytearray)` seals it into an immutable binary object.

---

## 🔍 Code Walkthrough

```python
# 1. Router Fragmentation Logic:
max_raw_payload = mtu - 20 # 1500 - 20 = 1480 bytes
# Ensure max payload is a multiple of 8:
max_aligned_payload = max_raw_payload - (max_raw_payload % 8)

while remaining_data:
    chunk = remaining_data[:max_aligned_payload]
    remaining_data = remaining_data[max_aligned_payload:]
    
    # Offset is stored in 8-byte units:
    offset_units = current_byte_offset // 8
    is_more = len(remaining_data) > 0
    
    fragments.append(IPv4Fragment(ident, df=False, mf=is_more, offset=offset_units, payload=chunk))
    current_byte_offset += len(chunk)
```

---

## 📋 Expected Terminal Output
```text
============================================================
DAY 07 LAB: IPV4 FRAGMENTATION & REASSEMBLY SIMULATOR
============================================================

[1] Original Datagram: 20-byte IP Header + 3980-byte Payload = 4,000 bytes.

[2] Forwarding across Link MTU = 1500 bytes (DF=0)...
    Generated 3 fragments:
    - Fragment 1: <Frag ID=0x4a21 | Len=1500B | DF=0 MF=1 | Offset=0 (0B)> | Payload = 1480 bytes
    - Fragment 2: <Frag ID=0x4a21 | Len=1500B | DF=0 MF=1 | Offset=185 (1480B)> | Payload = 1480 bytes
    - Fragment 3: <Frag ID=0x4a21 | Len=1040B | DF=0 MF=0 | Offset=370 (2960B)> | Payload = 1020 bytes
    [PASS] 8-byte offset alignment and MF flags mathematically verified.

[3] Simulating Destination Host Reassembly...
    Successfully reconstructed 3980 bytes without loss.
    [PASS] Out-of-order reassembly completed with 100% byte fidelity.

[4] Testing Path MTU Discovery constraint (DF=1)...
    Router Response: ICMP Type 3, Code 4: Fragmentation Needed and DF Set!
    [PASS] Router correctly rejected oversize packet and triggered ICMP Type 3 Code 4.
============================================================
```

---

## 🧪 Beginner Practice Challenges
1. **Challenge 1**: Look at Fragment 2. Why is `Offset=185` instead of `1480`? (Answer: Because $185 \times 8\text{ bytes} = 1480\text{ bytes}!$ The offset field stores 8-byte units).
2. **Challenge 2**: In `fragmentation_simulator.py`, what happens if you set `mtu = 1000`? How many fragments are created?
