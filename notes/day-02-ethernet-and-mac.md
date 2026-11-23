# 📦 Day 2: Ethernet Frames & Hardware MAC Addresses

> **Zero External Dependency Rule**: Everything you need to master this topic is contained right here in this document. You do NOT need to visit any external website or search Google.

---

## 1. The Core Problem: How Do Electrical Pulses Form Messages?

On Day 1, we learned that cables carry pulses of `1`s and `0`s.
But if a computer receives a continuous stream:
`101010101100010101110010101...`
* Where does the message start?
* Where does it end?
* Who sent it?
* Who is supposed to receive it?
* Did electrical noise corrupt the bits along the way?

To solve this, Robert Metcalfe invented **Ethernet** at Xerox PARC in 1973. Ethernet wraps raw bits inside a structured package called an **Ethernet Frame**.

---

## 2. Real-World Analogy: The Postal Envelope on Your Desk

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           THE POSTAL ENVELOPE                          │
 │                                                                        │
 │  TO (Destination)  : B4:2E:99:11:22:33 (Your Home Wi-Fi Router)        │
 │  FROM (Source)     : 00:1A:2B:AA:BB:CC (Your Laptop's Wi-Fi Card)      │
 │  STAMP (EtherType) : 0x0800 (Contains an IPv4 Internet Packet!)        │
 │                                                                        │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │                  THE LETTER INSIDE (PAYLOAD)                     │  │
 │  │        "GET /index.html HTTP/1.1 (User wants Google Homepage)"   │  │
 │  └──────────────────────────────────────────────────────────────────┘  │
 │                                                                        │
 │  SEAL CHECK (CRC)  : 0x3F2B9A1C (Mathematical proof of zero damage)    │
 └────────────────────────────────────────────────────────────────────────┘
```

An **Ethernet Frame** is the physical envelope of the digital world. It wraps your data before it flies across copper wires, optical fibers, or radio Wi-Fi waves.

---

## 3. The Anatomy of an Ethernet Frame (Byte-by-Byte)

The IEEE 802.3 standard defines the exact sequence of bytes in every standard Ethernet II frame:

```
┌───────────┬─────────────┬─────────────┬───────────┬───────────────────┬───────────┐
│ PREAMBLE  │ DESTINATION │   SOURCE    │ ETHERTYPE │   PAYLOAD DATA    │    CRC    │
│   + SFD   │ MAC ADDRESS │ MAC ADDRESS │           │                   │ CHECKSUM  │
│ (8 Bytes) │  (6 Bytes)  │  (6 Bytes)  │ (2 Bytes) │(46 - 1500 Bytes)  │ (4 Bytes) │
└───────────┴─────────────┴─────────────┴───────────┴───────────────────┴───────────┘
```

### Detailed Breakdown of Every Field:

### 1. Preamble & SFD (8 Bytes)
* **What it does**: Wakes up the receiving network card's electronics!
* **The Pattern**: 7 bytes of alternating `10101010` bits to synchronize the clock, followed by 1 byte of **Start Frame Delimiter (SFD)**: `10101011`. That final double `11` signals: *"Get ready! The actual destination address begins on the very next bit!"*

### 2. Destination MAC Address (6 Bytes / 48 Bits)
* The physical hardware address of the device on the local network that should accept this frame (e.g. your Wi-Fi router).
* If sending to everyone on the network, it uses the special **Broadcast MAC**: `FF:FF:FF:FF:FF:FF`.

### 3. Source MAC Address (6 Bytes / 48 Bits)
* The physical hardware address of the network interface card (NIC) that transmitted the frame.

### 4. EtherType (2 Bytes)
* Identifies what higher-level protocol is wrapped inside the payload:
  * **`0x0800`** $\rightarrow$ **IPv4** Internet Protocol packet inside.
  * **`0x0806`** $\rightarrow$ **ARP** (Address Resolution Protocol) query inside.
  * **`0x86DD`** $\rightarrow$ **IPv6** Internet Protocol packet inside.

### 5. Payload (46 to 1500 Bytes)
* The actual data being transported.
* **The Minimum Size Rule (46 Bytes)**: If the payload is smaller than 46 bytes, the card automatically adds **padding zero bytes** so the frame meets the minimum 64-byte total size needed for collision detection (CSMA/CD).
* **The Maximum Transmission Unit (MTU)**: The maximum standard payload size is **1500 Bytes**.

### 6. Frame Check Sequence / CRC (4 Bytes)
* A cyclic redundancy check (CRC-32) calculation. The sender computes a mathematical checksum of all preceding bytes. The receiver computes the same math. If even a single bit flipped due to electrical interference, the receiver **silently drops the damaged frame**!

---

## 4. What is a MAC Address (Media Access Control)?

A MAC address is a 48-bit (6-byte) physical hardware identifier burned into your network card at the factory:

$$\text{B4 : 2E : 99 : A1 : 0F : 7D}$$

* **First 3 Bytes (`B4:2E:99`) $\rightarrow$ OUI (Organizationally Unique Identifier)**: Assigned by the IEEE to the hardware manufacturer (e.g., Apple, Intel, Cisco).
* **Last 3 Bytes (`A1:0F:7D`) $\rightarrow$ Device Identifier**: A unique serial number assigned by the manufacturer to that specific chip.

---

## 5. Complete Self-Contained Q&A

**Q1: What is the maximum payload size (MTU) of a standard Ethernet frame?**  
**Answer**: **1,500 bytes**.

**Q2: What happens if an Ethernet frame is smaller than 64 bytes total?**  
**Answer**: The network card adds padding bytes to expand it to 64 bytes. If a receiver gets a frame smaller than 64 bytes without padding, it is classified as a collision error ("runt packet") and discarded.

**Q3: Can two network cards in the world have the same MAC address?**  
**Answer**: In theory, no. The IEEE assigns unique 3-byte vendor prefixes (OUIs) to each manufacturer to guarantee global uniqueness. However, modern operating systems allow software MAC-spoofing or randomized MAC addresses for privacy on public Wi-Fi.

---

## 6. Hands-on Lab Verification

Run the raw frame decoder in `code/day-02/`:
```bash
python code/day-02/parse_ethernet_frame.py
```
Observe how the 14-byte header is extracted from raw hex bytes to identify source, destination, and payload protocol!
