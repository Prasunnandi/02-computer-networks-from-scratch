# Day 45: DHCP Snooping Architecture - Rogue Server Suppression, Binding Databases, and Layer 2 Security

## 1. Threat Modeling on Broadcast Domains: The Rogue DHCP Server

Ethernet local area networks are inherently trusting broadcast environments. Because a client emitting a `DHCPDISCOVER` broadcasts to `FF:FF:FF:FF:FF:FF`, **every single device** on that switch or VLAN receives the request. 

This architectural vulnerability exposes the network to two catastrophic security attacks:
1. **Rogue DHCP Server Attack**: A malicious actor (or accidentally misconfigured consumer router) runs a rogue DHCP daemon. It replies to client queries faster than the legitimate server, handing out a malicious Default Gateway (`Router`) and DNS server IP under the attacker's control, achieving **100% Man-In-The-Middle (MITM)** traffic interception.
### Rogue DHCP Attack Vector Analysis:
When an attacker deploys a rogue DHCP server on an untrusted port, they can manipulate the following options:
- **Default Router (Option 3)**: Pointing client traffic to the attacker's IP enables transparent interception and SSL stripping.
- **DNS Servers (Option 6)**: Pointing DNS queries to an attacker-controlled resolver allows arbitrary domain hijacking and credential phishing.
- **WPAD (Option 252)**: Web Proxy Auto-Discovery Protocol manipulation forces browsers to download malicious proxy auto-config (.pac) scripts.

2. **DHCP Starvation Attack**: An attacker uses tools like `yersinia` to blast hundreds of thousands of `DHCPDISCOVER` packets with randomized fake MAC addresses. The legitimate server allocates its entire IP pool to phantom addresses, resulting in complete **Denial-of-Service (DoS)** for valid clients.

```
+--------------------------------------------------------------------------+
|                     DHCP SNOOPING SECURITY BOUNDARY                      |
+--------------------------------------------------------------------------+
|  UNTRUSTED ACCESS PORTS (Client Facing)    TRUSTED UPLINK (Server Facing)|
|  - Switch blocks all DHCPOFFER & DHCPACK   - Switch permits all messages |
|  - Rate-limits DHCPDISCOVER (anti-DoS)     - Connected to real server    |
+--------------------------------------------------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                                                   |
          v (Port 1: Untrusted)                               v (Port 24: Trusted)
+-----------------------+                       +-----------------------+
|   ATTACKER / ROGUE    |                       |   LEGITIMATE SERVER   |
|   Emits fake DHCPOFFER|                       |   Emits real DHCPOFFER|
|   [DROPPED BY SWITCH] |                       |   [PASSED BY SWITCH]  |
+-----------------------+                       +-----------------------+
```

---

## 2. Kernel C Structs & Binary Bitfields: The DHCP Snooping Binding Database

To prevent rogue attacks, enterprise Layer 2 switches implement **DHCP Snooping**. The switch acts as an inline firewall inspecting Layer 2 Ethernet frames on UDP ports 67 and 68:
- **Port Classification**:
  - **Trusted Ports**: Ports connecting to legitimate DHCP servers or network uplinks. All DHCP packets (both requests and replies) are permitted.
  - **Untrusted Ports**: Ports connecting to end-user workstations. The switch **strictly drops any DHCP server response** (`DHCPOFFER`, `DHCPACK`, `DHCPNAK`) received on an untrusted port!
- **Dynamic Binding Database**:
  When a legitimate client completes a DORA handshake through a trusted port, the switch snoops the `DHCPACK` and builds a hardware binding entry in TCAM memory:

```c
/* Real Enterprise Switch TCAM Snooping Entry Representation */
struct dhcp_snoop_binding {
    uint8_t             mac_address[6]; /* Client MAC address (from chaddr) */
    struct in_addr      ip_address;     /* Leased IP address (from yiaddr) */
    uint32_t            lease_duration; /* Lease time in seconds */
    uint16_t            vlan_id;        /* Ingress VLAN */
    uint16_t            interface_idx;  /* Physical switch port (e.g. GigabitEthernet0/1) */
    uint32_t            timestamp;      /* Epoch timestamp when binding was forged */
};
```

---

## 3. Mathematical Foundations: The Triple Layer-2 Security Matrix

DHCP Snooping is not merely a standalone feature; it forms the mathematical trust anchor for two downstream Layer 2 security technologies:

$$\text{Zero Trust L2} = \text{DHCP Snooping} \implies \text{Dynamic ARP Inspection (DAI)} \implies \text{IP Source Guard (IPSG)}$$

### 1. Dynamic ARP Inspection (DAI):
Prevents ARP Poisoning. When any ARP packet arrives on an untrusted port, the switch evaluates:
$$\text{Permit}(\text{ARP}) \iff \langle \text{SenderMAC}, \text{SenderIP} \rangle \in \text{SnoopingDatabase}$$
If an attacker attempts to spoof the default gateway's IP, the switch drops the ARP frame in hardware.

### 2. IP Source Guard (IPSG):
Prevents IP address spoofing. The switch configures a dynamic hardware ACL on the ingress port:
$$\text{Permit}(L3) \iff \text{SrcIP} == \text{SnoopingDatabase}[\text{Port}].\text{IP} \quad \land \quad \text{SrcMAC} == \text{SnoopingDatabase}[\text{Port}].\text{MAC}$$
If an attacker attempts to transmit raw packets using a forged IP address, the switch ASIC drops the packets at line rate.

---

## 4. Compilable C Implementation: DHCP Snooping Switch Logic Engine

Save the following program as `dhcp_snooper.c`:

