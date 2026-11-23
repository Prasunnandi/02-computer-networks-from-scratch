# -*- coding: utf-8 -*-
"""
Day 5 Lab: Network Address Translation (NAT) Router Simulator
Demonstrates how multiple private devices share one public IP using port translation!
"""

class NATRouterSimulator:
    def __init__(self, public_ip="203.0.113.1"):
        self.public_ip = public_ip
        # NAT Translation Table: (External_Port) -> (Private_IP, Private_Port)
        self.nat_table = {}
        self.next_external_port = 50000

    def send_outbound_packet(self, private_ip, private_port, destination_ip, destination_port, payload):
        # Assign an external port on the public IP
        ext_port = self.next_external_port
        self.next_external_port += 1

        # Save mapping in NAT table
        self.nat_table[ext_port] = (private_ip, private_port)

        print(f"\n[OUTBOUND PACKET CREATED]")
        print(f"  Internal Origin : {private_ip}:{private_port}")
        print(f"  NAT Rewriting   : Source changed to {self.public_ip}:{ext_port} (NAT table updated!)")
        print(f"  Destination     : {destination_ip}:{destination_port}")
        print(f"  Payload         : '{payload}'")

        return {
            "source_ip": self.public_ip,
            "source_port": ext_port,
            "dest_ip": destination_ip,
            "dest_port": destination_port,
            "payload": payload
        }

    def receive_inbound_packet(self, inbound_packet):
        ext_port = inbound_packet["dest_port"]
        print(f"\n[INBOUND PACKET RECEIVED FROM INTERNET]")
        print(f"  Arrived at Public Address: {inbound_packet['dest_ip']}:{ext_port}")

        # Check NAT Table
        if ext_port in self.nat_table:
            target_private_ip, target_private_port = self.nat_table[ext_port]
            print(f"  --> [NAT LOOKUP SUCCESS] Port {ext_port} belongs to Private Device {target_private_ip}:{target_private_port}!")
            print(f"  --> Forwarding payload '{inbound_packet['payload']}' to {target_private_ip}:{target_private_port}")
            return True
        else:
            print(f"  --> [NAT LOOKUP FAILED] No device in the private network opened port {ext_port}! Dropping packet!")
            return False

def main():
    print("==================================================")
    print("      NETWORKS DAY 5: NAT ROUTER SIMULATOR        ")
    print("==================================================")

    router = NATRouterSimulator(public_ip="142.250.190.46")

    # 1. Laptop makes request to Google
    pkt1 = router.send_outbound_packet(
        private_ip="192.168.1.5",
        private_port=54321,
        destination_ip="8.8.8.8",
        destination_port=443,
        payload="GET /index.html"
    )

    # 2. Phone makes request to Netflix
    pkt2 = router.send_outbound_packet(
        private_ip="192.168.1.8",
        private_port=54321, # Same private port, but different NAT external port!
        destination_ip="1.1.1.1",
        destination_port=443,
        payload="GET /stream"
    )

    print("\n--- Current NAT Table in Router Memory ---")
    for ext_p, (p_ip, p_p) in router.nat_table.items():
        print(f"  Public Port {ext_p} ---> Mapped to {p_ip}:{p_p}")

    # 3. Web server replies back to the Laptop
    reply_to_laptop = {
        "source_ip": "8.8.8.8",
        "source_port": 443,
        "dest_ip": router.public_ip,
        "dest_port": pkt1["source_port"], # Router's port 50000
        "payload": "200 OK (Google Homepage HTML)"
    }
    router.receive_inbound_packet(reply_to_laptop)

    # 4. Unknown hacker sends random packet from internet
    unsolicited_attack = {
        "source_ip": "198.51.100.23",
        "source_port": 1234,
        "dest_ip": router.public_ip,
        "dest_port": 9999, # Random port not in NAT table!
        "payload": "MALICIOUS SCAN"
    }
    router.receive_inbound_packet(unsolicited_attack)

    print("\n==================================================")
    print("Notice how NAT dropped the unsolicited attack automatically!")

if __name__ == "__main__":
    main()
