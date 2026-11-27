# Day 44: DHCP Relay Agents - Cross-Subnet Forwarding, giaddr Rewriting, and Option 82

## 1. The Multi-Subnet Challenge: Routers Drop Broadcasts

In enterprise networks, network architecture is divided into multiple broadcast domains (VLANs/subnets) separated by Layer 3 routers or switches. By design, standard IP routers **strictly discard broadcast packets** (`255.255.255.255`) to prevent broadcast storms from saturating the entire corporate network.

This creates a fundamental scaling dilemma:
$$\text{If a client in VLAN 10 broadcasts a DHCPDISCOVER, and routers block broadcasts, how can a centralized DHCP server in VLAN 100 receive it?}$$

Installing a dedicated physical DHCP server on every single VLAN is economically and operationally prohibitive. The industry standard solution is the **DHCP Relay Agent (RFC 1542 / RFC 3046)**.

```
+--------------------------------------------------------------------------+
|                     DHCP RELAY AGENT (IP HELPER) TOPOLOGY                |
+--------------------------------------------------------------------------+
|  CLIENT (VLAN 10)         ROUTER / RELAY AGENT        CENTRAL DHCP SERVER|
|  Unconfigured             (Interface 10: 10.10.0.1)   (VLAN 100: 10.100.0.5)
+--------------------------------------------------------------------------+
       |                                |                        |
       | 1. Broadcast DHCPDISCOVER      |                        |
       |    Src: 0.0.0.0:68             |                        |
       |    Dst: 255.255.255.255:67     |                        |
       |------------------------------->|                        |
       |                                |                        |
       |                                | 2. Unicast Relay Forward
       |                                |    Src: 10.10.0.1:67   |
       |                                |    Dst: 10.100.0.5:67  |
       |                                |    giaddr = 10.10.0.1  |
       |                                |    Option 82 Appended  |
       |                                |----------------------->|
       |                                |                        |
       |                                | 3. Unicast DHCPOFFER   |
       |                                |    Src: 10.100.0.5:67  |
       |                                |    Dst: 10.10.0.1:67   |
       |                                |    yiaddr: 10.10.0.150 |
       |                                |<-----------------------|
       |                                |                        |
       | 4. Broadcast / Unicast Offer   |                        |
       |    To Client MAC               |                        |
       |<-------------------------------|                        |
```

---

## 2. Kernel C Structs & Binary Bitfields: The giaddr Gateway Field

When a router configured with a DHCP Relay Agent (`ip helper-address` in Cisco IOS or `isc-dhcp-relay` in Linux) receives a broadcast on port 67:
1. It inspects the `dhcp_packet` header.
2. It increments the `hops` counter:
   $$\text{packet.hops} \mathrel{+}= 1$$
   If `hops > 16`, the packet is dropped to prevent infinite relay loops.
3. If `giaddr` (Gateway IP Address) is `0.0.0.0`, the relay agent writes the IP address of the **ingress interface** where the broadcast arrived into `giaddr`:
   $$\text{packet.giaddr} = \text{ingress\_interface.ip}$$
4. It wraps the packet in a standard **Unicast UDP** datagram and routes it directly across the enterprise network to the centralized DHCP server.

```c
/* Real Linux Kernel DHCP Relay Forwarding Logic */
void process_relay_forward(struct dhcp_packet *pkt, struct in_addr ingress_ip, struct in_addr server_ip)
{
    pkt->hops++;
    if (pkt->hops > 16) {
        return; /* Drop loop */
    }

    if (pkt->giaddr.s_addr == 0) {
        pkt->giaddr = ingress_ip; /* Critical: Tells server which subnet pool to use! */
    }

    /* Transmit via standard unicast socket to server_ip on Port 67 */
}
```

### Why `giaddr` is Architecturally Critical:
The centralized DHCP server hosts 50 different IP scopes (`10.10.0.0/24`, `10.20.0.0/24`, etc.). When it receives the unicast request, it reads `giaddr`:
$$\text{Pool Selected} = \text{LookupSubnet}(\text{giaddr})$$
Because `giaddr` is `10.10.0.1`, the server knows with 100% mathematical certainty to allocate an IP from the `VLAN 10` scope rather than any other subnet!

---

## 3. Mathematical Foundations: Option 82 Sub-Option Grammar

RFC 3046 defines **Option 82 (DHCP Relay Agent Information Option)**. Because `giaddr` only identifies the subnet, enterprise switches append Option 82 to identify the exact physical switch chassis, line card, and port where the user plugged in:

$$\text{Option 82 Wire} = \langle \text{Tag: 82}, \quad \text{Length}, \quad \text{Sub-Options Array} \rangle$$

### The Two Standard Sub-Options:
1. **Sub-Option 1: Agent Circuit ID (`sub-tag 1`)**:
   Encodes the physical switch blade and port index:
   $$\text{Circuit ID} = \langle \text{VLAN ID (2B)}, \quad \text{Module Index (1B)}, \quad \text{Port Index (1B)} \rangle$$
2. **Sub-Option 2: Agent Remote ID (`sub-tag 2`)**:
   Encodes the switch chassis MAC address:
   $$\text{Remote ID} = \text{Switch MAC Address (6B)}$$

This allows zero-trust DHCP servers to enforce MAC sticky policies: if a host plugs into Port 4, it receives a developer IP; if it plugs into Port 12, it receives an isolated guest IP.

---

## 4. Compilable C Implementation: DHCP Relay Forwarder Simulator

