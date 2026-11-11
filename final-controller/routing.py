"""The controller (final option): compute every switch's forwarding table from the topology.

You write next_hops().

This is week 6's routing, run by a controller instead of by the routers: the
controller sees the whole topology, computes shortest paths, and installs the
result in each switch (controller.py does the installing). It uses only the
standard library, so you can test it on any computer:

    python3 routing.py                 # print the tables for ../topo/topology.json
    python3 routing.py --down s1-s3    # the same, with that link out of service

Reference: https://docs.python.org/3/library/collections.html#collections.deque
"""

import argparse
import json
from collections import deque  # noqa: F401  (for your breadth-first search)


def parse_links(topo):
    """[(a, a_port, b, b_port)] from topology.json. A host has no port number (None).

    "s1-p3" means switch s1, port 3; "h1" is a host.
    """
    out = []
    for left, right in topo["links"]:
        ends = []
        for end in (left, right):
            node, _, port = end.partition("-p")
            ends += [node, int(port) if port else None]
        out.append(tuple(ends))
    return out


def gateway_mac(host_ip):
    """The MAC a switch writes when forwarding toward another switch: the gateway
    MAC of the destination host's subnet, as topology.json sets up
    (10.0.N.x -> 08:00:00:00:0N:00)."""
    return "08:00:00:00:%02x:00" % int(host_ip.split(".")[2])


def next_hops(topo, down=()):
    """Every switch's forwarding decision for every host.

    Returns {switch: {host_ip: (mac, port)}}: to reach host_ip, the switch sends
    out `port`, with `mac` as the frame's destination. On the last switch the
    MAC is the host's own; before that it is gateway_mac(host_ip).

    Paths must be shortest in number of links. When two paths tie, go through
    the neighbor whose name sorts first (s3 before s4), so every run gives the
    same answer. `down` holds links to leave out, as "s1-s3" strings (either
    order).

    YOUR TASK. parse_links() and gateway_mac() are yours to use.
    """
    raise NotImplementedError("routing.next_hops")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topo", default="../topo/topology.json")
    ap.add_argument("--down", action="append", default=[], help="a link to leave out, like s1-s3")
    args = ap.parse_args()
    with open(args.topo) as f:
        tables = next_hops(json.load(f), args.down)
    for switch in sorted(tables):
        for ip, (mac, port) in sorted(tables[switch].items()):
            print(f"{switch}  {ip:<10} -> port {port}, MAC {mac}")


if __name__ == "__main__":
    main()
