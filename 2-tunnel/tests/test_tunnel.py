"""Packet tests for the GRE tunnel endpoint. Given; do not edit.

The numbers are week 11's trace. This switch is R1: port 0 faces A
(10.1.0.5), port 1 faces the Internet. B (10.2.0.9) sits behind R2, the far
tunnel end at 198.51.100.2.

Fields a tunnel end may choose for itself (the outer IP identification and
flags, and the checksums that depend on them) are not compared, so the same
tests pass for this switch and for a Linux GRE tunnel.
"""

import ptf.testutils as tu
from ptf.base_tests import BaseTest
from ptf.mask import Mask
from scapy.all import GRE, ICMP, IP, Ether, NoPayload

A_MAC, R1_LAN_MAC = "00:00:00:00:00:05", "00:00:00:00:01:00"
R1_WAN_MAC, X_MAC = "00:00:00:00:02:00", "00:00:00:00:02:fe"
A, B = "10.1.0.5", "10.2.0.9"
R1, R2 = "203.0.113.1", "198.51.100.2"


def inner(src, dst, ttl):
    return (IP(src=src, dst=dst, ttl=ttl, id=7) / ICMP(type=8, id=1, seq=1)
            / (b"week 11 trace" * 4))


def loose(pkt):
    """Compare everything a reader would check, not the fields a tunnel end may choose."""
    m = Mask(pkt)
    m.set_do_not_care_scapy(IP, "id")
    m.set_do_not_care_scapy(IP, "flags")
    m.set_do_not_care_scapy(IP, "chksum")
    return m


def headers(raw):
    """The fields a reader checks, header by header: [(label, value), ...]."""
    out, layer, n = [], Ether(raw), 0
    out.append(("frame length", len(raw)))
    while layer and not isinstance(layer, NoPayload):
        if isinstance(layer, IP):
            n += 1
            which = ("outer IPv4" if n == 1 and layer.haslayer(GRE)
                     else ("inner IPv4" if n == 2 else "IPv4"))
            out += [(f"{which} {f}", getattr(layer, f))
                    for f in ("src", "dst", "ttl", "proto", "len")]
        elif isinstance(layer, GRE):
            out += [("GRE header", "present"), ("GRE protocol type", hex(layer.proto))]
        layer = layer.payload
    if not any(label == "GRE header" for label, _ in out):
        out.append(("GRE header", "absent"))
    return out


class TunnelTest(BaseTest):
    def setUp(self):
        BaseTest.setUp(self)
        self.dataplane = tu.ptf.dataplane_instance
        self.dataplane.flush()

    def expect(self, want, port, concept):
        """`want` is a Mask; the packet must arrive on `port` and match it."""
        res = tu.dp_poll(self, port_number=port, timeout=2)
        if not isinstance(res, self.dataplane.PollSuccess):
            other = tu.dp_poll(self, timeout=0.5)
            where = (f"it left by port {other.port} instead"
                     if isinstance(other, self.dataplane.PollSuccess)
                     else "nothing left the switch: did the parser reach the headers this "
                          "table needs, and did a table entry match?")
            raise AssertionError(f"{concept}. No packet on port {port}; {where}.")
        if not want.pkt_match(res.packet):
            expected, got = dict(headers(bytes(want.exp_pkt))), dict(headers(res.packet))
            diffs = [f"{k}: expected {expected.get(k)}, got {got.get(k)}"
                     for k in list(expected) + [k for k in got if k not in expected]
                     if expected.get(k) != got.get(k)]
            extra = (got.get("frame length") or 0) - (expected.get("frame length") or 0)
            clue = {4: " 4 extra bytes is one GRE header: is hdr.gre still valid when the packet"
                       " leaves?",
                    20: " 20 extra bytes is one IPv4 header: is the outer header still valid when"
                        " the packet leaves?",
                    24: " 24 extra bytes is the whole wrapper, outer IPv4 and GRE: did decap run?",
                    -24: " 24 missing bytes is the whole wrapper: did encap make hdr.gre valid and"
                         " fill the outer header?"}.get(extra, "")
            if "outer IPv4 len" in " ".join(diffs):
                clue += (" The outer totalLen must count the inner packet plus 24"
                         " (20 outer IPv4 + 4 GRE).")
            if "inner IPv4 ttl" in " ".join(diffs) or "IPv4 ttl" in " ".join(diffs):
                clue += (" Each tunnel end forwards the inner packet one hop, so it lowers the"
                         " inner TTL by one.")
            raise AssertionError(f"{concept}. The packet on port {port} differs: "
                                 + "; ".join(diffs[:5]) + "." + clue)
        tu.verify_no_other_packets(self)


class IntoTheTunnel(TunnelTest):
    """A to B: R1 wraps the packet.

    Outer 203.0.113.1 to 198.51.100.2, protocol 47, GRE carrying IPv4."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        sent = Ether(src=A_MAC, dst=R1_LAN_MAC) / inner(A, B, 64)
        tu.send_packet(self, 0, sent)
        want = (Ether(src=R1_WAN_MAC, dst=X_MAC) / IP(src=R1, dst=R2, ttl=64, proto=47)
                / GRE(proto=0x0800) / inner(A, B, 63))
        self.expect(loose(want), 1,
                    "a packet for B's network leaves port 1 inside GRE: outer 203.0.113.1 "
                    "to 198.51.100.2, protocol 47, GRE type 0x0800, and the inner packet "
                    "unchanged except its TTL, 64 to 63")


class OuterHeaderOnly(TunnelTest):
    """The middle of the path reads only the outer header: 24 bytes more, 20 IP and 4 GRE."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        sent = Ether(src=A_MAC, dst=R1_LAN_MAC) / inner(A, B, 64)
        tu.send_packet(self, 0, sent)
        result = tu.dp_poll(self, port_number=1, timeout=2)
        if not isinstance(result, self.dataplane.PollSuccess):
            raise AssertionError("nothing left port 1, so there is no tunnel packet to measure")
        grew = len(result.packet) - len(bytes(sent))
        if grew != 24:
            raise AssertionError(
                f"the tunnel should add 24 bytes (20 outer IPv4 + 4 GRE); it added {grew}")


class OutOfTheTunnel(TunnelTest):
    """B's reply arrives at R1 inside GRE.

    R1 removes both headers and forwards the inner packet to A."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        sent = (Ether(src=X_MAC, dst=R1_WAN_MAC) / IP(src=R2, dst=R1, ttl=62, proto=47)
                / GRE(proto=0x0800) / inner(B, A, 63))
        tu.send_packet(self, 1, sent)
        want = Ether(src=R1_LAN_MAC, dst=A_MAC) / inner(B, A, 62)
        self.expect(loose(want), 0,
                    "a GRE packet for 203.0.113.1 leaves port 0 as the inner packet alone, "
                    "no outer header and no GRE, with its TTL lowered once, 63 to 62")
