# Day 03: The Address Resolution Protocol (ARP): RFC 826, Kernel Neighbor Caches & Gratuitous Failover

> **Zero External Dependency Guarantee**: This document is an encyclopedic, self-contained masterclass. It contains complete historical origins, RFC 826 28-byte packet binary layouts, Linux kernel neighbor cache state machines (`net/ipv4/arp.c`), Gratuitous ARP failover physics, ARP poisoning attacks, production split-brain post-mortems, and FAANG staff-level interview questions. You do NOT need any textbook or external website.

---

## 1. Executive Summary & Historical Origins

In 1982, David C. Plummer published **RFC 826**, introducing the **Address Resolution Protocol (ARP)**. In computer networking, Layer 3 (Internet Protocol) operates on logical IP addresses (e.g., `192.168.1.50`), which define where a host lives globally in the network topology. However, Layer 2 (Ethernet) operates exclusively on physical MAC addresses (e.g., `00:1A:2B:3C:4D:5E`), which identify the physical network interface hardware on a local link.

When Host A wants to transmit an IP packet to Host B on the same local subnet, Host A's operating system faces a critical question:
$$\mathbf{"What\ physical\ Layer\ 2\ MAC\ address\ corresponds\ to\ target\ IP\ address\ 192.168.1.50?"}$$

ARP is the glue protocol that dynamically resolves logical Layer 3 IPv4 addresses into physical Layer 2 MAC addresses.

```
THE ADDRESS RESOLUTION PROTOCOL (ARP) WORKFLOW:
Host A (192.168.1.10) wants to send packet to 192.168.1.50:
  |
  +---> 1. ARP REQUEST (Broadcast: FF:FF:FF:FF:FF:FF)
  |        "Who has IP 192.168.1.50? Tell 192.168.1.10!"
  |        (Received by ALL stations on the local Ethernet switch)
  |
  +<--- 2. ARP REPLY (Unicast: Directly to Host A)
           Host B (192.168.1.50) replies:
           "I have 192.168.1.50! My MAC is 00:1A:2B:3C:4D:5E!"
```

---

## 2. Binary Anatomy of the RFC 826 ARP Packet (28 Bytes)

An ARP packet is encapsulated directly inside an Ethernet frame with EtherType **`0x0806`**.

```
RFC 826 ARP PACKET BINARY LAYOUT:
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       Hardware Type (HTYPE)   |       Protocol Type (PTYPE)   |  (e.g., 1 = Ethernet, 0x0800 = IPv4)
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  HLEN = 6     |  PLEN = 4     |          Operation (OP)       |  (1 = Request, 2 = Reply)
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Sender Hardware Address (SHA: Bytes 0-3)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  SHA (Bytes 4-5)              |  Sender Protocol Addr (SPA:0-1)|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  SPA (Bytes 2-3)              |  Target Hardware Address (THA) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Target Hardware Address (THA: Bytes 2-5)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                  Target Protocol Address (TPA: Bytes 0-3)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 2.1 Field Breakdown:
1. **Hardware Type (`HTYPE`, 16 bits)**: The Layer 2 architecture. Always `1` for Ethernet.
2. **Protocol Type (`PTYPE`, 16 bits)**: The Layer 3 architecture being resolved. Always `0x0800` for IPv4.
3. **Hardware Address Length (`HLEN`, 8 bits)**: Length of Layer 2 address in bytes. For MAC addresses, `6`.
4. **Protocol Address Length (`PLEN`, 8 bits)**: Length of Layer 3 address in bytes. For IPv4, `4`.
5. **Operation Code (`OP`, 16 bits)**:
   - `1`: ARP Request (Broadcast query)
   - `2`: ARP Reply (Unicast answer)
6. **Sender Hardware Address (`SHA`, 6 bytes)**: MAC address of the host generating the ARP message.
7. **Sender Protocol Address (`SPA`, 4 bytes)**: IPv4 address of the generating host.
8. **Target Hardware Address (`THA`, 6 bytes)**: In an ARP Request, this field is ignored (set to `00:00:00:00:00:00`). In an ARP Reply, contains recipient MAC.
9. **Target Protocol Address (`TPA`, 4 bytes)**: IPv4 address being resolved.

---

## 3. The Linux Kernel Neighbor Table State Machine (`net/ipv4/arp.c`)

The Linux kernel does not issue an ARP broadcast for every outgoing packet. That would saturate the network with broadcast noise. Instead, it caches IP-to-MAC mappings in physical RAM in the **Neighbor Table** (`ip neigh`).

```
LINUX NEIGHBOR CACHE (NUD - NEIGHBOUR UNCONFIRMED DETECTION) STATES:

          +------------------+
          |  NUD_INCOMPLETE  | <--- Packet queued; ARP Request transmitted
          +------------------+
                   | ARP Reply received
                   v
          +------------------+
          |  NUD_REACHABLE   | <--- Positive confirmation (valid for base_reachable_time, ~30s)
          +------------------+
                   | Timer expires
                   v
          +------------------+
          |    NUD_STALE     | <--- Entry valid, but needs verification before active use
          +------------------+
                   | Outgoing packet arrives
                   v
          +------------------+
          |    NUD_DELAY     | <--- Waits 5 seconds for Layer 4 ACK (TCP) confirmation
          +------------------+
                   | No L4 ACK received
                   v
          +------------------+
          |    NUD_PROBE     | <--- Sends direct unicast ARP probes
          +------------------+
                   | Max retries exceeded without reply
                   v
          +------------------+
          |    NUD_FAILED    | ---> Entry deleted from kernel table!
          +------------------+
