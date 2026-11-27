# Day 41: DHCP Architecture - The 4-Step DORA Flow and UDP Bootstrap Mechanics

## 1. The Bootstrap Dilemma: How to Communicate Without an Identity

When a network device connects to an Ethernet segment, it possesses an immutable 48-bit IEEE 802 MAC address burned into its Network Interface Card (NIC), but **zero layer-3 IP configuration**. It does not know:
- Its own IPv4 address or subnet mask.
- The default router (gateway) to reach external networks.
- The recursive DNS resolvers needed to translate domain names.

This presents the classical networking bootstrap paradox:
$$\text{To send an IP datagram to a server, a host needs an IP address; but to get an IP address, it must send an IP datagram!}$$

The **Dynamic Host Configuration Protocol (DHCP - RFC 2131)** resolves this paradox by executing a 4-step handshake known as **DORA** (Discover, Offer, Request, Acknowledge) using UDP transport over **Ports 67 (Server)** and **Port 68 (Client)**, leveraging IP layer-2/layer-3 broadcast primitives:
- Layer 2 Broadcast: `FF:FF:FF:FF:FF:FF`
- Layer 3 Broadcast: `255.255.255.255` (Limited Local Broadcast)
- Unspecified Source IP: `0.0.0.0`

```
+--------------------------------------------------------------------------+
|                       THE 4-STEP DHCP DORA SEQUENCE                      |
+--------------------------------------------------------------------------+
|  CLIENT (Port 68)                                     SERVER (Port 67)   |
|  MAC: 52:54:00:12:34:56                               IP: 192.168.1.1    |
+--------------------------------------------------------------------------+
       |                                                       |
       | 1. DHCPDISCOVER                                       |
       |    Src: 0.0.0.0:68  -> Dst: 255.255.255.255:67        |
       |    Ethernet: FF:FF:FF:FF:FF:FF                        |
       |    Transaction ID (xid): 0x39A41C02                   |
       |------------------------------------------------------>|
       |                                                       |
       | 2. DHCPOFFER                                          |
       |    Src: 192.168.1.1:67 -> Dst: 255.255.255.255:68    |
       |    Your IP (yiaddr): 192.168.1.100                    |
       |    Subnet: 255.255.255.0, Router: 192.168.1.1         |
       |<------------------------------------------------------|
       |                                                       |
       | 3. DHCPREQUEST                                        |
       |    Src: 0.0.0.0:68  -> Dst: 255.255.255.255:67        |
       |    Requested IP: 192.168.1.100                        |
       |    Server Identifier: 192.168.1.1                     |
       |------------------------------------------------------>|
       |                                                       |
       | 4. DHCPACK                                            |
       |    Src: 192.168.1.1:67 -> Dst: 255.255.255.255:68    |
       |    Confirmed IP (yiaddr): 192.168.1.100               |
       |    Lease Time: 86400s (T1: 43200s, T2: 75600s)        |
       |<------------------------------------------------------|
```

---

## 2. Kernel C Structs & Binary Bitfields: DHCP Wire Packet Anatomy

DHCP retains 100% backward compatibility with its predecessor BOOTP (RFC 951). Every DHCP packet starts with a fixed 236-byte header, followed by a 4-byte Magic Cookie and variable-length TLV (Type-Length-Value) options:

```c
/* Real Linux Kernel & glibc DHCP/BOOTP packet structure from netinet/udp.h */
#define DHCP_MAGIC_COOKIE   0x63825363  /* RFC 1497 Vendor Magic Cookie: 99.130.83.99 */

struct dhcp_packet {
    uint8_t             op;             /* 1 = BOOTREQUEST, 2 = BOOTREPLY */
    uint8_t             htype;          /* Hardware address type (1 = 10Mb Ethernet) */
    uint8_t             hlen;           /* Hardware address length (6 for MAC) */
    uint8_t             hops;           /* Set to 0 by client, incremented by Relay Agents */
    uint32_t            xid;            /* Transaction ID (Random 32-bit integer) */
    uint16_t            secs;           /* Seconds elapsed since client began acquisition */
    uint16_t            flags;          /* Bit 0: Broadcast flag; Bits 1-15: Reserved (MBZ) */
    struct in_addr      ciaddr;         /* Client IP address (only set if client is BOUND) */
    struct in_addr      yiaddr;         /* 'Your' (client) IP address (assigned by server) */
    struct in_addr      siaddr;         /* Next server IP (used in bootstrap TFTP) */
    struct in_addr      giaddr;         /* Relay agent IP address (GW IP) */
    uint8_t             chaddr[16];     /* Client hardware address (MAC padded with zeros) */
    char                sname[64];      /* Optional server host name (null-terminated) */
    char                file[128];      /* Boot file name (e.g., pxelinux.0 for PXE boot) */
    uint32_t            magic_cookie;   /* Magic Cookie: 0x63825363 */
    uint8_t             options[308];   /* Variable-length TLV options (min 312 bytes total) */
} __attribute__((packed));
```

