"""
Day 42: DHCP Binary Packet Codec & Options TLV Parser
100% pure Python standard library implementation of RFC 2131 / RFC 2132 binary
DHCP/BOOTP packet framing, magic cookie validation, and TLV option encoding/decoding.
"""

from dataclasses import dataclass, field
import struct
from typing import Any, Dict, List, Optional, Tuple

DHCP_MAGIC_COOKIE = b"\x63\x82\x53\x63"
BOOTREQUEST = 1
BOOTREPLY = 2


@dataclass
class ParsedDHCPPacket:
    op: int
    htype: int
    hlen: int
    hops: int
    xid: int
    secs: int
    flags: int
    ciaddr: str
    yiaddr: str
    siaddr: str
    giaddr: str
    chaddr: bytes
    sname: str
    file: str
    options: Dict[int, Any] = field(default_factory=dict)


class DHCPOptionsTLVCodec:
    """Encodes and decodes RFC 2132 Type-Length-Value (TLV) DHCP options."""

    PAD = 0
    SUBNET_MASK = 1
    ROUTER = 3
    DNS_SERVERS = 6
    HOST_NAME = 12
    DOMAIN_NAME = 15
    INTERFACE_MTU = 26
    LEASE_TIME = 51
    MESSAGE_TYPE = 53
    SERVER_IDENTIFIER = 54
    PARAMETER_REQUEST_LIST = 55
    END = 255

    @staticmethod
    def encode_ip(ip_str: str) -> bytes:
        return bytes(int(x) for x in ip_str.split("."))

    @staticmethod
    def decode_ip(data: bytes) -> str:
        return ".".join(str(b) for b in data)

    @classmethod
    def encode_options(cls, options: Dict[int, Any]) -> bytes:
        out = bytearray()
        for tag, val in options.items():
            if tag == cls.PAD:
                out.append(cls.PAD)
            elif tag == cls.END:
                continue
            elif tag == cls.MESSAGE_TYPE:
                out.extend(struct.pack("!BBB", tag, 1, val))
            elif tag in (cls.SUBNET_MASK, cls.ROUTER, cls.SERVER_IDENTIFIER):
                ip_bytes = cls.encode_ip(val)
                out.extend(struct.pack("!BB", tag, len(ip_bytes)) + ip_bytes)
            elif tag == cls.DNS_SERVERS:
                ip_bytes = b"".join(cls.encode_ip(ip) for ip in val)
                out.extend(struct.pack("!BB", tag, len(ip_bytes)) + ip_bytes)
            elif tag in (cls.HOST_NAME, cls.DOMAIN_NAME):
                raw = val.encode("ascii")
                out.extend(struct.pack("!BB", tag, len(raw)) + raw)
            elif tag in (cls.LEASE_TIME,):
                out.extend(struct.pack("!BBI", tag, 4, val))
            elif tag == cls.INTERFACE_MTU:
                out.extend(struct.pack("!BBH", tag, 2, val))
            elif tag == cls.PARAMETER_REQUEST_LIST:
                out.extend(struct.pack("!BB", tag, len(val)) + bytes(val))
            else:
                raw_bytes = val if isinstance(val, (bytes, bytearray)) else bytes(val)
                out.extend(struct.pack("!BB", tag, len(raw_bytes)) + raw_bytes)

        out.append(cls.END)
        return bytes(out)

    @classmethod
    def decode_options(cls, payload: bytes) -> Dict[int, Any]:
        options: Dict[int, Any] = {}
        idx = 0
        while idx < len(payload):
            tag = payload[idx]
            if tag == cls.PAD:
                idx += 1
                continue
            if tag == cls.END:
                break

            if idx + 1 >= len(payload):
                raise ValueError("Truncated option length field")
            length = payload[idx + 1]
            val_start = idx + 2
            val_end = val_start + length
            if val_end > len(payload):
                raise ValueError(f"Option {tag} length {length} overflows payload")

            val_bytes = payload[val_start:val_end]
            idx = val_end

            if tag == cls.MESSAGE_TYPE:
                options[tag] = struct.unpack("!B", val_bytes)[0]
            elif tag in (cls.SUBNET_MASK, cls.ROUTER, cls.SERVER_IDENTIFIER):
                options[tag] = cls.decode_ip(val_bytes)
            elif tag == cls.DNS_SERVERS:
                options[tag] = [cls.decode_ip(val_bytes[i:i+4]) for i in range(0, len(val_bytes), 4)]
            elif tag in (cls.HOST_NAME, cls.DOMAIN_NAME):
                options[tag] = val_bytes.decode("ascii", errors="replace")
            elif tag == cls.LEASE_TIME:
                options[tag] = struct.unpack("!I", val_bytes)[0]
            elif tag == cls.INTERFACE_MTU:
                options[tag] = struct.unpack("!H", val_bytes)[0]
            elif tag == cls.PARAMETER_REQUEST_LIST:
                options[tag] = list(val_bytes)
            else:
                options[tag] = val_bytes

        return options