```

---

## 4. Gratuitous ARP: IP Conflict Detection & High Availability Failover

A **Gratuitous ARP (GARP)** is an unsolicited ARP broadcast where a host announces its own IP and MAC address:
$$\text{Sender IP} = \text{Target IP} \quad \text{and} \quad \text{Destination MAC} = \texttt{FF:FF:FF:FF:FF:FF}$$

### 4.1 The Two Critical Use Cases:
1. **IP Address Conflict Detection (ACD)**:
   When an interface boots up, it broadcasts a GARP. If another host replies, the kernel detects an IP conflict, logs an error, and refuses to bind the duplicate IP.
2. **Virtual IP (VIP) High-Availability Failover (Keepalived, VRRP, CARP)**:
   - In a database cluster, Master Node A owns VIP `10.0.0.100` with MAC `00:AA:AA...`.
   - Node A crashes! Backup Node B takes over VIP `10.0.0.100` with MAC `00:BB:BB...`.
   - Node B immediately broadcasts a **Gratuitous ARP**!
   - Every switch on the local network instantly updates its CAM table, redirecting all incoming packets to Node B within milliseconds!

---

## 5. Security Vulnerabilities: ARP Cache Poisoning (Man-in-the-Middle)

RFC 826 was designed in 1982 when all ARPANET university participants trusted each other. **ARP has zero cryptographic authentication!**

```
ARP POISONING (MITM) ATTACK:
Attacker sends spoofed ARP Replies to both Victim and Gateway:
  To Victim:  "192.168.1.1 (Gateway) is at MAC: ATTACKER_MAC"
  To Gateway: "192.168.1.50 (Victim) is at MAC: ATTACKER_MAC"

Result:
[ Victim ] <====== (All Traffic) ======> [ Attacker ] <====== (All Traffic) ======> [ Gateway ]
                                         (Sniffs passwords,
                                          alters data packets)
```

### 5.1 Enterprise Mitigations:
* **Dynamic ARP Inspection (DAI)**: Managed switches inspect ARP packets against a trusted DHCP Snooping binding database. Any ARP reply claiming an IP not assigned by DHCP is dropped at the switch ASIC!
* **Static ARP Mappings**: On critical servers: `arp -s 192.168.1.1 00:11:22:33:44:55`.

---

## 6. Real-World Production War Stories

### 6.1 War Story 1: The VRRP Split-Brain Flapping Storm
* **The Incident**: In a major banking payment gateway, the active/standby database pair experienced an intermittent heartbeat network cable fault.
* **The Catastrophe**:
  - Both nodes assumed the other was dead. Both declared themselves "Master" (Split-Brain).
  - Node A sent a Gratuitous ARP for VIP `10.0.0.1`: "I am 10.0.0.1 (MAC A)!"
  - 100 milliseconds later, Node B sent a Gratuitous ARP: "No, I am 10.0.0.1 (MAC B)!"
  - Core switches flapped CAM table entries 500 times per second, dropping 95% of customer payment transactions!
* **The SRE Fix**: Enforced dual-channel redundant heartbeats (Ethernet + Serial/Dedicated Link) and STONITH (Shoot The Other Node In The Head) fencing.

---

## 7. Staff-Level Technical Interview Deep-Dives

### Question 1: What is the "ARP Flux" problem in multi-homed Linux servers?
**Exhaustive Answer**:
* By default, the Linux kernel operates under the **Weak Host Model**. It considers IP addresses to belong to the entire host machine, not to specific network interfaces!
* If a server has two network cards: `eth0` (`192.168.1.10`) and `eth1` (`192.168.1.11`) on the same subnet:
  - If an ARP request arrives on `eth0` asking for `192.168.1.11`, Linux may reply with the MAC address of `eth0`!
  - This causes incoming traffic to arrive on the wrong physical interface, breaking asymmetric routing and firewalls.
* **The Fix**: Configure `/proc/sys/net/ipv4/conf/all/arp_ignore = 1` and `arp_announce = 2` to force the kernel to reply only on the interface that owns the target IP.

---

## 8. Complete Verification Checklist (Zero Gaps)
- [ ] Draw the 9 fields of an RFC 826 ARP packet and specify their bit widths.
- [ ] Diagram the 6 states of the Linux Neighbor cache (`INCOMPLETE` to `FAILED`).
- [ ] How does Gratuitous ARP enable instant IP failover in Keepalived/VRRP clusters?
- [ ] What is an ARP cache poisoning attack and how does Dynamic ARP Inspection (DAI) prevent it?
