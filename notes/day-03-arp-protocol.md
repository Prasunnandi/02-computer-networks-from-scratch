# 📢 Day 3: Address Resolution Protocol (ARP) — "Who has this IP?"

> **Zero External Dependency Rule**: Everything you need to master this topic is contained right here in this document. You do NOT need to visit any external website or search Google.

---

## 1. The Core Problem: The Missing Link Between IP & MAC

When you want to visit `google.com`, your operating system decides:
> *"I need to send this packet to my Default Gateway (my home Wi-Fi router) at IP address `192.168.1.1`."*

**Here is the fatal problem**:
* Your Wi-Fi network card (NIC) **does not understand IP addresses**! Network cards are physical Layer 2 hardware that can ONLY send Ethernet frames to a physical **MAC Address**!
* Your computer knows the router's IP (`192.168.1.1`), but it has **no idea what the router's physical MAC address is**!

How does your computer discover the MAC address of an IP address?
It uses **ARP (Address Resolution Protocol - RFC 826)**.

---

## 2. Real-World Analogy: Shouting in a Crowded Classroom

Imagine a college classroom with 60 students:
The professor walks in holding an exam paper marked: **"Roll Number 42"**. The professor doesn't know what Student 42 looks like or which desk they sit in.

```
                  ┌──────────────────────────────────────────────┐
                  │                 THE CLASSROOM                │
                  │                                              │
[ Professor ] ────┼──► SHOUTS OUT LOUD (BROADCAST):              │
                  │    "Who has Roll Number 42?"                 │
                  │                                              │
                  │    ┌──────────────────┬──────────────────┐   │
                  │    ▼                  ▼                  ▼   │
                  │ Student 1        Student 2          Student 42
                  │ (Roll #1)        (Roll #2)          (Roll #42)
                  │ (Ignores)        (Ignores)               │   │
                  │                                          │   │
                  │    ◄── DIRECT WHISPER (UNICAST) ─────────┘   │
                  │        "That's me! I sit in Desk #5!"        │
                  │                                              │
                  │ [ Professor writes on notepad ]:             │
                  │ Roll Number 42 = Desk #5 (ARP Cache!)        │
                  └──────────────────────────────────────────────┘
```

1. **The Request is a Broadcast**: The professor shouts to **everyone** in the room.
2. **The Reply is a Unicast**: Only the student whose Roll Number matches stands up and answers back directly to the professor.
3. **The Notepad (ARP Cache)**: The professor writes the mapping on a notepad. For the rest of the day, the professor never has to shout again!

---

## 3. The 3-Step Mechanics of ARP

```
   YOUR LAPTOP                                                   YOUR ROUTER
 (192.168.1.5)                                                  (192.168.1.1)
  MAC: AA:AA:AA                                                  MAC: BB:BB:BB
       │                                                               │
       │ ──► [ STEP 1: ARP REQUEST (BROADCAST) ] ────────────────────► │
       │     Dst MAC: FF:FF:FF:FF:FF:FF (Sent to EVERYONE on Wi-Fi)    │
       │     Payload: "Who has IP 192.168.1.1? Tell AA:AA:AA!"         │
       │                                                               │
       │ ◄── [ STEP 2: ARP REPLY (UNICAST) ] ───────────────────────── │
       │     Dst MAC: AA:AA:AA (Directly to your laptop)               │
       │     Payload: "I have 192.168.1.1! My MAC is BB:BB:BB!"        │
       │                                                               │
       ▼                                                               ▼
   [ STEP 3: LAPTOP UPDATES LOCAL ARP TABLE ]
   IP 192.168.1.1 ──► BB:BB:BB (Cached for 20 minutes)
```

1. **Step 1 (ARP Request)**:
   * Destination MAC is set to `FF:FF:FF:FF:FF:FF` (the universal broadcast address).
   * Every network switch and device on the local network receives this frame.
2. **Step 2 (ARP Reply)**:
   * Every device whose IP does *not* match drops the packet.
   * The device that owns `192.168.1.1` builds an ARP Reply packet, places its own MAC address inside, and sends it directly back (unicast) to your laptop.
3. **Step 3 (ARP Caching)**:
   * Your laptop stores `192.168.1.1 -> BB:BB:BB` in an in-memory **ARP Cache Table**.
   * Entries automatically expire after a timeout (typically 2 to 20 minutes) so if you get a new router, the address updates cleanly.

---

## 4. The Binary Structure of an ARP Packet (28 Bytes)

When an ARP packet travels inside an Ethernet frame (EtherType `0x0806`), its internal structure is:

| Field Name | Size | Value / Meaning |
| :--- | :---: | :--- |
| **Hardware Type** | 2 Bytes | `0x0001` (Ethernet) |
| **Protocol Type** | 2 Bytes | `0x0800` (IPv4) |
| **Hardware Size** | 1 Byte | `6` (Length of a MAC address in bytes) |
| **Protocol Size** | 1 Byte | `4` (Length of an IPv4 address in bytes) |
| **Opcode** | 2 Bytes | `1` for ARP Request, `2` for ARP Reply |
| **Sender MAC** | 6 Bytes | Physical hardware address of the sender |
| **Sender IP** | 4 Bytes | IPv4 address of the sender |
| **Target MAC** | 6 Bytes | Blank (`00:00:00...`) in request; filled in reply |
| **Target IP** | 4 Bytes | IPv4 address being searched for |

---

## 5. Security Threat: ARP Spoofing / Cache Poisoning

Because ARP was designed in 1982 when the internet was a trusting network of universities, **ARP has zero authentication**!
* An attacker on your public coffee shop Wi-Fi can send fake ARP replies:  
  *"Hey Laptop! I am IP 192.168.1.1 (the router)! My MAC is EVIL_MAC!"*
* If your laptop believes it, all your internet traffic (passwords, websites) flows directly through the hacker's laptop before reaching the router. This is called a **Man-in-the-Middle (MITM) attack**.
* **Defense**: Dynamic ARP Inspection (DAI) on managed switches, static ARP tables, and HTTPS/TLS encryption.

---

## 6. Complete Self-Contained Q&A

**Q1: At which OSI layer does ARP operate?**  
**Answer**: ARP operates between Layer 2 (Data Link) and Layer 3 (Network). It translates Layer 3 IP addresses into Layer 2 physical MAC addresses.

**Q2: What is the special MAC address used for ARP broadcast requests?**  
**Answer**: `FF:FF:FF:FF:FF:FF` (all 48 bits set to `1`).

**Q3: How do you view the active ARP cache on your computer right now?**  
**Answer**: Open any command prompt or terminal and run `arp -a`.

---

## 7. Hands-on Lab Verification

Run the simulated ARP resolution engine in `code/day-03/`:
```bash
python code/day-03/arp_cache_simulator.py
```
Observe how the first request requires an expensive network broadcast, while subsequent requests result in instant, local **Cache Hits**!
