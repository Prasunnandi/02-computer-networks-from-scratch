# Day 46: IPv4 Link-Local (APIPA) & Multicast DNS (mDNS) - Zero-Configuration Networking

## 1. Zero-Configuration Networking (Zeroconf) Architecture

When a client device connects to an ad-hoc local network where **no DHCP server exists** and **no authoritative DNS server is reachable** (e.g. connecting two laptops directly with an Ethernet cable, or IoT smart home devices on a local subnet), communication must not fail.

The IETF developed **Zero-Configuration Networking (Zeroconf)** to provide three autonomous network capabilities without human intervention or centralized infrastructure:
1. **Dynamic IPv4 Link-Local Address Allocation (APIPA - RFC 3927)**: Self-assigning an IP address from the reserved `169.254.0.0/16` prefix.
2. **Multicast DNS (mDNS - RFC 6762)**: Resolving domain names in the dedicated `.local` top-level domain without a DNS server via UDP multicast port 5353.
3. **DNS-Based Service Discovery (DNS-SD - RFC 6763)**: Discovering network printers, media streaming nodes, and file shares over mDNS using standard PTR, SRV, and TXT record semantics.

```
+--------------------------------------------------------------------------+
|                      ZEROCONF PROTOCOL SUITE TRIAD                       |
+--------------------------------------------------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                                                   |
          v                                                   v
+-------------------------------+             +------------------------------+
|     RFC 3927: IPv4 APIPA      |             |     RFC 6762: Multicast DNS  |
|  - Subnet: 169.254.0.0/16     |             |  - Top-Level Domain: .local  |
|  - Pseudo-random selection    |             |  - IPv4 Multicast: 224.0.0.251|
|  - ARP Probes & ARP Announces |             |  - IPv6 Multicast: FF02::FB  |
|  - Defends against collision  |             |  - UDP Port: 5353            |
+-------------------------------+             +------------------------------+
```

---

## 2. Kernel C Structs & Binary Bitfields: ARP Probes and Defenses

RFC 3927 specifies the mathematical state machine for claiming an APIPA address. To prevent allocating an address already used by a neighbor, the host uses **ARP Probes** and **ARP Announcements**:

```c
/* Real Linux Kernel ARP Header representation from net/ipv4/arp.c */
struct arphdr_rfc3927 {
    uint16_t    ar_hrd;         /* Hardware type: 1 = ARPHRD_ETHER */
    uint16_t    ar_pro;         /* Protocol type: 0x0800 = ETH_P_IP */
    uint8_t     ar_hln;         /* Hardware length: 6 for MAC */
    uint8_t     ar_pln;         /* Protocol length: 4 for IPv4 */
    uint16_t    ar_op;          /* Opcode: 1 = ARPOP_REQUEST, 2 = ARPOP_REPLY */
    
    /* Variable addresses */
    uint8_t     sender_mac[6];  /* Client physical MAC */
    uint32_t    sender_ip;      /* Set to 0.0.0.0 in ARP Probe to prevent cache pollution! */
    uint8_t     target_mac[6];  /* Zeroed (00:00:00:00:00:00) */
    uint32_t    target_ip;      /* Candidate 169.254.X.Y address under evaluation */
} __attribute__((packed));
```

### The ARP Probe Rule:
In an **ARP Probe**, the `sender_ip` field **MUST be set to `0.0.0.0`**. If the probing host used its candidate IP as `sender_ip`, all other hosts on the switch would update their ARP neighbor caches with this unconfirmed mapping, polluting their routing tables if a collision subsequently occurred!

---

## 3. Mathematical Foundations: APIPA Address Selection & Collision Dynamics

The Link-Local IPv4 prefix is defined by RFC 3927 as `169.254.0.0/16`.
The first 256 addresses (`169.254.0.0` to `169.254.0.255`) and the last 256 addresses (`169.254.255.0` to `169.254.255.255`) are reserved for future IETF expansion.

This leaves an active allocatable pool of:
$$N_{\text{pool}} = 2^{16} - 512 = 65,024 \text{ usable IP addresses}$$

### Pseudo-Random Seed Generation:
The client generates an initial candidate address using a deterministic pseudo-random sequence seeded by its 48-bit MAC address:
$$\text{CandidateIP} = 169.254.1.0 + \Big(\text{Hash}(\text{MAC}) \pmod{65024}\Big)$$

### Collision Probability in Ad-hoc Networks:
In an ad-hoc conference room or mesh cluster with $k$ devices selecting addresses uniformly at random:
$$P(\text{collision}) = 1 - \prod_{i=1}^{k-1} \left(1 - \frac{i}{N_{\text{pool}}}\right) \approx 1 - e^{-\frac{k^2}{2 \times 65024}}$$

For $k = 50$ devices:
$$\frac{k^2}{2 N} = \frac{2500}{130048} \approx 0.0192 \implies P \approx 1.90\%$$

To resolve the ~1.9% collision probability, RFC 3927 mandates transmitting **3 ARP Probes** spaced with randomized jitter between 1 and 2 seconds. If no host replies with an ARP response within 2 seconds, the client sends **2 ARP Announcements** (gratuitous ARPs with `sender_ip = target_ip`) and claims the address.

---

## 4. Compilable C Implementation: Multicast DNS (mDNS) Query Engine

