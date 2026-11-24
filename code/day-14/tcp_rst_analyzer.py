#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tcp_rst_analyzer.py - TCP Reset (RST) Packet Generator & Abort Analyzer
Evaluates conditions that trigger RST packets and analyzes abortive close semantics.
"""

def analyze_rst_trigger(event_type: str, listening_ports: list, target_port: int, has_unread_data: bool) -> dict:
    send_rst = False
    reason = "Normal processing"
    
    if event_type == "SYN_RECEIVED":
        if target_port not in listening_ports:
            send_rst = True
            reason = f"Port {target_port} closed (ECONNREFUSED)"
    elif event_type == "SOCKET_CLOSE":
        if has_unread_data:
            send_rst = True
            reason = "Socket closed with unread data in receive buffer"
    elif event_type == "PACKET_TO_UNKNOWN_CONNECTION":
        send_rst = True
        reason = "Packet arrived for non-existent connection (Crash/Reboot recovery)"
        
    return {
        "event_type": event_type,
        "target_port": target_port,
        "should_send_rst": send_rst,
        "reason": reason,
        "bypasses_timewait": send_rst
    }

if __name__ == "__main__":
    open_ports = [80, 443, 22]
    
    test1 = analyze_rst_trigger("SYN_RECEIVED", open_ports, target_port=8080, has_unread_data=False)
    test2 = analyze_rst_trigger("SOCKET_CLOSE", open_ports, target_port=80, has_unread_data=True)
    
    print("=== TCP Reset (RST) Trigger Analysis ===")
    print("Test 1 (Connecting to Closed Port):")
    for k, v in test1.items():
        print(f"  {k}: {v}")
    print("\nTest 2 (Closing Socket with Unread Data):")
    for k, v in test2.items():
        print(f"  {k}: {v}")