```c
/*
 * dhcp_snooper.c - Simulation of Enterprise Switch DHCP Snooping Validation Logic
 * Demonstrates:
 * 1. Port classification: TRUSTED vs UNTRUSTED
 * 2. Dropping rogue server replies on untrusted ports
 * 3. Building dynamic binding tables from snooped DHCPACKs
 *
 * Compilation:
 *   gcc -O2 -Wall -Wextra -pthread dhcp_snooper.c -o dhcp_snooper
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include <arpa/inet.h>

typedef enum {
    PORT_UNTRUSTED = 0,
    PORT_TRUSTED = 1
} PortTrust;

typedef struct {
    uint8_t mac[6];
    char ip[16];
    uint16_t vlan;
    int port;
} SnoopEntry;

static SnoopEntry g_database[16];
static int g_db_count = 0;

bool evaluate_dhcp_frame(int port, PortTrust trust, uint8_t dhcp_msg_type, const uint8_t *mac, const char *assigned_ip)
{
    /* Rule 1: Server response messages (OFFER=2, ACK=5, NAK=6) CANNOT arrive on untrusted ports! */
    if (trust == PORT_UNTRUSTED) {
        if (dhcp_msg_type == 2 || dhcp_msg_type == 5 || dhcp_msg_type == 6) {
            printf("[SECURITY ALERT] Rogue DHCP Server frame (Type %d) DROPPED on Untrusted Port %d!\n",
                   dhcp_msg_type, port);
            return false; /* Security Violation */
        }
    }

    /* Rule 2: Snooping genuine DHCPACK on trusted port to populate binding table */
    if (trust == PORT_TRUSTED && dhcp_msg_type == 5) {
        SnoopEntry *entry = &g_database[g_db_count++];
        memcpy(entry->mac, mac, 6);
        strncpy(entry->ip, assigned_ip, sizeof(entry->ip) - 1);
        entry->vlan = 10;
        entry->port = port;

        printf("[SNOOPING DB] Created Binding: MAC %02X:%02X:%02X:%02X:%02X:%02X -> IP %s (VLAN %d, Port %d)\n",
               mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], entry->ip, entry->vlan, entry->port);
    }

    return true; /* Frame allowed */
}

int main(void)
{
    printf("====================================================\n");
    printf("ENTERPRISE SWITCH DHCP SNOOPING ENGINE\n");
    printf("====================================================\n");

    uint8_t client_mac[6] = { 0x52, 0x54, 0x00, 0x11, 0x22, 0x33 };
    uint8_t rogue_mac[6]  = { 0x00, 0x50, 0x56, 0xDE, 0xAD, 0x01 };

    /* Scenario 1: Legitimate client broadcasts DHCPDISCOVER on Untrusted Port 2 */
    printf("1. Client sends DHCPDISCOVER on Untrusted Port 2:\n");
    bool ok1 = evaluate_dhcp_frame(2, PORT_UNTRUSTED, 1, client_mac, "0.0.0.0");
    printf("   Result: %s\n\n", ok1 ? "[PERMITTED]" : "[BLOCKED]");

    /* Scenario 2: Rogue hacker attempts to emit DHCPOFFER on Untrusted Port 2 */
    printf("2. Rogue server attempts DHCPOFFER on Untrusted Port 2:\n");
    bool ok2 = evaluate_dhcp_frame(2, PORT_UNTRUSTED, 2, rogue_mac, "192.168.1.100");
    printf("   Result: %s\n\n", ok2 ? "[PERMITTED]" : "[BLOCKED]");
    assert(ok2 == false);

    /* Scenario 3: Real corporate DHCP server emits DHCPACK on Trusted Uplink Port 24 */
    printf("3. Genuine Corporate Server emits DHCPACK on Trusted Port 24:\n");
    bool ok3 = evaluate_dhcp_frame(24, PORT_TRUSTED, 5, client_mac, "10.10.0.45");
    printf("   Result: %s\n\n", ok3 ? "[PERMITTED]" : "[BLOCKED]");
    assert(ok3 == true);

    printf("[VERIFIED] DHCP Snooping logic effectively thwarted rogue server injection!\n");
    return EXIT_SUCCESS;
}
```

---

## 5. Production War Story: The Database Sync Reboot Storm

In 2019, a corporate headquarters experienced network-wide failure after a power flicker. 

The campus network utilized Cisco Catalyst switches with DHCP Snooping, Dynamic ARP Inspection (DAI), and IP Source Guard (IPSG) configured. However, an architectural mistake was present: **the switches were not configured to persist the DHCP Snooping database to non-volatile flash or a remote TFTP server**.

When power was restored:
1. The switches rebooted with completely empty snooping binding databases.
2. The user workstations, however, remained suspended in memory or booted faster than the switches, retaining their existing DHCP leases.
3. When workstations attempted to send network traffic or resolve the gateway via ARP:
   - Dynamic ARP Inspection inspected the ARP packet.
   - The IP/MAC was missing from the empty snooping table.
   - The switches dropped 100% of all user packets (`%SW_DAI-4-DHCP_SNOOPING_DENY`)!
4. The entire campus network was paralyzed until network engineers manually configured:
   ```cisco
   ip dhcp snooping database flash:snooping-db.bin
   ```
   and forced all workstations to release and renew their leases via group policy.

---

## 6. Verification & CLI Mastery Reference

| Command | Action | Deep Technical Purpose |
| :--- | :--- | :--- |
| `show ip dhcp snooping` | Status Verification | Audits enabled VLANs and lists trusted vs untrusted interfaces. |
| `show ip dhcp snooping binding` | Binding Table | Dumps active TCAM table mapping MAC $\to$ IP $\to$ Lease $\to$ Interface. |
| `ip dhcp snooping limit rate 100` | Rate Limiting | Sets maximum allowed DHCP packets per second to defeat starvation attacks. |
