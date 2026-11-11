/* -*- P4_16 -*- */
/*
 * ECMP (final option). You complete each YOUR TASK.
 *
 * Part 1 sent every packet for a destination the same way. Here a switch with
 * several equally short paths spreads traffic across them, the way data-center
 * networks do: it hashes each packet's flow (addresses, protocol, ports) and
 * uses the hash to pick one next hop from the destination's group. Every
 * packet of a flow hashes the same, so a flow stays on one path and its
 * packets are not reordered.
 *
 *   ecmp_group  (IPv4 destination, LPM) -> set_ecmp_select(group, count)
 *   ecmp_nhop   (group, select, exact)  -> set_nhop(next-hop MAC, port)
 *
 * Structure after p4lang/tutorials exercises/load_balance (Apache-2.0; see
 * ../utils/NOTICE.md), extended to one group per destination.
 */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;
const bit<8>  PROTO_TCP = 6;
const bit<8>  PROTO_UDP = 17;

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

/* TCP and UDP both start with the two ports; that is all ECMP reads. */
header ports_t {
    bit<16> srcPort;
    bit<16> dstPort;
}

struct metadata {
    bit<16> ecmp_group;
    bit<16> ecmp_select;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    ports_t    ports;
}

parser MyParser(packet_in packet, out headers hdr, inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        /* YOUR TASK (from part 1): parse Ethernet, then IPv4. Then, for TCP
         * and UDP only, extract the ports. Other IPv4 traffic, such as ping,
         * has no ports and hashes on the addresses alone. */
        transition accept;
    }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control MyIngress(inout headers hdr, inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    action drop() {
        mark_to_drop(standard_metadata);
    }

    /* The controller gives each destination a group number and the number of
     * next hops in it. */
    action set_ecmp_select(bit<16> group, bit<16> count) {
        /* YOUR TASK: record the group, and set meta.ecmp_select to a hash of
         * the flow (source and destination address, protocol, both ports)
         * that falls between 0 and count - 1. v1model's hash() does this; see
         * the v1model.p4 reference linked in the README. */
    }

    /* The same forwarding as part 1's ipv4_forward. */
    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        /* YOUR TASK (from part 1). */
    }

    table ecmp_group {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { set_ecmp_select; drop; NoAction; }
        size = 1024;
        default_action = drop();
    }

    table ecmp_nhop {
        key = {
            meta.ecmp_group:  exact;
            meta.ecmp_select: exact;
        }
        actions = { set_nhop; drop; NoAction; }
        size = 1024;
        default_action = drop();
    }

    apply {
        /* YOUR TASK: for IPv4 packets, choose the group, then the next hop. */
        ecmp_group.apply();
        ecmp_nhop.apply();
    }
}

control MyEgress(inout headers hdr, inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv, hdr.ipv4.totalLen,
              hdr.ipv4.identification, hdr.ipv4.flags, hdr.ipv4.fragOffset,
              hdr.ipv4.ttl, hdr.ipv4.protocol, hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        /* YOUR TASK (from part 1, plus the ports). */
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(),
         MyComputeChecksum(), MyDeparser()) main;
