#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handshake_simulator.py - TCP 3-Way Handshake State Machine Simulator
Simulates SYN, SYN-ACK, ACK transitions and Initial Sequence Number (ISN) tracking.
"""

class TCPEndpoint:
    def __init__(self, name: str, isn: int):
        self.name = name
        self.state = "CLOSED"
        self.isn = isn
        self.seq = isn
        self.ack = 0

class TCPHandshakeSimulation:
    def __init__(self):
        self.client = TCPEndpoint("Client", isn=10000)
        self.server = TCPEndpoint("Server", isn=50000)
        self.server.state = "LISTEN"

    def run(self) -> list:
        log = []
        # Step 1: Client sends SYN
        self.client.state = "SYN_SENT"
        log.append(f"[Step 1: SYN] Client -> Server: seq={self.client.seq}, flags=SYN")
        
        # Server receives SYN
        self.server.state = "SYN_RCVD"
        self.server.ack = self.client.seq + 1 # SYN consumes 1 sequence number
        
        # Step 2: Server sends SYN-ACK
        log.append(f"[Step 2: SYN-ACK] Server -> Client: seq={self.server.seq}, ack={self.server.ack}, flags=SYN+ACK")
        
        # Client receives SYN-ACK
        self.client.state = "ESTABLISHED"
        self.client.seq = self.server.ack
        self.client.ack = self.server.seq + 1 # SYN consumes 1 sequence number
        
        # Step 3: Client sends ACK
        log.append(f"[Step 3: ACK] Client -> Server: seq={self.client.seq}, ack={self.client.ack}, flags=ACK")
        
        # Server receives ACK
        self.server.state = "ESTABLISHED"
        self.server.seq = self.client.ack
        
        return log

if __name__ == "__main__":
    sim = TCPHandshakeSimulation()
    events = sim.run()
    print("=== TCP 3-Way Handshake Simulation ===")
    for e in events:
        print(f"  {e}")
    print(f"Final Client State: {sim.client.state}")
    print(f"Final Server State: {sim.server.state}")
