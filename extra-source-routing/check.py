"""Part 4 checks. Run `make check` inside the course container. Given; do not change it.

Each check sends one packet from h1 along a chosen path and watches where it
arrives, which spine link it crossed, and its TTL on arrival.
"""

import sys
import time

sys.path.insert(0, "../utils")
import checklib                               # noqa: E402

TOPO, JSON = "../topo/topology.json", "build/source_routing.json"


def send(net, dest_host, dest_ip, route):
    """What dest_host captured (tcpdump -v text) and s1's tx counts on ports 3 and 4."""
    d = net.get(dest_host)
    d.cmd("rm -f /tmp/cap.txt; tcpdump -l -v -n -i eth0 udp port 4321 > /tmp/cap.txt 2>/dev/null &")
    time.sleep(1)
    s1 = net.get("s1")
    def count(i):
        return int(s1.cmd(f"cat /sys/class/net/s1-eth{i}/statistics/tx_packets").strip() or 0)
    before = count(3), count(4)
    net.get("h1").cmd(f'python3 send_route.py {dest_ip} "{route}" check')
    time.sleep(1)
    d.cmd("kill %tcpdump")
    return d.cmd("cat /tmp/cap.txt"), (count(3) - before[0], count(4) - before[1])


def via(route, s1_sends, ttl):
    """s1_sends: packets s1 should send on (port 3, port 4) for this route."""
    def check(net):
        seen, sent = send(net, "h3", "10.0.3.3", route)
        if "4321" not in seen:
            return f'h3 did not receive the packet sent along "{route}"'
        if sent != s1_sends:
            return (f'"{route}" should make s1 send {s1_sends[0]} on port 3 '
                    f'and {s1_sends[1]} on port 4; it sent {sent[0]} and {sent[1]}')
        if f"ttl {ttl}," not in seen:
            return (f'"{route}" crosses {64 - ttl} switches, '
                    f'so the packet should arrive with TTL {ttl}: {seen.strip()[:160]}')
        return None
    return check


def other_host(net):
    seen, _ = send(net, "h4", "10.0.4.4", "3 2 2")
    return None if "4321" in seen else 'h4 did not receive the packet sent along "3 2 2"'


if __name__ == "__main__":
    ok = checklib.run_checks(TOPO, JSON, [
        ('"3 2 1" reaches h3 through s3', via("3 2 1", (1, 0), 61)),
        ('"4 1 1" reaches h3 through s4', via("4 1 1", (0, 1), 61)),
        ('the detour "3 1 4 1 1" still arrives, with the TTL it earned',
         via("3 1 4 1 1", (1, 1), 59)),
        ('"3 2 2" reaches h4 instead', other_host),
    ])
    sys.exit(0 if ok else 1)
