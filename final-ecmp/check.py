"""ECMP (final option) checks. Given; do not change it.

Run `make check` inside the course container.

Traffic from h1 to h3 can cross either spine: out s1's port 3 (to s3) or
port 4 (to s4). The checks count the packets on those two links while iperf3
runs, first with many flows at once, then with one.
"""

import json
import sys
import time

sys.path.insert(0, "../utils")
import checklib                               # noqa: E402
import controller                             # noqa: E402
import routing_ecmp                           # noqa: E402

HOSTS = {"h1": "10.0.1.1", "h2": "10.0.2.2", "h3": "10.0.3.3", "h4": "10.0.4.4"}
P4INFO, JSON, TOPO = "build/ecmp.p4.p4info.txt", "build/ecmp.json", "../topo/topology.json"


def tx(net, intf):
    return int(net.get("s1").cmd(f"cat /sys/class/net/{intf}/statistics/tx_packets").strip() or 0)


def spine_split(net, flows):
    """Packets s1 sent toward s3 and toward s4 while h1 ran `flows` TCP flows to h3."""
    h3 = net.get("h3")
    h3.cmd("iperf3 -s -D -1 -p 5201")
    time.sleep(0.5)
    before = tx(net, "s1-eth3"), tx(net, "s1-eth4")
    net.get("h1").cmd(f"iperf3 -c {HOSTS['h3']} -p 5201 -t 4 -P {flows} > /dev/null 2>&1")
    after = tx(net, "s1-eth3"), tx(net, "s1-eth4")
    return after[0] - before[0], after[1] - before[1]


def groups_shape(net):
    with open(TOPO) as f:
        groups = routing_ecmp.ecmp_next_hops(json.load(f))
    if [p for _, p in groups["s1"]["10.0.3.3"]] != [3, 4]:
        return "from s1 to h3 both spines are equally short: expected ports [3, 4]"
    if groups["s1"]["10.0.1.1"] != [("08:00:00:00:01:11", 1)]:
        return "to a host on the same switch there is one next hop, the host"
    if [p for _, p in groups["s3"]["10.0.3.3"]] != [2]:
        return "from s3 to h3 there is one shortest path, through s2 on port 2"
    return None


def all_pairs(net):
    missing = [f"{a}->{b}" for a in HOSTS for b, ip in HOSTS.items()
               if a != b and checklib.ping(net, a, ip, count=1)[0] == 0]
    return f"no reply for {', '.join(missing)}" if missing else None


def shortest(net):
    _, ttl = checklib.ping(net, "h1", HOSTS["h3"])
    return None if ttl == 61 else f"h1 to h3 should cross 3 switches (reply TTL 61), got TTL {ttl}"


def many_flows_spread(net):
    a, b = spine_split(net, 16)
    total = a + b
    if total < 100:
        return f"only {total} packets crossed the spines; is TCP getting through?"
    if min(a, b) < 0.15 * total:
        return f"16 flows put {a} packets on s3's link and {b} on s4's; ECMP should use both"
    return None


def one_flow_stays(net):
    a, b = spine_split(net, 1)
    total = a + b
    if total < 100:
        return f"only {total} packets crossed the spines; is TCP getting through?"
    if min(a, b) > 0.05 * total:
        return (f"one flow put {a} packets on s3's link and {b} on s4's; "
                "a flow should stay on one path")
    return None


if __name__ == "__main__":
    ok = checklib.run_checks(TOPO, JSON, [
        ("ecmp_next_hops() gives the expected groups", groups_shape),
        ("every host reaches every other host", all_pairs),
        ("paths are shortest", shortest),
        ("many flows use both spines", many_flows_spread),
        ("one flow stays on one path", one_flow_stays),
    ], before=lambda net: controller.install(TOPO, P4INFO, JSON))
    sys.exit(0 if ok else 1)
