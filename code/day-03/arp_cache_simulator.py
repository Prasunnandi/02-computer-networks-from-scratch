# -*- coding: utf-8 -*-
"""
Day 3 Lab: Address Resolution Protocol (ARP) Cache Simulator
Demonstrates broadcast query, unicast reply, and local cache expiration.
"""

class ARPCacheSimulator:
    def __init__(self):
        # Known network devices (IP -> MAC)
        self.network_devices = {
            "192.168.1.1": "00:1A:2B:3C:4D:5E",   # Default Gateway / Router
            "192.168.1.15": "A4:C3:F0:12:34:56",  # Office Printer
            "192.168.1.20": "D8:9E:F3:77:88:99",  # Teammate's Laptop
        }
        # Local ARP Table (initially empty)
        self.arp_table = {}

    def resolve_ip_to_mac(self, target_ip):
        print(f"\n[QUERY] Need to send frame to IP: {target_ip}")
        
        # 1. Check local ARP cache first!
        if target_ip in self.arp_table:
            mac = self.arp_table[target_ip]
            print(f"  --> [CACHE HIT] Found in local ARP table: {target_ip} -> {mac} (No network broadcast needed!)")
            return mac

        print(f"  --> [CACHE MISS] IP {target_ip} is NOT in local ARP table.")
        print(f"  --> [BROADCAST] Shouting to FF:FF:FF:FF:FF:FF: 'Who has {target_ip}? Tell my MAC!'")

        # 2. Simulate network broadcast
        if target_ip in self.network_devices:
            resolved_mac = self.network_devices[target_ip]
            print(f"  --> [UNICAST REPLY] Device with IP {target_ip} heard the shout and replied: My MAC is {resolved_mac}!")
            # 3. Save to local ARP cache!
            self.arp_table[target_ip] = resolved_mac
            print(f"  --> [SAVED] Cached {target_ip} -> {resolved_mac} in local ARP table.")
            return resolved_mac
        else:
            print(f"  --> [HOST UNREACHABLE] No device on the local network responded to ARP for {target_ip}!")
            return None

def main():
    print("==================================================")
    print("   NETWORKS DAY 3: ARP PROTOCOL SIMULATOR LAB     ")
    print("==================================================")

    simulator = ARPCacheSimulator()

    # Request 1: Needs broadcast because cache is empty
    simulator.resolve_ip_to_mac("192.168.1.1")

    # Request 2: Instant cache hit! No network broadcast needed!
    simulator.resolve_ip_to_mac("192.168.1.1")

    # Request 3: New device (printer), needs broadcast
    simulator.resolve_ip_to_mac("192.168.1.15")

    # Request 4: Non-existent IP
    simulator.resolve_ip_to_mac("192.168.1.99")

    print("\n==================================================")
    print("Final Local ARP Table State:")
    for ip, mac in simulator.arp_table.items():
        print(f"  {ip:<16} ---> {mac}")
    print("==================================================")

if __name__ == "__main__":
    main()
