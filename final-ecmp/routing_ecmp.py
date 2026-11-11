"""ECMP (final option): every equally short next hop, not just one. You write ecmp_next_hops().

Builds on your controller's routing.py (imported below): the same topology, the same
MACs, and the same shortest-path idea. The difference is that when two
neighbors are equally close to a host, the switch keeps both.

    python3 routing_ecmp.py            # print the groups for ../topo/topology.json
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "final-controller"))
import routing  # noqa: E402, F401  (your controller code, for your ecmp_next_hops)


def ecmp_next_hops(topo, down=()):
    """{switch: {host_ip: [(mac, port), ...]}}, every first hop on a shortest path.

    The list is sorted by port. On the host's own switch it has one entry, the
    host itself. routing.parse_links() and routing.gateway_mac() are yours to use.

    YOUR TASK.
    """
    raise NotImplementedError("routing_ecmp.ecmp_next_hops")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "topo", "topology.json")) as f:
        groups = ecmp_next_hops(json.load(f))
    for switch in sorted(groups):
        for ip, hops in sorted(groups[switch].items()):
            print(f"{switch}  {ip:<10} -> " + ", ".join(f"port {p} ({m})" for m, p in hops))
