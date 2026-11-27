# Day 47: LLMNR & NetBIOS Name Service - Legacy Local Resolution and Poisoning Vectors

## 1. Local Name Resolution Before DNS: The NetBIOS and LLMNR Era

Before modern DNS servers were ubiquitous, local subnet name resolution on Windows and mixed OS networks was handled by two legacy protocols:
1. **NetBIOS Name Service (NBNS / WINS - RFC 1001 / 1002)**: Developed in 1987. Binds 16-character machine and service names over UDP broadcast **Port 137**. Uses custom half-byte ASCII character encoding.
2. **Link-Local Multicast Name Resolution (LLMNR - RFC 4795)**: Developed by Microsoft to modernize local name resolution without full mDNS adoption. Operates via UDP multicast on **Port 5355** (`224.0.0.252` in IPv4, `FF02::1:3` in IPv6).

### Windows Fallback Hierarchy:
When a Windows machine attempts to resolve a hostname (e.g. `fileserver`):
$$\text{DNS (Port 53)} \xrightarrow{\text{Fail}} \text{LLMNR (UDP 5355)} \xrightarrow{\text{Fail}} \text{NetBIOS (UDP 137)}$$

If DNS fails (or if an employee mistypes a server name like `\\prnter`), Windows immediately broadcasts LLMNR and NetBIOS queries to the entire local network:
$$\text{"Does anyone know the IP for PRNTER?"}$$

```
+--------------------------------------------------------------------------+
|                  THE LLMNR / NETBIOS POISONING VECTOR                    |
+--------------------------------------------------------------------------+
|  VICTIM WORKSTATION                                  ATTACKER (Responder)|
|  Types: \\fileshare                                  Running: responder  |
+--------------------------------------------------------------------------+
       |                                                       |
       | 1. DNS Query fails (fileshare not in corporate DNS)   |
       |                                                       |
       | 2. LLMNR Multicast (UDP 5355 to 224.0.0.252)          |
       |    "Who is fileshare?"                                |
       |------------------------------------------------------>|
       |                                                       |
       | 3. Poisoned LLMNR Response                            |
       |    "I am fileshare! My IP is: 10.0.0.99 (Attacker)"   |
       |<------------------------------------------------------|
       |                                                       |
       | 4. SMB Connection to 10.0.0.99                        |
       |    Transmits NTLMv2 Hash: User\Domain\Challenge\HMAC  |
       |------------------------------------------------------>|
       |                                                       |
       | Attacker captures NTLMv2 hash -> Cracks via Hashcat!  |
+--------------------------------------------------------------------------+
```

---

## 2. Kernel C Structs & Binary Bitfields: NetBIOS 16-Character Name Encoding

NetBIOS names are strictly 16 characters long. Characters 1 to 15 represent the machine name, padded with ASCII spaces. The 16th character (the **Suffix Byte**) defines the specific service role:
- `0x00`: Workstation Service
- `0x20`: File Server Service (SMB)
- `0x1B`: Domain Master Browser
- `0x1D`: Master Browser

### The Half-Byte First-Level Encoding Algorithm:
Because NetBIOS names travel inside standard DNS-like label envelopes, each 8-bit ASCII character is split into two 4-bit nibbles, added to ASCII `'A'` (`0x41`), and encoded as two ASCII characters:

```c
/* Real NetBIOS Half-byte First-Level Encoding Logic */
void encode_netbios_name(const char *input_name, uint8_t service_byte, char *output_wire)
{
    char padded[16];
    memset(padded, ' ', 15);
    int len = strlen(input_name);
    if (len > 15) len = 15;
    memcpy(padded, input_name, len);
    padded[15] = service_byte;

    /* First byte in DNS wire format is label length = 32 bytes */
    output_wire[0] = 32;

    for (int i = 0; i < 16; i++) {
        uint8_t c = (uint8_t)padded[i];
        output_wire[1 + (i * 2)]     = 'A' + ((c >> 4) & 0x0F); /* High nibble */
        output_wire[1 + (i * 2) + 1] = 'A' + (c & 0x0F);        /* Low nibble */
    }
    output_wire[33] = 0; /* Null terminator */
}
```

---

## 3. Mathematical Foundations: NTLMv2 Cryptographic Hash Capture

When a poisoned LLMNR response directs a victim to connect to an attacker-controlled SMB server, Windows automatically negotiates authentication using **NTLMv2**.

### The NTLMv2 Challenge-Response Formula:
1. Attacker server generates an 8-byte random server challenge:
   $$C_{\text{server}} \in \{0, 1\}^{64}$$
2. Client generates an 8-byte random client challenge (blob):
   $$C_{\text{client}} \in \{0, 1\}^{64}$$
3. Client computes intermediate NTLMv2 hash using user's secret NT password hash:
   $$H_{\text{NTLMv2}} = \text{HMAC-MD5}\left(\text{NT\_Hash}, \quad \text{Upper}(\text{Username}) \parallel \text{Domain}\right)$$
4. Client computes the final response $R$:
   $$R = \text{HMAC-MD5}\left(H_{\text{NTLMv2}}, \quad C_{\text{server}} \parallel C_{\text{client}} \parallel \text{Timestamp} \parallel \text{TargetInfo}\right)$$