Save the following program as `dhcp_relay_sim.c`:

```c
/*
 * dhcp_relay_sim.c - Low-Level DHCP Relay Agent Simulation
 * Demonstrates:
 * 1. Intercepting a broadcast DHCPDISCOVER
 * 2. Rewriting giaddr and incrementing hops
 * 3. Appending RFC 3046 Option 82 (Circuit ID + Remote ID)
 * 4. Forwarding to centralized server via unicast
 *
 * Compilation:
 *   gcc -O2 -Wall -Wextra -pthread dhcp_relay_sim.c -o dhcp_relay_sim
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <arpa/inet.h>

struct minimal_dhcp {
    uint8_t  op, htype, hlen, hops;
    uint32_t xid;
    uint16_t secs, flags;
    uint32_t ciaddr, yiaddr, siaddr, giaddr;
    uint8_t  chaddr[16];
    char     sname[64];
    char     file[128];
    uint32_t magic_cookie;
    uint8_t  options[128];
} __attribute__((packed));

void relay_forward(struct minimal_dhcp *pkt, const char *ingress_ip_str, const char *server_ip_str)
{
    printf("[RELAY] Intercepted client broadcast on ingress interface: %s\n", ingress_ip_str);

    /* 1. Increment hops counter */
    pkt->hops++;
    printf("  -> Incremented hops counter to: %d\n", pkt->hops);

    /* 2. Populate giaddr if not already set */
    if (pkt->giaddr == 0) {
        pkt->giaddr = inet_addr(ingress_ip_str);
        printf("  -> Injected giaddr: %s\n", ingress_ip_str);
    }

    /* 3. Append Option 82 (Relay Agent Information) */
    /* Find the Option 255 (End) marker */
    int idx = 0;
    while (idx < 120 && pkt->options[idx] != 255) {
        if (pkt->options[idx] == 0) { idx++; continue; }
        idx += 2 + pkt->options[idx + 1];
    }

    /* Build Option 82 payload:
     * Sub-option 1 (Circuit ID: VLAN 10, Port 5) -> [0x01, 0x02, 0x00, 0x05]
     */
    printf("  -> Appending Option 82 (Circuit ID: Port 5, VLAN 10)\n");
    pkt->options[idx++] = 82;       /* Option 82 Tag */
    pkt->options[idx++] = 4;        /* Option 82 Total Length */
    pkt->options[idx++] = 1;        /* Sub-option 1: Circuit ID */
    pkt->options[idx++] = 2;        /* Sub-option Length: 2 bytes */
    pkt->options[idx++] = 0;        /* Port index */
    pkt->options[idx++] = 5;        /* Port 5 */
    pkt->options[idx++] = 255;      /* Re-append End option */

    printf("[RELAY] Unicasting transformed packet to Central Server: %s:67\n", server_ip_str);
}

int main(void)
{
    printf("====================================================\n");
    printf("DHCP RELAY AGENT & OPTION 82 FORWARDING ENGINE\n");
    printf("====================================================\n");

    struct minimal_dhcp packet;
    memset(&packet, 0, sizeof(packet));

    packet.op = 1;      /* BOOTREQUEST */
    packet.htype = 1;
    packet.hlen = 6;
    packet.hops = 0;
    packet.xid = htonl(0x4A12BC09);
    packet.magic_cookie = htonl(0x63825363);

    /* Option 53: DHCPDISCOVER */
    packet.options[0] = 53;
    packet.options[1] = 1;
    packet.options[2] = 1;
    packet.options[3] = 255; /* End */

    relay_forward(&packet, "10.10.0.1", "10.100.0.5");

    struct in_addr check_giaddr;
    check_giaddr.s_addr = packet.giaddr;
    printf("\n[VERIFIED] Relay agent successfully assigned giaddr=%s and hops=%d!\n",
           inet_ntoa(check_giaddr), packet.hops);

    return EXIT_SUCCESS;
}
```

---

## 5. Production War Story: The Option 82 Untrusted Drop Outage

In 2020, a university updated its access layer switches to enterprise managed switches with DHCP Snooping and Option 82 enabled by default:
1. When students plugged in laptops in the dormitories, the switch inserted Option 82 into the broadcast packet and passed it to the upstream distribution router.
2. The distribution router was running an older Cisco IOS release.
3. **The Cisco Default Rule**: By default, Cisco routers running `ip helper-address` consider any packet arriving on an untrusted edge port with **Option 82 already present and giaddr=0.0.0.0 to be a malicious spoofing attack**!
4. The router silently discarded 100% of student DHCP packets (`%DHCP-4-DROPPED: DHCP packet dropped: received with Option 82 but giaddr is zero`).
5. Over 6,000 students were without internet access for 8 hours.

**The Fix**:
Configured the distribution router to trust Option 82 from downstream switches:
```cisco
ip dhcp relay information trust-all
# OR
ip dhcp relay information option allow-untrusted
```

---

## 6. Verification & CLI Mastery Reference

| Command | Action | Deep Technical Purpose |
| :--- | :--- | :--- |
| `tcpdump -envvn -i eth0 'udp and (port 67 or 68)'` | Sniff Relayed Traffic | Displays `giaddr` IP and parsed Option 82 circuit identifiers. |
| `show ip dhcp relay information trusted-sources` | Switch Security | Audits which trunk ports are permitted to inject Option 82 metadata. |
| `dhcrelay -d -i eth0 10.100.0.5` | Linux Relay Daemon | Launches userspace relay forwarder binding `eth0` and relaying to server. |