class DHCPPacketCodec:
    """Serializes and deserializes the full 236-byte BOOTP header + Magic Cookie + Options."""

    BOOTP_HEADER_FORMAT = "!BBBBIHH4s4s4s4s16s64s128s"
    BOOTP_HEADER_SIZE = 236

    @classmethod
    def encode(cls, pkt: ParsedDHCPPacket) -> bytes:
        def ip_bytes(ip: str) -> bytes:
            return bytes(int(x) for x in ip.split("."))

        chaddr_padded = pkt.chaddr.ljust(16, b"\x00")
        sname_padded = pkt.sname.encode("ascii").ljust(64, b"\x00")
        file_padded = pkt.file.encode("ascii").ljust(128, b"\x00")

        header = struct.pack(
            cls.BOOTP_HEADER_FORMAT,
            pkt.op, pkt.htype, pkt.hlen, pkt.hops,
            pkt.xid, pkt.secs, pkt.flags,
            ip_bytes(pkt.ciaddr), ip_bytes(pkt.yiaddr),
            ip_bytes(pkt.siaddr), ip_bytes(pkt.giaddr),
            chaddr_padded, sname_padded, file_padded
        )

        options_bytes = DHCPOptionsTLVCodec.encode_options(pkt.options)
        return header + DHCP_MAGIC_COOKIE + options_bytes

    @classmethod
    def decode(cls, raw: bytes) -> ParsedDHCPPacket:
        if len(raw) < cls.BOOTP_HEADER_SIZE + 4:
            raise ValueError(f"Packet too short: {len(raw)} bytes")

        header_bytes = raw[:cls.BOOTP_HEADER_SIZE]
        cookie = raw[cls.BOOTP_HEADER_SIZE:cls.BOOTP_HEADER_SIZE + 4]
        if cookie != DHCP_MAGIC_COOKIE:
            raise ValueError(f"Invalid DHCP magic cookie: {cookie.hex()}")

        unpacked = struct.unpack(cls.BOOTP_HEADER_FORMAT, header_bytes)
        op, htype, hlen, hops, xid, secs, flags = unpacked[0:7]
        ciaddr = ".".join(str(b) for b in unpacked[7])
        yiaddr = ".".join(str(b) for b in unpacked[8])
        siaddr = ".".join(str(b) for b in unpacked[9])
        giaddr = ".".join(str(b) for b in unpacked[10])
        chaddr = unpacked[11][:hlen]
        sname = unpacked[12].rstrip(b"\x00").decode("ascii", errors="replace")
        file_name = unpacked[13].rstrip(b"\x00").decode("ascii", errors="replace")

        options_raw = raw[cls.BOOTP_HEADER_SIZE + 4:]
        options = DHCPOptionsTLVCodec.decode_options(options_raw)

        return ParsedDHCPPacket(
            op=op, htype=htype, hlen=hlen, hops=hops,
            xid=xid, secs=secs, flags=flags,
            ciaddr=ciaddr, yiaddr=yiaddr, siaddr=siaddr, giaddr=giaddr,
            chaddr=chaddr, sname=sname, file=file_name,
            options=options
        )


def main():
    print("=== Day 42: DHCP Binary Packet Codec & Options TLV Parser ===")

    mac_raw = bytes.fromhex("525400123456")
    original_pkt = ParsedDHCPPacket(
        op=BOOTREQUEST,
        htype=1,
        hlen=6,
        hops=0,
        xid=0x12345678,
        secs=10,
        flags=0x8000,
        ciaddr="0.0.0.0",
        yiaddr="0.0.0.0",
        siaddr="0.0.0.0",
        giaddr="0.0.0.0",
        chaddr=mac_raw,
        sname="",
        file="",
        options={
            53: 1,
            12: "dev-server-01",
            55: [1, 3, 6, 15, 26],
            26: 1500
        }
    )

    encoded = DHCPPacketCodec.encode(original_pkt)
    print(f"[*] Serialized DHCPDISCOVER packet length: {len(encoded)} bytes")
    assert len(encoded) >= 240
    assert encoded[236:240] == DHCP_MAGIC_COOKIE

    decoded = DHCPPacketCodec.decode(encoded)
    assert decoded.op == BOOTREQUEST
    assert decoded.xid == 0x12345678
    assert decoded.flags == 0x8000
    assert decoded.chaddr == mac_raw
    assert decoded.options[53] == 1
    assert decoded.options[12] == "dev-server-01"
    assert decoded.options[55] == [1, 3, 6, 15, 26]
    assert decoded.options[26] == 1500
    print("[*] Successfully decoded and asserted binary field equality!")

    offer_pkt = ParsedDHCPPacket(
        op=BOOTREPLY,
        htype=1,
        hlen=6,
        hops=0,
        xid=0x12345678,
        secs=0,
        flags=0x0000,
        ciaddr="0.0.0.0",
        yiaddr="192.168.1.50",
        siaddr="192.168.1.1",
        giaddr="0.0.0.0",
        chaddr=mac_raw,
        sname="tftp.lan",
        file="pxelinux.0",
        options={
            53: 2,
            1: "255.255.255.0",
            3: "192.168.1.1",
            6: ["1.1.1.1", "8.8.8.8"],
            15: "internal.corp",
            51: 86400,
            54: "192.168.1.1"
        }
    )

    encoded_offer = DHCPPacketCodec.encode(offer_pkt)
    decoded_offer = DHCPPacketCodec.decode(encoded_offer)
    assert decoded_offer.yiaddr == "192.168.1.50"
    assert decoded_offer.options[1] == "255.255.255.0"
    assert decoded_offer.options[6] == ["1.1.1.1", "8.8.8.8"]
    assert decoded_offer.options[51] == 86400
    assert decoded_offer.sname == "tftp.lan"
    assert decoded_offer.file == "pxelinux.0"

    print(f"[*] Decoded DHCPOFFER: {decoded_offer.yiaddr}, DNS: {decoded_offer.options[6]}, Lease: {decoded_offer.options[51]}s")
    print("All DHCP Binary Codec & TLV Parser assertions passed successfully!")


if __name__ == "__main__":
    main()