The attacker captures $\langle C_{\text{server}}, C_{\text{client}}, R \rangle$. Because MD5 is fast to compute on modern GPUs, tools like `hashcat` can execute $5 \times 10^9$ hash evaluations per second, cracking passwords with catastrophic speed!

---

## 4. Compilable C Implementation: NetBIOS Name Decoder & Wire Crafter

Save the following program as `netbios_codec.c`:

```c
/*
 * netbios_codec.c - RFC 1001/1002 NetBIOS Name Encoding and Decoding Engine
 * Demonstrates:
 * 1. Splitting 8-bit ASCII bytes into 4-bit nibbles with 'A' base offset
 * 2. Extracting service suffix byte (e.g. 0x20 File Server)
 * 3. Round-trip validation
 *
 * Compilation:
 *   gcc -O2 -Wall -Wextra -pthread netbios_codec.c -o netbios_codec
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>

void netbios_encode(const char *name, uint8_t suffix, char *out_encoded)
{
    char padded[16];
    memset(padded, ' ', 15);
    int len = strlen(name);
    if (len > 15) len = 15;
    for (int i = 0; i < len; i++) {
        padded[i] = toupper((unsigned char)name[i]);
    }
    padded[15] = suffix;

    for (int i = 0; i < 16; i++) {
        uint8_t b = (uint8_t)padded[i];
        out_encoded[i * 2]     = 'A' + ((b >> 4) & 0x0F);
        out_encoded[i * 2 + 1] = 'A' + (b & 0x0F);
    }
    out_encoded[32] = '\0';
}

void netbios_decode(const char *encoded, char *out_name, uint8_t *out_suffix)
{
    char decoded[17];
    for (int i = 0; i < 16; i++) {
        uint8_t high = encoded[i * 2] - 'A';
        uint8_t low  = encoded[i * 2 + 1] - 'A';
        decoded[i] = (char)((high << 4) | (low & 0x0F));
    }
    decoded[16] = '\0';

    *out_suffix = (uint8_t)decoded[15];

    /* Trim trailing spaces from name */
    int idx = 14;
    while (idx >= 0 && decoded[idx] == ' ') {
        idx--;
    }
    decoded[idx + 1] = '\0';
    strcpy(out_name, decoded);
}

int main(void)
{
    printf("====================================================\n");
    printf("RFC 1001/1002 NetBIOS FIRST-LEVEL CODEC\n");
    printf("====================================================\n");

    const char *test_host = "FILESERVER";
    uint8_t service = 0x20; /* 0x20 = SMB File Server */

    char encoded[33];
    netbios_encode(test_host, service, encoded);

    printf("[ENCODER] Hostname: '%s' (Suffix: 0x%02X)\n", test_host, service);
    printf("[ENCODER] 32-Byte NetBIOS Wire String:\n  %s\n", encoded);

    char recovered_name[17];
    uint8_t recovered_suffix;
    netbios_decode(encoded, recovered_name, &recovered_suffix);

    printf("[DECODER] Recovered Name   : '%s'\n", recovered_name);
    printf("[DECODER] Recovered Suffix : 0x%02X\n", recovered_suffix);

    if (strcmp(test_host, recovered_name) == 0 && recovered_suffix == service) {
        printf("\n[VERIFIED] Round-trip NetBIOS encoding/decoding matched 100%%!\n");
    }

    return EXIT_SUCCESS;
}
```

---

## 5. Production War Story: The Responder Corporate Breach Incident

In 2018, a Fortune 100 industrial manufacturer had its entire Active Directory domain compromised in under 45 minutes during an authorized penetration test:
1. **The Vector**: An engineer typed `\\filesharr\docs` (a simple typo for `\\fileshare`).
2. **The Mechanism**:
   - Corporate DNS returned `NXDOMAIN`.
   - Windows automatically broadcasted an LLMNR query over UDP 5355 to `224.0.0.252`.
   - The security consultant’s laptop was running `responder -I eth0`.
   - Responder immediately replied: `I am filesharr at 10.10.10.200`.
   - The victim's workstation initiated an SMB handshake and transmitted the user's NTLMv2 hash.
3. **The Disaster**: The victim was a Domain Administrator who happened to be checking documentation. The consultant cracked the 8-character password within 12 minutes on an RTX 2080 GPU, achieving full Domain Admin control.

**The Fix**:
1. Disable LLMNR via Active Directory Group Policy (GPO):
   `Computer Configuration -> Administrative Templates -> Network -> DNS Client -> Turn off multicast name resolution = Enabled`.
2. Disable NetBIOS on all DHCP scopes via DHCP Option 43/Vendor spaces or direct network adapter properties.

---

## 6. Verification & CLI Mastery Reference

| Command | Action | Deep Technical Purpose |
| :--- | :--- | :--- |
| `nbtstat -A <ip>` | Query NetBIOS Table | Dumps remote host's NetBIOS 16-character service table over UDP port 137. |
| `tcpdump -i eth0 udp port 5355` | Sniff LLMNR | Captures multicast LLMNR local name resolution traffic on the wire. |
| `systemd-resolve --status` | Check Status | Audits whether `LLMNR=no` and `MulticastDNS=no` are enforced locally. |
