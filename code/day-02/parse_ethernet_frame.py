# -*- coding: utf-8 -*-
"""
Day 2 Lab: Parsing Raw Ethernet II Frames
Decodes 14-byte Ethernet headers from hex bytes!
"""

ETHERTYPES = {
    0x0800: "IPv4 (Internet Protocol v4)",
    0x0806: "ARP (Address Resolution Protocol)",
    0x86DD: "IPv6 (Internet Protocol v6)"
}

def format_mac(byte_seq):
    return ":".join(f"{b:02X}" for b in byte_seq)

def parse_ethernet_header(raw_bytes):
    if len(raw_bytes) < 14:
        raise ValueError("Ethernet header must be at least 14 bytes long!")

    # Byte 0 to 5: Destination MAC
    dst_mac = format_mac(raw_bytes[0:6])
    
    # Byte 6 to 11: Source MAC
    src_mac = format_mac(raw_bytes[6:12])
    
    # Byte 12 to 13: EtherType (Big-Endian 16-bit integer)
    ethertype_int = (raw_bytes[12] << 8) | raw_bytes[13]
    protocol = ETHERTYPES.get(ethertype_int, f"Unknown Protocol (0x{ethertype_int:04X})")

    payload = raw_bytes[14:]

    return {
        "Destination_MAC": dst_mac,
        "Source_MAC": src_mac,
        "EtherType_Hex": f"0x{ethertype_int:04X}",
        "Protocol": protocol,
        "Payload_Length": len(payload)
    }

def main():
    print("==================================================")
    print("   NETWORKS DAY 2: ETHERNET FRAME DECODER LAB     ")
    print("==================================================")

    # Sample simulated captured Ethernet frame (in Hex bytes)
    # Dst: AA:BB:CC:11:22:33, Src: B4:2E:99:A1:0F:7D, EtherType: 08 00 (IPv4), Payload: Hello Network!
    sample_raw_frame = bytes([
        0xAA, 0xBB, 0xCC, 0x11, 0x22, 0x33, # Destination MAC
        0xB4, 0x2E, 0x99, 0xA1, 0x0F, 0x7D, # Source MAC
        0x08, 0x00,                         # EtherType: 0x0800 (IPv4)
        0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x4E, 0x65, 0x74, 0x77, 0x6F, 0x72, 0x6B, 0x21 # Payload
    ])

    info = parse_ethernet_header(sample_raw_frame)
    print(f"Destination MAC : {info['Destination_MAC']}")
    print(f"Source MAC      : {info['Source_MAC']}")
    print(f"EtherType       : {info['EtherType_Hex']} -> {info['Protocol']}")
    print(f"Payload Size    : {info['Payload_Length']} bytes")
    print(f"Payload Content : {sample_raw_frame[14:].decode('utf-8', errors='ignore')}")
    print("==================================================")

if __name__ == "__main__":
    main()
