"""Packet tests for the routing data plane (switch s1). Given; do not edit.

Each test checks one thing a router does to a packet, weeks 5 and 6: leave by
the port the table names, lower the TTL by one, rewrite both MAC addresses,
recompute the IPv4 checksum, drop what no entry matches, and let the longest
matching prefix win. A test names the job that went wrong.

s1's ports: 1 is h1 (10.0.1.1), 2 is h2 (10.0.2.2), 3 leads to spine s3, 4 to
spine s4. Entries: s1-runtime.json, plus 10.0.0.0/16 forwarding to port 3 and
10.0.3.0/24 dropping, beside the existing 10.0.3.3/32 (ptf-tables.json).
"""

import ptf.testutils as tu
from ptf.base_tests import BaseTest
from scapy.all import ICMP, IP, Ether

S1_PORT1_MAC = "08:00:00:00:01:00"   # h1's gateway: the MAC h1 addresses frames to
H1_MAC, H2_MAC = "08:00:00:00:01:11", "08:00:00:00:02:22"
S3_MAC = "08:00:00:00:03:00"


def from_h1(dst, ttl=64):
    return (Ether(src=H1_MAC, dst=S1_PORT1_MAC) / IP(src="10.0.1.1", dst=dst, ttl=ttl)
            / ICMP() / (b"x" * 20))


class RoutingTest(BaseTest):
    def setUp(self):
        BaseTest.setUp(self)
        self.dataplane = tu.ptf.dataplane_instance
        self.dataplane.flush()

    def one_packet_on(self, port, concept):
        """The packet that left by `port`, or a failure naming the concept."""
        res = tu.dp_poll(self, port_number=port, timeout=2)
        if not isinstance(res, self.dataplane.PollSuccess):
            other = tu.dp_poll(self, timeout=0.5)
            seen = (f" It left by port {other.port} instead." + (
                        " Port 0 is where a packet goes when nothing set egress_spec: the lookup"
                        " did not run, or ran without an IPv4 header to match (does the parser"
                        " extract IPv4?)."
                        if other.port == 0 else "")
                    if isinstance(other, self.dataplane.PollSuccess)
                    else " Nothing left the switch. Usual causes: the parser never extracts IPv4,"
                         " so the lookup has no address and the default (drop) applies; apply()"
                         " never calls the table; or the forward action never sets egress_spec.")
            raise AssertionError(f"{concept}: expected the packet on port {port}.{seen}")
        return Ether(res.packet)


class LeavesByTablePort(RoutingTest):
    """The entry for 10.0.2.2 says port 2."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        tu.send_packet(self, 1, from_h1("10.0.2.2"))
        self.one_packet_on(2, "the packet leaves by the port its table entry names "
                              "(ipv4_forward sets egress_spec)")


class TtlDropsByOne(RoutingTest):
    """Week 5: every router lowers the TTL by one."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        tu.send_packet(self, 1, from_h1("10.0.2.2", ttl=64))
        got = self.one_packet_on(2, "a forwarded packet")
        if got[IP].ttl != 63:
            raise AssertionError(
                f"the TTL should go from 64 to 63 at one router; it left with {got[IP].ttl}")


class MacsRewritten(RoutingTest):
    """Week 4 and 5: a router sends a new frame, from itself to the next hop."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        tu.send_packet(self, 1, from_h1("10.0.2.2"))
        got = self.one_packet_on(2, "a forwarded packet")
        problems = []
        if got.dst != H2_MAC:
            problems.append(f"destination MAC should be the next hop's, {H2_MAC}; it was {got.dst}")
        if got.src != S1_PORT1_MAC:
            problems.append(f"source MAC should be the address the frame was sent to, "
                            f"{S1_PORT1_MAC}; it was {got.src}")
        if problems:
            raise AssertionError("; ".join(problems))


class ChecksumRecomputed(RoutingTest):
    """Week 3 and 5: changing the TTL changes the header, so its checksum must change too."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        tu.send_packet(self, 1, from_h1("10.0.2.2"))
        got = self.one_packet_on(2, "a forwarded packet")
        sent = got[IP].chksum
        del got[IP].chksum
        right = IP(bytes(got[IP])).chksum
        if sent != right:
            raise AssertionError(f"the IPv4 checksum is {sent:#06x} but this header needs "
                                 f"{right:#06x}: is the header emitted with the TTL change, "
                                 "and is the checksum block reached?")


class NoEntryDropped(RoutingTest):
    """No entry matches 10.1.0.1, so the default action, drop, applies."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        tu.send_packet(self, 1, from_h1("10.1.0.1"))
        res = tu.dp_poll(self, timeout=1)
        if isinstance(res, self.dataplane.PollSuccess):
            raise AssertionError(
                f"a destination with no entry should be dropped; it left by port {res.port}")


class LongestPrefixWins(RoutingTest):
    """Week 5: /32 beats /24, /24 beats /16, and /16 applies where nothing longer matches."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        tu.send_packet(self, 1, from_h1("10.0.3.3"))
        self.one_packet_on(3, "10.0.3.3 matches /32 (forward), /24 (drop) and /16; "
                              "the /32 is longest and should win")
        tu.send_packet(self, 1, from_h1("10.0.3.99"))
        res = tu.dp_poll(self, timeout=1)
        if isinstance(res, self.dataplane.PollSuccess):
            raise AssertionError(f"10.0.3.99 matches /24 (drop) and /16 (forward); "
                                 f"the /24 is longer and should drop it, "
                                 f"but it left by port {res.port}")
        tu.send_packet(self, 1, from_h1("10.0.9.99"))
        self.one_packet_on(3, "10.0.9.99 matches only 10.0.0.0/16, which forwards to port 3")
