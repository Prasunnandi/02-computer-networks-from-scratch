# -*- coding: utf-8 -*-
"""
Day 4 Lab: Custom IPv4 Subnet Calculator from Scratch
Calculates Network Address, Broadcast Address, Netmask, and Usable Host Range using bitwise logic.
"""

def ip_str_to_int(ip_str):
    octets = [int(x) for x in ip_str.split(".")]
    if len(octets) != 4 or any(o < 0 or o > 255 for o in octets):
        raise ValueError(f"Invalid IPv4 address: {ip_str}")
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

def int_to_ip_str(ip_int):
    return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"

def calculate_subnet(cidr_str):
    ip_part, prefix_part = cidr_str.split("/")
    prefix = int(prefix_part)
    if prefix < 0 or prefix > 32:
        raise ValueError("CIDR prefix must be between 0 and 32")

    ip_int = ip_str_to_int(ip_part)
    
    # Generate netmask by shifting 1s
    if prefix == 0:
        netmask_int = 0
    else:
        netmask_int = ((0xFFFFFFFF << (32 - prefix))) & 0xFFFFFFFF

    # Bitwise AND calculates Network ID
    network_int = ip_int & netmask_int

    # Wildcard mask calculates Broadcast ID
    wildcard_int = (~netmask_int) & 0xFFFFFFFF
    broadcast_int = network_int | wildcard_int

    total_hosts = 2 ** (32 - prefix)
    usable_hosts = max(0, total_hosts - 2)

    first_usable = network_int + 1 if usable_hosts > 0 else network_int
    last_usable = broadcast_int - 1 if usable_hosts > 0 else broadcast_int

    return {
        "CIDR": cidr_str,
        "Netmask": int_to_ip_str(netmask_int),
        "Network_Address": int_to_ip_str(network_int),
        "Broadcast_Address": int_to_ip_str(broadcast_int),
        "Usable_Range": f"{int_to_ip_str(first_usable)} - {int_to_ip_str(last_usable)}",
        "Total_Hosts": total_hosts,
        "Usable_Hosts": usable_hosts
    }

def main():
    print("==================================================")
    print("   NETWORKS DAY 4: IPV4 SUBNET CALCULATOR LAB     ")
    print("==================================================")

    test_cidrs = ["192.168.1.45/24", "10.0.50.12/16", "172.16.8.99/26"]

    for cidr in test_cidrs:
        res = calculate_subnet(cidr)
        print(f"\n--- Analysis for: {res['CIDR']} ---")
        print(f"  Subnet Netmask    : {res['Netmask']}")
        print(f"  Network Address   : {res['Network_Address']} (Reserved - ID)")
        print(f"  Broadcast Address : {res['Broadcast_Address']} (Reserved - Shout to all)")
        print(f"  Usable Host Range : {res['Usable_Range']}")
        print(f"  Total Usable Hosts: {res['Usable_Hosts']} devices")

    print("\n==================================================")

if __name__ == "__main__":
    main()
