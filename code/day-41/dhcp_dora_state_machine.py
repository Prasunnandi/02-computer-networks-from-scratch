"""
Day 41: DHCP DORA State Machine Simulator
100% pure Python standard library implementation of the 4-step DHCP exchange:
DISCOVER -> OFFER -> REQUEST -> ACK with client FSM and server address pool.
"""

from dataclasses import dataclass, field
import enum
import random
import struct
import time
from typing import Dict, List, Optional, Tuple


class DHCPMessageType(enum.Enum):
    DISCOVER = 1
    OFFER = 2
    REQUEST = 3
    DECLINE = 4
    ACK = 5
    NAK = 6
    RELEASE = 7
    INFORM = 8


class ClientState(enum.Enum):
    INIT = "INIT"
    SELECTING = "SELECTING"
    REQUESTING = "REQUESTING"
    BOUND = "BOUND"


@dataclass
class DHCPMessage:
    op: int                      # 1 = BOOTREQUEST, 2 = BOOTREPLY
    xid: int                     # Transaction ID
    ciaddr: str                  # Client IP address
    yiaddr: str                  # 'Your' (client) IP address
    siaddr: str                  # Next server IP address
    chaddr: str                  # Client hardware address (MAC)
    msg_type: DHCPMessageType    # Option 53
    server_id: Optional[str] = None  # Option 54
    lease_time: int = 3600       # Option 51 (seconds)
    subnet_mask: str = "255.255.255.0"
    router: str = "192.168.1.1"
    dns_server: str = "8.8.8.8"


class DHCPServer:
    """Simulates an RFC 2131 compliant DHCP server managing a subnet pool."""

    def __init__(self, server_ip: str, pool_start: str, pool_end: str, lease_time: int = 3600):
        self.server_ip = server_ip
        self.pool_start = pool_start
        self.pool_end = pool_end
        self.lease_time = lease_time
        self.subnet_mask = "255.255.255.0"
        self.router = server_ip
        self.dns_server = "1.1.1.1"

        self.leases: Dict[str, Tuple[str, float]] = {}
        self.pending_offers: Dict[int, Tuple[str, float]] = {}
        self.available_ips: List[str] = self._generate_pool(pool_start, pool_end)

    def _ip_to_int(self, ip: str) -> int:
        octets = [int(x) for x in ip.split(".")]
        return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

    def _int_to_ip(self, val: int) -> str:
        return f"{(val >> 24) & 0xFF}.{(val >> 16) & 0xFF}.{(val >> 8) & 0xFF}.{val & 0xFF}"

    def _generate_pool(self, start: str, end: str) -> List[str]:
        s = self._ip_to_int(start)
        e = self._ip_to_int(end)
        return [self._int_to_ip(i) for i in range(s, e + 1)]

    def handle_discover(self, msg: DHCPMessage) -> Optional[DHCPMessage]:
        if msg.msg_type != DHCPMessageType.DISCOVER:
            return None

        offered_ip = None
        now = time.time()
        if msg.chaddr in self.leases:
            curr_ip, exp = self.leases[msg.chaddr]
            if exp > now:
                offered_ip = curr_ip

        if not offered_ip:
            assigned = {ip for ip, exp in self.leases.values() if exp > now}
            offered = {ip for ip, exp in self.pending_offers.values() if now - exp < 10.0}
            for ip in self.available_ips:
                if ip not in assigned and ip not in offered:
                    offered_ip = ip
                    break

        if not offered_ip:
            return None

        self.pending_offers[msg.xid] = (offered_ip, now)
        return DHCPMessage(
            op=2,
            xid=msg.xid,
            ciaddr="0.0.0.0",
            yiaddr=offered_ip,
            siaddr=self.server_ip,
            chaddr=msg.chaddr,
            msg_type=DHCPMessageType.OFFER,
            server_id=self.server_ip,
            lease_time=self.lease_time,
            subnet_mask=self.subnet_mask,
            router=self.router,
            dns_server=self.dns_server
        )

    def handle_request(self, msg: DHCPMessage) -> DHCPMessage:
        now = time.time()
        if msg.server_id and msg.server_id != self.server_ip:
            self.pending_offers.pop(msg.xid, None)
            return None

        req_ip = msg.ciaddr if msg.ciaddr != "0.0.0.0" else self.pending_offers.get(msg.xid, (None, 0))[0]
        if not req_ip:
            return DHCPMessage(
                op=2, xid=msg.xid, ciaddr="0.0.0.0", yiaddr="0.0.0.0", siaddr=self.server_ip,
                chaddr=msg.chaddr, msg_type=DHCPMessageType.NAK, server_id=self.server_ip
            )

        self.leases[msg.chaddr] = (req_ip, now + self.lease_time)
        self.pending_offers.pop(msg.xid, None)

        return DHCPMessage(
            op=2,
            xid=msg.xid,
            ciaddr="0.0.0.0",
            yiaddr=req_ip,
            siaddr=self.server_ip,
            chaddr=msg.chaddr,
            msg_type=DHCPMessageType.ACK,
            server_id=self.server_ip,
            lease_time=self.lease_time,
            subnet_mask=self.subnet_mask,
            router=self.router,
            dns_server=self.dns_server
        )


