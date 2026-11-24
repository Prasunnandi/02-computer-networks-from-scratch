#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tcp_state_machine_sim.py - TCP 4-Way Teardown & TIME_WAIT Simulator
Simulates FIN, ACK, FIN, ACK exchange and 2MSL timer execution.
"""

def simulate_tcp_teardown(client_seq: int = 1500, server_seq: int = 8200) -> list:
    log = []
    # Step 1: Active close by Client
    client_state = "FIN_WAIT_1"
    log.append(f"1. Client sends FIN: seq={client_seq} | Client enters {client_state}")
    
    # Step 2: Server receives FIN
    server_state = "CLOSE_WAIT"
    server_ack = client_seq + 1
    log.append(f"2. Server sends ACK: ack={server_ack} | Server enters {server_state}")
    client_state = "FIN_WAIT_2"
    log.append(f"   Client enters {client_state} (Half-closed: can still read server data)")
    
    # Step 3: Server finishes sending data and sends FIN
    server_state = "LAST_ACK"
    log.append(f"3. Server sends FIN: seq={server_seq}, ack={server_ack} | Server enters {server_state}")
    
    # Step 4: Client receives FIN, sends final ACK
    client_ack = server_seq + 1
    client_state = "TIME_WAIT"
    log.append(f"4. Client sends ACK: ack={client_ack} | Client enters {client_state} (2MSL = 60s)")
    
    server_state = "CLOSED"
    log.append(f"   Server receives final ACK -> Server enters {server_state}")
    
    return log

if __name__ == "__main__":
    print("=== TCP 4-Way Teardown & TIME_WAIT Simulation ===")
    steps = simulate_tcp_teardown()
    for s in steps:
        print(f"  {s}")