Multicast DNS queries look identical to standard RFC 1035 DNS queries, but are transmitted via UDP to the link-local multicast address **`224.0.0.251` (Port 5353)**.

Save the following program as `mdns_query.c`:

```c
/*
 * mdns_query.c - Multicast DNS (mDNS) Query Transmitter
 * Demonstrates:
 * 1. Constructing standard RFC 1035 wire query for '.local' names
 * 2. Setting multicast TTL to 255 (RFC 6762 requirement)
 * 3. Transmitting over UDP to 224.0.0.251:5353
 *
 * Compilation:
 *   gcc -O2 -Wall -Wextra -pthread mdns_query.c -o mdns_query
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define MDNS_MULTICAST_ADDR "224.0.0.251"
#define MDNS_PORT           5353

int main(void)
{
    printf("====================================================\n");
    printf("MULTICAST DNS (mDNS) ZERO-CONF QUERY ENGINE\n");
    printf("====================================================\n");

    int sockfd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sockfd < 0) {
        perror("Socket creation failed");
        return EXIT_FAILURE;
    }

    /* RFC 6762 mandates setting IP Multicast TTL to 255 to ensure local-subnet propagation */
    unsigned char ttl = 255;
    if (setsockopt(sockfd, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl)) < 0) {
        perror("setsockopt IP_MULTICAST_TTL failed");
        close(sockfd);
        return EXIT_FAILURE;
    }

    /* Build a DNS query for "printer.local" */
    uint8_t packet[64];
    memset(packet, 0, sizeof(packet));

    /* 12-byte DNS Header: ID=0, Flags=0 (Standard Query), QDCOUNT=1 */
    packet[0] = 0x00; packet[1] = 0x00; /* ID = 0 for mDNS queries */
    packet[2] = 0x00; packet[3] = 0x00; /* Standard Query */
    packet[4] = 0x00; packet[5] = 0x01; /* QDCOUNT = 1 */

    /* QNAME: "printer.local" -> \x07printer\x05local\x00 */
    int idx = 12;
    const char *label1 = "printer";
    packet[idx++] = strlen(label1);
    memcpy(&packet[idx], label1, strlen(label1));
    idx += strlen(label1);

    const char *label2 = "local";
    packet[idx++] = strlen(label2);
    memcpy(&packet[idx], label2, strlen(label2));
    idx += strlen(label2);
    packet[idx++] = 0; /* Terminating null label */

    /* QTYPE = 1 (A Record), QCLASS = 1 (IN) */
    packet[idx++] = 0x00; packet[idx++] = 0x01; /* Type A */
    packet[idx++] = 0x00; packet[idx++] = 0x01; /* Class IN */

    struct sockaddr_in dest;
    memset(&dest, 0, sizeof(dest));
    dest.sin_family = AF_INET;
    dest.sin_port = htons(MDNS_PORT);
    dest.sin_addr.s_addr = inet_addr(MDNS_MULTICAST_ADDR);

    printf("[mDNS] Broadcasting query for 'printer.local' to %s:%d\n",
           MDNS_MULTICAST_ADDR, MDNS_PORT);

    ssize_t sent = sendto(sockfd, packet, idx, 0, (struct sockaddr *)&dest, sizeof(dest));
    if (sent > 0) {
        printf("  [PASS] Transmitted %zd bytes over local multicast group!\n", sent);
    } else {
        perror("sendto failed");
    }

    close(sockfd);
    return EXIT_SUCCESS;
}
```

---

## 5. Production War Story: The Subnet Flapping APIPA Cluster Severance

In 2021, an enterprise Kubernetes cluster running on bare-metal servers suffered an intermittent node-disconnect crisis:
1. **The Architecture**: Nodes used DHCP to acquire `10.240.0.X` IPs.
2. **The Flaw**: An upstream core switch had an aggressive spanning-tree port-cost recalculation that occasionally dropped physical link for 800 milliseconds.
3. **The Incident**: When link flapped, `NetworkManager` on Linux timed out on DHCP and immediately invoked APIPA fallback, self-assigning a `169.254.X.Y` address to the physical interface.
4. **The Disaster**: When the physical switch link recovered 1 second later, `NetworkManager` failed to tear down the APIPA IP, leaving the node isolated on a `169.254.0.0/16` subnet. The Kubernetes control plane declared the node dead and initiated emergency pod evictions, triggering database lock contention across the entire cluster.

**The Fix**:
Explicitly disable link-local IPv4 autoconfiguration on production datacenter servers:
```ini
# /etc/systemd/network/10-eth0.network
[Network]
LinkLocalAddressing=no
IPv4LLRoute=no
```

---

## 6. Verification & CLI Mastery Reference

| Command | Action | Deep Technical Purpose |
| :--- | :--- | :--- |
| `avahi-browse -a -t` | Discover Zeroconf | Browses all active DNS-SD services advertised over mDNS on the local LAN. |
| `resolvectl query myhost.local` | Query mDNS | Uses systemd-resolved to query the local `.local` multicast group. |
| `ip route show | grep 169.254` | Inspect APIPA | Verifies presence of the `169.254.0.0/16 dev eth0 scope link` kernel route. |
| `tcpdump -i eth0 udp port 5353` | Sniff mDNS | Captures multicast DNS announcements and response payloads. |
