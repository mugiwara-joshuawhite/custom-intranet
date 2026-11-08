"""Packet tests for the learning switch. Given; do not edit.

Each test sends frames into the switch and checks which ports they leave by,
the same behaviour week 4's switch showed: flood an unknown destination,
flood a broadcast such as an ARP request, forward a known destination out one
port only, and never send a frame back out the port it came in on.

Ports 0, 1 and 2 have hosts h1, h2 and h3 behind them.
"""

import time

import ptf.testutils as tu
from ptf.base_tests import BaseTest

H1, H2, H3 = "00:00:00:00:00:01", "00:00:00:00:00:02", "00:00:00:00:00:03"
BROADCAST = "ff:ff:ff:ff:ff:ff"
LEARN_WAIT = 1.0  # seconds for the controller to write a new MAC's entries


class SwitchTest(BaseTest):
    def setUp(self):
        BaseTest.setUp(self)
        self.dataplane = tu.ptf.dataplane_instance
        self.dataplane.flush()

    def expect(self, pkt, ports, concept, came_in=None):
        """The frame must leave by exactly these ports, and no others."""
        try:
            tu.verify_packets(self, pkt, ports)
        except AssertionError as exc:
            msg = str(exc)
            hint = ""
            if came_in is not None and f"port {came_in}" in msg and "not to receive" in msg:
                hint = (f" Port {came_in} is where the frame came in: a flood must not go back "
                        "out its arrival port (the egress task).")
            elif "not to receive" in msg and len(ports) == 1:
                hint = (" A known destination should leave by one port: forward() sets "
                        "egress_spec, not the flood group.")
            elif "was not received" in msg:
                hint = (" A frame is missing: does flood() set mcast_grp to FLOOD_GROUP, "
                        "and does apply() call both learned and mac_table?")
            first = msg.strip().splitlines()[0] if msg.strip() else ""
            raise AssertionError(
                f"{concept}: expected the frame on port(s) {ports} only. {first}{hint}") from None


class UnknownDestinationFloods(SwitchTest):
    """Week 4: a switch that has never seen the destination sends the frame everywhere else."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        pkt = tu.simple_eth_packet(eth_dst="00:00:00:00:00:99", eth_src=H1)
        tu.send_packet(self, 0, pkt)
        self.expect(pkt, [1, 2],
                    "an unknown destination is flooded to every port except the one it came in on",
                    came_in=0)


class BroadcastArpFloods(SwitchTest):
    """Week 4: an ARP request goes to the broadcast MAC, so every other host hears it."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        pkt = tu.simple_arp_packet(eth_dst=BROADCAST, eth_src=H3, arp_op=1,
                                   ip_snd="10.0.0.3", ip_tgt="10.0.0.1", hw_snd=H3)
        tu.send_packet(self, 2, pkt)
        self.expect(pkt, [0, 1], "a broadcast ARP request reaches every other port", came_in=2)


class KnownDestinationOnePort(SwitchTest):
    """Week 4: once h2 has sent a frame, frames for h2 leave only by h2's port."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        hello = tu.simple_eth_packet(eth_dst=BROADCAST, eth_src=H2)
        tu.send_packet(self, 1, hello)              # the switch learns h2 is on port 1
        self.expect(hello, [0, 2], "a broadcast from h2 is flooded", came_in=1)
        time.sleep(LEARN_WAIT)
        pkt = tu.simple_eth_packet(eth_dst=H2, eth_src=H1)
        tu.send_packet(self, 0, pkt)
        self.expect(pkt, [1], "after h2 is learned on port 1, a frame for h2 leaves by port 1 only")


class ArpReplyIsUnicast(SwitchTest):
    """Week 4: the ARP reply goes back to the asker only, learned from its request."""

    def runTest(self):  # noqa: N802 (PTF calls runTest)
        request = tu.simple_arp_packet(eth_dst=BROADCAST, eth_src=H1, arp_op=1,
                                       ip_snd="10.0.0.1", ip_tgt="10.0.0.3", hw_snd=H1)
        tu.send_packet(self, 0, request)
        self.expect(request, [1, 2], "the ARP request from h1 is flooded", came_in=0)
        time.sleep(LEARN_WAIT)
        reply = tu.simple_arp_packet(eth_dst=H1, eth_src=H3, arp_op=2,
                                     ip_snd="10.0.0.3", ip_tgt="10.0.0.1", hw_snd=H3, hw_tgt=H1)
        tu.send_packet(self, 2, reply)
        self.expect(reply, [0], "the ARP reply for h1 leaves by h1's port only")
