/* -*- P4_16 -*- */
/*
 * Part 1: IPv4 forwarding in P4. You complete each YOUR TASK.
 *
 * The switch parses Ethernet and IPv4, looks up the destination address in
 * ipv4_lpm (longest-prefix match), and forwards the packet out the port the
 * table entry names, the way a router's forwarding table does. The table's
 * entries come from s1-runtime.json to s4-runtime.json in this part; in the final
 * option your own controller installs them.
 *
 * Structure after p4lang/tutorials exercises/basic (Apache-2.0; see
 * ../utils/NOTICE.md). Language reference: https://p4.org/specifications/
 */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;

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

struct metadata { }

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
}

parser MyParser(packet_in packet, out headers hdr, inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        /* YOUR TASK: extract the Ethernet header, then move to a state that
         * extracts IPv4 when the EtherType says the payload is IPv4. Any
         * other frame is accepted with only Ethernet parsed. */
         packet.extract(hdr.ethernet);  // Extract ethernet header
         transition select(hdr.ethernet.etherType) {    // move to state that extracts on ethertype
            TYPE_IPV4: ext_ipv4;
            default: accept;    // why
        }
    }

    state ext_ipv4 {
        packet.extract(hdr.ipv4);
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

    /* The table entry supplies dstAddr (the next hop's MAC) and port. */
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        /* YOUR TASK: send the packet out `port`; the frame's new source is
         * the MAC it was addressed to, and its new destination is the next
         * hop's; and do what every router does to the TTL. */
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ipv4_lpm {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { ipv4_forward; drop; NoAction; }
        size = 1024;
        default_action = drop();
    }

    apply {
        /* YOUR TASK: this looks up every packet, including ones with no IPv4
         * header to match on. Look up only packets that have one. */
        ipv4_lpm.apply();
    }
}

control MyEgress(inout headers hdr, inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

/* Changing the TTL changes the IPv4 header, so its checksum is recomputed here. */
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
        /* YOUR TASK: put the headers back on the packet, outermost first. */
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(),
         MyComputeChecksum(), MyDeparser()) main;
