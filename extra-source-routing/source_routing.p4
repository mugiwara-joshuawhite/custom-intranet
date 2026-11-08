/* -*- P4_16 -*- */
/*
 * Part 4: source routing. You complete each YOUR TASK.
 *
 * In parts 1 to 3 the switches chose the path from their tables. Here the
 * sender chooses it: between the Ethernet and IPv4 headers it puts a stack of
 * source-route entries, one per switch, each naming the port to leave by.
 * Each switch reads the top entry, removes it, and sends the packet out that
 * port. The last entry has bos (bottom of stack) set; the switch that uses it
 * turns the packet back into plain IPv4 for the host. No tables, no
 * controller. SRv6 (week 15) is the same idea carried in an IPv6 extension
 * header.
 *
 *   Ethernet (type 0x1234) | srcRoute ... srcRoute (bos=1) | IPv4 | payload
 *
 * Structure after p4lang/tutorials exercises/source_routing (Apache-2.0; see
 * ../utils/NOTICE.md).
 */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;
const bit<16> TYPE_SRCROUTING = 0x1234;

#define MAX_HOPS 9

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header srcRoute_t {
    bit<1>  bos;
    bit<15> port;
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

struct metadata { }

struct headers {
    ethernet_t           ethernet;
    srcRoute_t[MAX_HOPS] srcRoutes;
    ipv4_t               ipv4;
}

parser MyParser(packet_in packet, out headers hdr, inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        /* YOUR TASK: after Ethernet, when the type is TYPE_SRCROUTING,
         * extract source-route entries one at a time until the one with bos
         * set, then extract IPv4. A header stack's .next and .last are the
         * P4 tools for this; the README links the spec section. */
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

    action srcRoute_nhop() {
        /* YOUR TASK: leave by the port the top entry names, and remove that entry. */
    }

    action srcRoute_finish() {
        /* YOUR TASK: this switch uses the last entry; the host expects plain IPv4. */
    }

    action update_ttl() {
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    apply {
        /* YOUR TASK: a packet with a source route goes where its top entry
         * says, finishing the route if that entry is the last, and its TTL
         * goes down by one. Anything else is dropped. */
        drop();
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
        /* YOUR TASK: Ethernet, whatever source-route entries remain, then IPv4. */
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(),
         MyComputeChecksum(), MyDeparser()) main;