class DHCPClient:
    """State machine client managing dynamic IP configuration."""

    def __init__(self, mac_address: str):
        self.mac = mac_address
        self.state = ClientState.INIT
        self.assigned_ip: Optional[str] = None
        self.subnet_mask: Optional[str] = None
        self.router: Optional[str] = None
        self.dns_server: Optional[str] = None
        self.server_id: Optional[str] = None
        self.lease_time: int = 0
        self.current_xid: int = 0

    def start_discovery(self) -> DHCPMessage:
        self.state = ClientState.SELECTING
        self.current_xid = random.randint(1, 0x7FFFFFFF)
        return DHCPMessage(
            op=1,
            xid=self.current_xid,
            ciaddr="0.0.0.0",
            yiaddr="0.0.0.0",
            siaddr="0.0.0.0",
            chaddr=self.mac,
            msg_type=DHCPMessageType.DISCOVER
        )

    def select_offer(self, offer: DHCPMessage) -> Optional[DHCPMessage]:
        if self.state != ClientState.SELECTING:
            return None
        if offer.xid != self.current_xid or offer.msg_type != DHCPMessageType.OFFER:
            return None

        self.state = ClientState.REQUESTING
        self.server_id = offer.server_id
        return DHCPMessage(
            op=1,
            xid=self.current_xid,
            ciaddr="0.0.0.0",
            yiaddr=offer.yiaddr,
            siaddr=offer.server_id,
            chaddr=self.mac,
            msg_type=DHCPMessageType.REQUEST,
            server_id=offer.server_id
        )

    def handle_ack(self, ack: DHCPMessage) -> bool:
        if self.state != ClientState.REQUESTING:
            return False
        if ack.xid != self.current_xid or ack.msg_type != DHCPMessageType.ACK:
            return False

        self.assigned_ip = ack.yiaddr
        self.subnet_mask = ack.subnet_mask
        self.router = ack.router
        self.dns_server = ack.dns_server
        self.lease_time = ack.lease_time
        self.state = ClientState.BOUND
        return True


def main():
    print("=== Day 41: DHCP DORA State Machine Simulator ===")
    server = DHCPServer(server_ip="192.168.1.1", pool_start="192.168.1.100", pool_end="192.168.1.200")
    client = DHCPClient(mac_address="00:1A:2B:3C:4D:5E")

    discover_msg = client.start_discovery()
    assert client.state == ClientState.SELECTING
    print(f"[Step 1] Client sends DISCOVER: xid=0x{discover_msg.xid:08X}, MAC={discover_msg.chaddr}")

    offer_msg = server.handle_discover(discover_msg)
    assert offer_msg is not None
    assert offer_msg.msg_type == DHCPMessageType.OFFER
    assert offer_msg.yiaddr == "192.168.1.100"
    print(f"[Step 2] Server responds OFFER: Offered IP={offer_msg.yiaddr}, Server={offer_msg.server_id}")

    request_msg = client.select_offer(offer_msg)
    assert request_msg is not None
    assert client.state == ClientState.REQUESTING
    print(f"[Step 3] Client broadcasts REQUEST: Requested IP={request_msg.yiaddr}, Server={request_msg.server_id}")

    ack_msg = server.handle_request(request_msg)
    assert ack_msg.msg_type == DHCPMessageType.ACK
    success = client.handle_ack(ack_msg)
    assert success is True
    assert client.state == ClientState.BOUND
    assert client.assigned_ip == "192.168.1.100"
    print(f"[Step 4] Server sends ACK: Client BOUND to {client.assigned_ip} (Gateway: {client.router}, DNS: {client.dns_server})")

    client2 = DHCPClient(mac_address="00:50:56:C0:00:08")
    d2 = client2.start_discovery()
    o2 = server.handle_discover(d2)
    assert o2.yiaddr == "192.168.1.101"
    r2 = client2.select_offer(o2)
    a2 = server.handle_request(r2)
    client2.handle_ack(a2)
    assert client2.assigned_ip == "192.168.1.101"
    print(f"[*] Second client allocated next sequential IP: {client2.assigned_ip}")

    print("All DHCP DORA State Machine assertions passed successfully!")


if __name__ == "__main__":
    main()
