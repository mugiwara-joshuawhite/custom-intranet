"""Part 2 checks. Run `make check` inside the course container. Given; do not change it.

The switches start with empty tables; the checks run your controller, then
test the network it built, then take a link down and run it again.
"""

import json
import sys

sys.path.insert(0, "../utils")
import checklib                               # noqa: E402
import controller                             # noqa: E402
import routing                                # noqa: E402

HOSTS = {"h1": "10.0.1.1", "h2": "10.0.2.2", "h3": "10.0.3.3", "h4": "10.0.4.4"}
P4INFO, JSON = "build/forwarding.p4.p4info.txt", "build/forwarding.json"
TOPO = "../topo/topology.json"


def unreachable(net):
    return [f"{a}->{b}" for a in HOSTS for b, ip in HOSTS.items()
            if a != b and checklib.ping(net, a, ip, count=1)[0] == 0]


def all_pairs(net):
    missing = unreachable(net)
    return f"no reply for {', '.join(missing)}" if missing else None


def shortest(net):
    _, ttl = checklib.ping(net, "h1", HOSTS["h3"])
    return None if ttl == 61 else f"h1 to h3 should cross 3 switches (reply TTL 61), got TTL {ttl}"


def table_shape(net):
    with open(TOPO) as f:
        tables = routing.next_hops(json.load(f))
    if sorted(tables) != ["s1", "s2", "s3", "s4"] or any(len(t) != 4 for t in tables.values()):
        return "next_hops() should give each of s1 to s4 one entry for each of the 4 hosts"
    if tables["s1"]["10.0.3.3"][1] != 3:
        return "from s1 to h3, both spines tie; the tie goes to s3, which is s1's port 3"
    if tables["s1"]["10.0.1.1"] != ("08:00:00:00:01:11", 1):
        return "on the last switch, the MAC is the host's own and the port is the host's"
    return None


def cut(net, a, b, broken):
    """Make the a-b link lose every packet, or carry them again.

    The interfaces stay up, as with a cut cable: bmv2 stops forwarding on every
    port if one of its interfaces is taken down.
    """
    for node, peer in ((a, b), (b, a)):
        for intf in net.get(node).connectionsTo(net.get(peer))[0][:1]:
            if broken:
                net.get(node).cmd(f"tc qdisc replace dev {intf.name} root netem loss 100%")
            else:
                net.get(node).cmd(f"tc qdisc del dev {intf.name} root")


def reroutes(net):
    cut(net, "s1", "s3", True)
    try:
        if not unreachable(net):
            return ("the network still worked with s1-s3 cut, before rerouting; "
                    "the check itself is broken")
        controller.install(TOPO, P4INFO, JSON, down=["s1-s3"])
        missing = unreachable(net)
        if missing:
            return ("after s1-s3 was cut and the controller ran again: "
                    f"no reply for {', '.join(missing)}")
        return None
    finally:
        cut(net, "s1", "s3", False)


if __name__ == "__main__":
    ok = checklib.run_checks(TOPO, JSON, [
        ("next_hops() gives the expected tables", table_shape),
        ("every host reaches every other host", all_pairs),
        ("paths are shortest", shortest),
        ("the controller routes around a failed link", reroutes),
    ], before=lambda net: controller.install(TOPO, P4INFO, JSON))
    sys.exit(0 if ok else 1)
