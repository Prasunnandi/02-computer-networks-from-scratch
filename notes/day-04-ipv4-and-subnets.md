# 🔢 Day 4: IPv4 Addressing, CIDR Notation & Subnet Masks

> **Zero External Dependency Rule**: Everything you need to master this topic is contained right here in this document. You do NOT need to visit any external website or search Google.

---

## 1. The Core Problem: Why MAC Addresses Cannot Scale to the Global Internet

On Day 2 and Day 3, we learned that local network devices communicate using 48-bit **MAC Addresses**.
Why can't we use MAC addresses to run the entire global internet?

* **MAC addresses have no geography or structure**: A MAC address is a random serial number burned into a chip. A laptop manufactured in China might be shipped to California, and then carried to Paris.
* If internet routers used MAC addresses, every single router on planet Earth would need a database table containing all **20 billion connected devices**! Looking up where to send a packet would take minutes.

To solve this, in 1981, Jon Postel designed the **Internet Protocol (IPv4 - RFC 791)**.
An IP address is a **hierarchical logical address**—just like a postal mail address!

---

## 2. Real-World Analogy: The Postal Street Address

When you send a letter across the world, postal trucks don't search for individual names; they read the address hierarchically from biggest area to smallest:

```
        COUNTRY ──────► STATE ──────► CITY ──────► STREET ──────► HOUSE #
```

An **IPv4 Address** does the exact same thing by splitting its 32 bits into **TWO parts**:

```
               192 . 168 . 1 . 45
                │          │
                ▼          ▼
       [ NETWORK PORTION ]  [ HOST / DEVICE NUMBER ]
       (The Neighborhood)    (Your Specific Laptop)
```

* **Network Portion (Neighborhood)**: Identifies which company, university, or ISP owns this network block. Routers across the world only look at this part to forward packets!
* **Host Portion (Door Number)**: Identifies the specific device inside that local network.

---

## 3. The Anatomy of an IPv4 Address

* An IPv4 address is made of **32 binary bits** (4 bytes).
* For humans, we divide the 32 bits into **4 chunks of 8 bits** (called **Octets**), separated by dots. This is called **Dotted Decimal Notation**:

```
Binary:  11000000 . 10101000 . 00000001 . 00101101
          │          │          │          │
Decimal: 192    .   168    .    1     .    45
```

### Why No Number in an IP Address Can Exceed 255:
Because each octet is strictly **8 bits** ($1\text{ Byte}$):
* Smallest value: `00000000` = **`0`**
* Largest value: `11111111` = $2^7 + 2^6 + 2^5 + 2^4 + 2^3 + 2^2 + 2^1 + 2^0$ = **`255`**!
* Any address with numbers above 255 (e.g. `270.1.2.3`) is completely invalid and impossible.

---

## 4. What is a Subnet Mask & What Does `/24` Mean?

If an IP address is just a string of 32 bits, how does your computer know where the **Network Portion** ends and the **Host Portion** begins?

It uses a **Subnet Mask**!

A Subnet Mask is a continuous string of **`1`s followed by a continuous string of `0`s**:
* The **`1`s** mask out the **Network (Neighborhood)**.
* The **`0`s** identify the **Host (Device)**.

### CIDR (Classless Inter-Domain Routing) Notation:
Writing `255.255.255.0` is tedious. Instead, engineers write **slash notation** indicating the count of `1` bits:

$$\mathbf{192.168.1.45 / 24}$$

The **`/24`** means: **"The first 24 bits are all `1`s (the network). The remaining $32 - 24 = 8$ bits are `0`s (the devices)!"**

```
IP Address:   11000000.10101000.00000001 . 00101101  (192.168.1.45)
Subnet Mask:  11111111.11111111.11111111 . 00000000  (255.255.255.0 = /24)
              └───────── 24 bits ────────┘   └── 8 bits ──┘
                    NETWORK PORTION             HOST PORTION
```

---

## 5. The Golden Subnet Formulas (Mastering the Math)

Whenever you are given any CIDR prefix (e.g. `/24`, `/26`, `/16`), use these **3 golden formulas**:

### Formula 1: Number of Host Bits ($H$)
$$H = 32 - \text{Prefix}$$
* For `/24`: $H = 32 - 24 = 8\text{ host bits}$.
* For `/26`: $H = 32 - 26 = 6\text{ host bits}$.

### Formula 2: Total IP Addresses ($T$)
$$T = 2^H$$
* For `/24`: $2^8 = 256\text{ total addresses}$.
* For `/26`: $2^6 = 64\text{ total addresses}$.

### Formula 3: Usable Device Addresses ($U$)
$$U = 2^H - 2$$
Why do we always subtract **2**? Because in every single network, **two addresses are strictly reserved by law**:
1. **The First Address (All host bits = `0`) $\rightarrow$ Network Address**: Used to identify the entire network block.
2. **The Last Address (All host bits = `1`) $\rightarrow$ Broadcast Address**: Used to send a packet to every device on that subnet simultaneously.

```
For Subnet 192.168.1.0/24:
├── 192.168.1.0   : RESERVED (Network ID)
├── 192.168.1.1   : First Usable Computer / Device
├── ...           : (254 Usable Computers)
├── 192.168.1.254 : Last Usable Computer / Device
└── 192.168.1.255 : RESERVED (Broadcast to all)
```

---

## 6. Complete Self-Contained Q&A

**Q1: How many total IPv4 addresses exist in the world?**  
**Answer**: $2^{32} = \mathbf{4,294,967,296}$ (roughly 4.3 billion addresses). Because there are now over 8 billion humans and tens of billions of mobile phones and IoT devices, the world officially ran out of unassigned IPv4 addresses in 2011, prompting the creation of IPv6 ($2^{128}$ addresses) and NAT!

**Q2: If an office network uses `/28`, how many usable laptops and servers can be connected?**  
**Answer**:
* Host bits: $32 - 28 = 4\text{ bits}$.
* Total addresses: $2^4 = 16$.
* Usable devices: $16 - 2 = \mathbf{14\text{ usable devices}}$.

**Q3: How does a computer determine its Network Address from its IP and Subnet Mask?**  
**Answer**: It performs a hardware-level **Bitwise AND operation** between its 32-bit IP and its 32-bit Subnet Mask. Since $X \text{ AND } 1 = X$ and $X \text{ AND } 0 = 0$, all host bits are turned to zero, leaving only the Network Address!

---

## 7. Hands-on Lab Verification

Run the Bitwise Subnet Calculator in `code/day-04/`:
```bash
python code/day-04/subnet_calculator.py
```
Observe how the bitwise AND logic calculates the exact Network ID, Broadcast ID, and usable host limits for `/24`, `/16`, and `/26` subnets!
