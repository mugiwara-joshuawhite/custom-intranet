"""Send one UDP packet along a path you choose. Given.

Run on a host inside the network (make run, then at the mininet> prompt):

    h1 python3 send_route.py 10.0.3.3 "3 2 1" hello

"3 2 1" is the port to leave by at each switch in turn: out s1's port 3 to
s3, out s3's port 2 to s2, out s2's port 1 to h3. The packet goes to UDP port
4321 on the destination.

Scapy reference: https://scapy.readthedocs.io/
"""

import sys

from scapy.all import IP, UDP, Ether, Packet, bind_layers, get_if_hwaddr, get_if_list, sendp
from scapy.fields import BitField


class SourceRoute(Packet):
    fields_desc = [BitField("bos", 0, 1), BitField("port", 0, 15)]


bind_layers(Ether, SourceRoute, type=0x1234)
bind_layers(SourceRoute, SourceRoute, bos=0)
bind_layers(SourceRoute, IP, bos=1)


def main():
    if len(sys.argv) < 3:
        sys.exit('usage: send_route.py DEST_IP "PORT PORT ..." [MESSAGE]')
    dest, ports = sys.argv[1], [int(p) for p in sys.argv[2].split()]
    message = sys.argv[3] if len(sys.argv) > 3 else "source routed"
    iface = next(i for i in get_if_list() if i.endswith("eth0"))
    pkt = Ether(src=get_if_hwaddr(iface), dst="ff:ff:ff:ff:ff:ff")
    for i, port in enumerate(ports):
        pkt = pkt / SourceRoute(bos=int(i == len(ports) - 1), port=port)
    pkt = pkt / IP(dst=dest, ttl=64) / UDP(dport=4321, sport=1234) / message
    sendp(pkt, iface=iface, verbose=False)


if __name__ == "__main__":
    main()
