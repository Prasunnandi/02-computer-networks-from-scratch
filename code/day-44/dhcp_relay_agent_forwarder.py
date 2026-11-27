"""
Day 44: DHCP Relay Agent Cross-Subnet Forwarder Simulator
100% pure Python standard library implementation of RFC 3046 Relay Agent (Option 82)
forwarding, hop-count enforcement, and giaddr gateway IP injection.
"""

from dataclasses import dataclass, field
import struct
from typing import Dict, List, Optional, Tuple


@dataclass
class RelayPacket:
    op: int
    xid: int
    hops: int
    ciaddr: str
    yiaddr: str
    giaddr: str
    chaddr: str
    options: Dict[int, bytes] = field(default_factory=dict)


class DHCPRelayAgent:
    """Simulates an L3 switch/router relay agent forwarding DHCP across subnets."""

    MAX_HOPS = 16
    OPTION_RELAY_INFO = 82

    def __init__(self, interface_ips: Dict[str, str], upstream_server_ip: str):
        self.interface_ips = interface_ips
        self.upstream_server_ip = upstream_server_ip
        self.forwarded_count = 0
        self.dropped_count = 0

    @staticmethod
    def encode_option_82(circuit_id: str, remote_id: str) -> bytes:
        c_bytes = circuit_id.encode("ascii")
        r_bytes = remote_id.encode("ascii")
        sub1 = struct.pack("!BB", 1, len(c_bytes)) + c_bytes
        sub2 = struct.pack("!BB", 2, len(r_bytes)) + r_bytes
        return sub1 + sub2

    @staticmethod
    def decode_option_82(raw: bytes) -> Tuple[str, str]:
        idx = 0
        circuit_id = ""
        remote_id = ""
        while idx < len(raw):
            sub_tag = raw[idx]
            sub_len = raw[idx + 1]
            sub_val = raw[idx + 2: idx + 2 + sub_len]
            idx += 2 + sub_len
            if sub_tag == 1:
                circuit_id = sub_val.decode("ascii")
            elif sub_tag == 2:
                remote_id = sub_val.decode("ascii")
        return circuit_id, remote_id

    def forward_client_request(self, pkt: RelayPacket, incoming_interface: str) -> Optional[Tuple[str, RelayPacket]]:
        if incoming_interface not in self.interface_ips:
            self.dropped_count += 1
            return None

        if pkt.hops >= self.MAX_HOPS:
            self.dropped_count += 1
            return None

        pkt.hops += 1

        if pkt.giaddr == "0.0.0.0" or not pkt.giaddr:
            pkt.giaddr = self.interface_ips[incoming_interface]

        circuit_id = f"vlan100-{incoming_interface}"
        remote_id = f"switch-core-01-{pkt.chaddr}"
        pkt.options[self.OPTION_RELAY_INFO] = self.encode_option_82(circuit_id, remote_id)

        self.forwarded_count += 1
        return self.upstream_server_ip, pkt

    def forward_server_reply(self, pkt: RelayPacket) -> Optional[Tuple[str, RelayPacket]]:
        if self.OPTION_RELAY_INFO in pkt.options:
            raw_opt82 = pkt.options.pop(self.OPTION_RELAY_INFO)
            circuit_id, remote_id = self.decode_option_82(raw_opt82)
            target_interface = None
            for iface, ip in self.interface_ips.items():
                if ip == pkt.giaddr:
                    target_interface = iface
                    break

            if target_interface:
                return target_interface, pkt

        self.dropped_count += 1
        return None


def main():
    print("=== Day 44: DHCP Relay Agent Cross-Subnet Forwarder Simulator ===")

    relay = DHCPRelayAgent(
        interface_ips={"eth1": "192.168.10.1", "eth2": "192.168.20.1"},
        upstream_server_ip="10.0.0.5"
    )

    client_pkt = RelayPacket(
        op=1,
        xid=0xABCDEF01,
        hops=0,
        ciaddr="0.0.0.0",
        yiaddr="0.0.0.0",
        giaddr="0.0.0.0",
        chaddr="00:11:22:33:44:55",
        options={53: b"\x01"}
    )

    result = relay.forward_client_request(client_pkt, incoming_interface="eth1")
    assert result is not None
    dest_ip, forwarded = result
    assert dest_ip == "10.0.0.5"
    assert forwarded.hops == 1
    assert forwarded.giaddr == "192.168.10.1"
    assert 82 in forwarded.options
    circuit_id, remote_id = relay.decode_option_82(forwarded.options[82])
    assert circuit_id == "vlan100-eth1"
    assert "00:11:22:33:44:55" in remote_id
    print(f"[*] Client DISCOVER relayed to {dest_ip}: giaddr={forwarded.giaddr}, hops={forwarded.hops}")
    print(f"[*] Injected Option 82: Circuit ID='{circuit_id}', Remote ID='{remote_id}'")

    server_reply = RelayPacket(
        op=2,
        xid=0xABCDEF01,
        hops=1,
        ciaddr="0.0.0.0",
        yiaddr="192.168.10.150",
        giaddr="192.168.10.1",
        chaddr="00:11:22:33:44:55",
        options={
            53: b"\x02",
            82: forwarded.options[82]
        }
    )

    reply_result = relay.forward_server_reply(server_reply)
    assert reply_result is not None
    out_iface, delivered_pkt = reply_result
    assert out_iface == "eth1"
    assert 82 not in delivered_pkt.options
    print(f"[*] Server OFFER stripped Option 82 and forwarded to subnet on {out_iface}")

    loop_pkt = RelayPacket(op=1, xid=0x111, hops=16, ciaddr="0.0.0.0", yiaddr="0.0.0.0", giaddr="0.0.0.0", chaddr="AA:BB:CC:DD:EE:FF")
    drop_res = relay.forward_client_request(loop_pkt, "eth1")
    assert drop_res is None
    print("[*] Hop count >= 16 loop detection successfully dropped packet")

    print("All DHCP Relay Agent assertions passed successfully!")


if __name__ == "__main__":
    main()