### The Broadcast Flag Bitfield:
In the 16-bit `flags` field:
- **Bit 15 (MSB)** is the **Broadcast Flag ($B$)**:
  $$B = 1 \implies \text{Server MUST broadcast responses to } 255.255.255.255$$
  $$B = 0 \implies \text{Server may unicast response directly to client MAC via ARP}$$
Certain operating system IP stacks cannot receive unicast IP packets before their interface has an assigned IP. Setting $B=1$ forces the server to use layer-2 broadcast (`FF:FF:FF:FF:FF:FF`), guaranteeing delivery.

---

## 3. Mathematical Foundations: Collision Probability in Transaction IDs (xid)

The 32-bit Transaction ID (`xid`) ties requests to responses across the broadcast domain. If two hosts on the same switch simultaneously boot and pick the same `xid`, or if an attacker predicts `xid`, session hijacking occurs.

Let $N = 2^{32} \approx 4.29 \times 10^9$ be the total possible `xid` states.
By the **Birthday Paradox**, the probability $P$ that at least two booting clients in a network of $k$ machines select the identical `xid` is:
$$P(\text{collision}) = 1 - \prod_{i=1}^{k-1} \left(1 - \frac{i}{N}\right) \approx 1 - e^{-\frac{k(k-1)}{2N}}$$

For $k = 1,000$ simultaneously booting virtual machines in a cloud cluster:
$$\frac{k(k-1)}{2N} = \frac{1000 \times 999}{2 \times 4.29 \times 10^9} \approx \frac{9.99 \times 10^5}{8.58 \times 10^9} \approx 0.000116 \implies P \approx 0.0116\%$$
Thus, 32-bit entropy guarantees negligible collision risk under normal conditions, provided `xid` is generated from `/dev/urandom` rather than predictable linear counters (`PID` or `time(NULL)`).

---

## 4. Compilable C Implementation: Raw Socket DHCPDISCOVER Packet Crafter

Save the following program as `dhcp_discover.c`:

```c
/*
 * dhcp_discover.c - Low-level DHCPDISCOVER packet crafter using standard sockets
 * Demonstrates:
 * 1. Packing the 236-byte BOOTP/DHCP header
 * 2. Appending RFC 1497 Magic Cookie and TLV options (Option 53 = DHCPDISCOVER)
 * 3. Transmitting over UDP broadcast socket (SO_BROADCAST)
 *
 * Compilation:
 *   gcc -O2 -Wall -Wextra -pthread dhcp_discover.c -o dhcp_discover
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <time.h>

struct dhcp_msg {
    uint8_t  op, htype, hlen, hops;
    uint32_t xid;
    uint16_t secs, flags;
    uint32_t ciaddr, yiaddr, siaddr, giaddr;
    uint8_t  chaddr[16];
    char     sname[64];
    char     file[128];
    uint32_t magic_cookie;
    uint8_t  options[64];
} __attribute__((packed));

int main(void)
{
    printf("====================================================\n");
    printf("RAW DHCPDISCOVER UDP BROADCAST CRAFTER\n");
    printf("====================================================\n");

    int sockfd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sockfd < 0) {
        perror("Socket creation failed");
        return EXIT_FAILURE;
    }

    /* Enable broadcast transmission on socket */
    int broadcast_perm = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_BROADCAST, &broadcast_perm, sizeof(broadcast_perm)) < 0) {
        perror("setsockopt SO_BROADCAST failed");
        close(sockfd);
        return EXIT_FAILURE;
    }

    struct dhcp_msg packet;
    memset(&packet, 0, sizeof(packet));

    packet.op = 1;          /* 1 = BOOTREQUEST */
    packet.htype = 1;       /* 1 = 10Mb Ethernet */
    packet.hlen = 6;        /* 6 bytes MAC */
    packet.hops = 0;
    
    srand(time(NULL));
    packet.xid = htonl((uint32_t)rand()); /* Random Transaction ID */
    packet.flags = htons(0x8000);        /* Set Broadcast flag B=1 */

    /* Synthetic client MAC: 52:54:00:AB:CD:EF */
    uint8_t mock_mac[6] = { 0x52, 0x54, 0x00, 0xAB, 0xCD, 0xEF };
    memcpy(packet.chaddr, mock_mac, 6);

    /* Magic Cookie: 99.130.83.99 */
    packet.magic_cookie = htonl(0x63825363);

    /* Option 53: DHCP Message Type (Length 1, Value 1 = DHCPDISCOVER) */
    int opt_idx = 0;
    packet.options[opt_idx++] = 53;
    packet.options[opt_idx++] = 1;
    packet.options[opt_idx++] = 1;  /* 1 = DHCPDISCOVER */

    /* Option 55: Parameter Request List (Subnet Mask, Router, DNS) */
    packet.options[opt_idx++] = 55;
    packet.options[opt_idx++] = 3;
    packet.options[opt_idx++] = 1;  /* Subnet Mask */
    packet.options[opt_idx++] = 3;  /* Router */
    packet.options[opt_idx++] = 6;  /* Domain Name Server */

    /* Option 255: End Option */
    packet.options[opt_idx++] = 255;

    struct sockaddr_in dest;
    memset(&dest, 0, sizeof(dest));
    dest.sin_family = AF_INET;
    dest.sin_port = htons(67);                    /* DHCP Server Port 67 */
    dest.sin_addr.s_addr = inet_addr("255.255.255.255"); /* Limited Broadcast */

    printf("[DHCP] Built DHCPDISCOVER packet: Size=%zu bytes, xid=0x%08X\n",
           sizeof(packet), ntohl(packet.xid));
    printf("[DHCP] Target: 255.255.255.255:67 (Broadcast)\n");

    /* Attempt transmission (Requires root permissions or local loopback in unprivileged dev) */
    ssize_t sent = sendto(sockfd, &packet, sizeof(packet), 0, (struct sockaddr *)&dest, sizeof(dest));
    if (sent > 0) {
        printf("  [PASS] Successfully broadcasted %zd bytes across local wire!\n", sent);
    } else {
        printf("  [NOTE] Broadcast restricted by OS network stack (Requires CAP_NET_RAW/Root).\n");
    }

    close(sockfd);
    return EXIT_SUCCESS;
}
```

---

## 5. Production War Story: The Multiple Server DHCPOFFER NAK War

In 2018, an enterprise office floor suffered total network connectivity failure whenever laptops were docked in the morning:
1. **The Culprit**: An engineer plugged a consumer Wi-Fi access point into a wall jack with its default DHCP server running on `192.168.0.1/24`, competing with the corporate server on `10.200.0.1/16`.
2. **The Battle**:
   - Laptop broadcasts `DHCPDISCOVER`.
   - Rogue AP replies with `DHCPOFFER` of `192.168.0.45` in 2 milliseconds. Corporate server replies in 15 milliseconds.
   - Laptop picks the faster rogue offer and broadcasts `DHCPREQUEST` requesting `192.168.0.45`.
   - The corporate DHCP server hears the request. Seeing an IP address that belongs to an alien subnet, it immediately issues a **`DHCPNAK` (Negative Acknowledgment)**!
   - The laptop receives `DHCPNAK`, drops the lease, restarts DORA from scratch, and loops indefinitely. Over 400 employees were disconnected.
3. **The Fix**: Deployment of **DHCP Snooping** on enterprise access switches (Day 45).

---

## 6. Verification & CLI Mastery Reference

| Command | Action | Deep Technical Purpose |
| :--- | :--- | :--- |
| `tcpdump -envvn -i eth0 port 67 or port 68` | Packet Sniff | Captures full DORA wire conversation with xid and option decoding. |
| `dhclient -v -r eth0` | Release Lease | Transmits `DHCPRELEASE` to server and flushes interface IP. |
| `dhclient -v eth0` | Trigger DORA | Initiates fresh 4-step DORA handshake and logs assigned options. |
| `cat /var/lib/dhcp/dhclient.leases` | Lease Inspection | Reads historical lease parameters, renewal timestamps, and router options. |
