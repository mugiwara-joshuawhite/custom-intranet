"""Part 1 checks, given. Run make check in the course container; do not edit."""

# Imports come from the course image and ../utils, not the host Python environment.
# pyright: reportMissingImports=false

import sys

sys.path.insert(0, "../utils")
import checklib  # noqa: E402
import p4runtime_lib.bmv2  # noqa: E402
import p4runtime_lib.helper  # noqa: E402
from p4runtime_lib.switch import ShutdownAllSwitchConnections  # noqa: E402

HOSTS = {"h1": "10.0.1.1", "h2": "10.0.2.2", "h3": "10.0.3.3", "h4": "10.0.4.4"}


def every_host_reaches_every_other(net):
    missing = [
        f"{a}->{b}"
        for a in HOSTS
        for b, ip in HOSTS.items()
        if a != b and checklib.ping(net, a, ip, count=1)[0] == 0
    ]
    return f"no reply for {', '.join(missing)}" if missing else None


def ttl_drops_once_per_switch(net):
    _, same_switch = checklib.ping(net, "h1", HOSTS["h2"])
    _, across = checklib.ping(net, "h1", HOSTS["h3"])
    if (same_switch, across) != (63, 61):
        return (
            f"reply TTLs were {same_switch} (h1 to h2, one switch) and {across} "
            "(h1 to h3, three switches); expected 63 and 61, starting at 64"
        )
    return None


def unknown_destination_dropped(net):
    received, _ = checklib.ping(net, "h1", "10.0.9.9", count=1)
    return (
        "a packet to 10.0.9.9, which no table entry matches, got a reply"
        if received
        else None
    )


def overlapping_prefixes_choose_longest(net):
    """Prove /32 beats /24, and /24 beats /16, on reachable destinations."""
    helper = p4runtime_lib.helper.P4InfoHelper("build/forwarding.p4.p4info.txt")
    connections = {}

    def insert(switch, address, prefix, action, params=None):
        if switch not in connections:
            device = int(switch[1:]) - 1
            sw = p4runtime_lib.bmv2.Bmv2SwitchConnection(
                name=switch, address=f"127.0.0.1:{50051 + device}", device_id=device
            )
            sw.MasterArbitrationUpdate()
            connections[switch] = sw
        connections[switch].WriteTableEntry(
            helper.buildTableEntry(
                table_name="MyIngress.ipv4_lpm",
                match_fields={"hdr.ipv4.dstAddr": (address, prefix)},
                action_name=f"MyIngress.{action}",
                action_params=params or {},
            )
        )

    aliases = ("10.0.3.99", "10.0.9.99")
    host = net.get("h3")
    interface = str(host.defaultIntf())
    try:
        # Both addresses live on h3; downstream /32 routes make them reachable.
        for address in aliases:
            output = host.cmd(f"ip addr add {address}/32 dev {interface}")
            if output.strip():
                return f"could not add probe address {address}: {output.strip()}"
            insert(
                "s3",
                address,
                32,
                "ipv4_forward",
                {"dstAddr": "08:00:00:00:03:00", "port": 2},
            )
            insert(
                "s2",
                address,
                32,
                "ipv4_forward",
                {"dstAddr": "08:00:00:00:03:33", "port": 1},
            )
        insert(
            "s1",
            "10.0.0.0",
            16,
            "ipv4_forward",
            {"dstAddr": "08:00:00:00:03:00", "port": 3},
        )
        for address in aliases:
            if checklib.ping(net, "h1", address, count=1)[0] == 0:
                return f"probe {address} was not reachable before adding /24 drop"

        insert("s1", "10.0.3.0", 24, "drop")
        probes = (
            ("10.0.3.3", True, "/32 forwarding beats /24 drop"),
            ("10.0.3.99", False, "/24 drop beats /16 forwarding"),
            ("10.0.9.99", True, "/16 forwarding applies outside the /24"),
        )
        for address, should_reply, reason in probes:
            received, _ = checklib.ping(net, "h1", address, count=1)
            print(
                f"  LPM {address}: {received} replies; "
                f"expected {int(should_reply)} ({reason})"
            )
            if bool(received) != should_reply:
                return f"wrong result for {address}: {reason}"
        return None
    finally:
        for address in aliases:
            host.cmd(f"ip addr del {address}/32 dev {interface}")
        ShutdownAllSwitchConnections()


if __name__ == "__main__":
    ok = checklib.run_checks(
        "topology.json",
        "build/forwarding.json",
        [
            ("every host reaches every other host", every_host_reaches_every_other),
            ("TTL goes down by one at each switch", ttl_drops_once_per_switch),
            ("a destination with no entry is dropped", unknown_destination_dropped),
            (
                "overlapping prefixes choose the longest match",
                overlapping_prefixes_choose_longest,
            ),
        ],
    )
    sys.exit(0 if ok else 1)
