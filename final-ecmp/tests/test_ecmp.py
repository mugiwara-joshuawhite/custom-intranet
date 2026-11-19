"""Packet tests for ECMP at switch s1. Given; do not edit.

The groups come from your routing_ecmp.ecmp_next_hops(), installed by
controller.py --only s1. h1 and h2 are on s1 (ports 1 and 2); h3 and h4 are
behind two equal-cost spines, s3 on port 3 and s4 on port 4.

What is tested, weeks 7 to 10 seen from a router: every packet of one TCP
connection takes one path (so it arrives in order), different connections
spread over both paths, and UDP flows are spread by their ports too.
"""

import collections

import ptf.testutils as tu
from ptf.base_tests import BaseTest
from scapy.all import IP, TCP, UDP, Ether

S1_PORT1_MAC, H1_MAC, H2_MAC = "08:00:00:00:01:00", "08:00:00:00:01:11", "08:00:00:00:02:22"
SPINES = (3, 4)


def flow(dst, sport, proto=TCP, dport=5201, ttl=64):
    return (Ether(src=H1_MAC, dst=S1_PORT1_MAC) / IP(src="10.0.1.1", dst=dst, ttl=ttl)
            / proto(sport=sport, dport=dport) / (b"x" * 20))


class EcmpTest(BaseTest):
    def setUp(self):
        BaseTest.setUp(self)
        self.dataplane = tu.ptf.dataplane_instance
        self.dataplane.flush()

    def port_of(self, pkt, what):
        tu.send_packet(self, 1, pkt)
        res = tu.dp_poll(self, timeout=2)
        if not isinstance(res, self.dataplane.PollSuccess):
            raise AssertionError(f"{what}: nothing left the switch. Usual causes: no ecmp_group "
                                 "entry for this destination (is ecmp_next_hops() returning it "
                                 "for s1?), a count of 0 in the group, or the ecmp_nhop lookup "
                                 "not applied after ecmp_group.")
        return res.port, Ether(res.packet)


class LocalHostOnePath(EcmpTest):
    """h2 is on s1 itself: a group of one, port 2."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        port, got = self.port_of(flow("10.0.2.2", 40000), "h1 to h2")
        if port != 2:
            raise AssertionError(f"h2 is on s1's port 2, a group of one next hop; "
                                 f"the packet left by port {port}")
        if got[IP].ttl != 63 or got.dst != H2_MAC or got.src != S1_PORT1_MAC:
            raise AssertionError(f"set_nhop should forward as part 1 did: "
                                 f"TTL 63 (got {got[IP].ttl}), "
                                 f"destination MAC {H2_MAC} (got {got.dst}), "
                                 f"source {S1_PORT1_MAC} (got {got.src})")


class RemoteHostOnASpine(EcmpTest):
    """h3 is two hops away by either spine, so every packet must leave by port 3 or 4."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        for sport in range(41000, 41008):
            port, _ = self.port_of(flow("10.0.3.3", sport), f"a flow to h3 from port {sport}")
            if port not in SPINES:
                raise AssertionError(f"a packet for h3 left by port {port}; "
                                     "only the spines, ports 3 and 4, lead to h3")


class OneFlowOnePath(EcmpTest):
    """Weeks 7 and 9: reordering looks like loss to TCP, so a connection stays on one path."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        ports = {self.port_of(flow("10.0.3.3", 42000), "one TCP flow to h3")[0]
                 for _ in range(8)}
        if len(ports) != 1:
            raise AssertionError(f"eight packets of one TCP connection left by ports "
                                 f"{sorted(ports)}; "
                                 "every packet of a flow must hash to the same path. Does the hash "
                                 "use only header fields that stay the same for the whole flow?")


class TcpFlowsSpread(EcmpTest):
    """Different connections should use both equal-cost paths."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        seen = collections.Counter(self.port_of(flow("10.0.3.3", s), "a TCP flow to h3")[0]
                                   for s in range(43000, 43016))
        if set(seen) != set(SPINES):
            raise AssertionError(f"16 TCP flows to h3 used ports {dict(seen)}; they should spread "
                                 "over both 3 and 4. Usual causes: the group's count is 1 (does "
                                 "ecmp_next_hops() list both spines?), or the hash leaves out the "
                                 "ports, so every flow from h1 to h3 hashes alike.")


class UdpFlowsSpread(EcmpTest):
    """UDP flows are spread by their ports too, the same as TCP flows."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        seen = collections.Counter(
            self.port_of(flow("10.0.3.3", s, proto=UDP), "a UDP flow to h3")[0]
            for s in range(44000, 44016))
        if set(seen) != set(SPINES):
            tcp = {self.port_of(flow("10.0.3.3", s), "a TCP flow to h3")[0]
                   for s in range(43000, 43016)}
            why = ("TCP flows do not spread either, so start with TcpFlowsSpread."
                   if len(tcp) < 2 else
                   "TCP flows do spread, so the ports reach the hash for TCP only: does the "
                   "parser extract the ports for UDP (protocol 17) as well as TCP (6)?")
            raise AssertionError(f"16 UDP flows to h3 used ports {dict(seen)}; "
                                 f"they should spread over both 3 and 4. {why}")
