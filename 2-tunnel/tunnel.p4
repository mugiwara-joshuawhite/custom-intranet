/* -*- P4_16 -*- */
/*
 * Part 2: a GRE tunnel endpoint in P4 (week 11). You complete each YOUR TASK.
 *
 * This switch is R1 from week 11's trace. Port 0 faces A's network
 * (10.1.0.0/24); port 1 faces the Internet. A packet from A to B's network
 * (10.2.0.0/16) goes into the tunnel: the switch wraps it in a GRE header and
 * an outer IPv4 header addressed 203.0.113.1 to 198.51.100.2, R2's address. A
 * GRE packet from R2 addressed to 203.0.113.1 comes out of the tunnel: the
 * switch removes both headers and forwards the inner packet to A.
 *
 * GRE: RFC 2784 (the header, section 2.1; IP protocol 47, section 4).
 * Language reference: https://p4.org/specifications/
 */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x0800;
const bit<8>  PROTO_GRE = 47;

typedef bit<9>  port_t;
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

/* RFC 2784 section 2.1, with no checksum: 4 bytes. */
header gre_t {
    bit<1>  checksumPresent;
    bit<12> reserved0;
    bit<3>  version;
    bit<16> protocolType;
}

struct metadata { }

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;        /* the only IPv4 header, or the outer one */
    gre_t      gre;
    ipv4_t     inner_ipv4;  /* the packet inside the tunnel */
}

parser MyParser(packet_in packet, out headers hdr, inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        /* YOUR TASK: week 11's rule, "the outer header names what is inside".
         * When the IPv4 protocol field is PROTO_GRE (47), go to parse_gre;
         * otherwise accept. Use transition select(hdr.ipv4.protocol). */
        transition accept;
    }
    state parse_gre {
        packet.extract(hdr.gre);
        transition select(hdr.gre.protocolType) {
            TYPE_IPV4: parse_inner_ipv4;
            default: accept;
        }
    }
    state parse_inner_ipv4 {
        packet.extract(hdr.inner_ipv4);
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

    /* Into the tunnel: the original packet becomes the inner packet. */
    action encap(ip4Addr_t local, ip4Addr_t remote, port_t port,
                 macAddr_t my_mac, macAddr_t next_hop_mac) {
        /* YOUR TASK: wrap the packet, as R1 did in week 11's trace.
         * 1. Copy the packet's IPv4 header into hdr.inner_ipv4, and lower the
         *    inner TTL by one: R1 forwards it one hop.
         * 2. Make hdr.gre valid: checksumPresent, reserved0 and version 0, and
         *    protocolType TYPE_IPV4 (what is inside).
         * 3. Turn hdr.ipv4 into the outer header: version 4, ihl 5, diffserv 0,
         *    totalLen = the inner totalLen + 24 (20 outer IPv4 + 4 GRE),
         *    identification 0, flags 2 (don't fragment), fragOffset 0, ttl 64,
         *    protocol PROTO_GRE, srcAddr local, dstAddr remote.
         * 4. Set the Ethernet source to my_mac and destination to next_hop_mac,
         *    and leave by `port` (standard_metadata.egress_spec). */
    }

    /* Out of the tunnel: the inner packet becomes the only packet. */
    action decap() {
        /* YOUR TASK: unwrap, as R2 did. Copy hdr.inner_ipv4 into hdr.ipv4 so
         * the inner packet becomes the only packet, then make hdr.inner_ipv4
         * and hdr.gre invalid (setInvalid) so the deparser does not emit them. */
    }

    action forward(port_t port, macAddr_t my_mac, macAddr_t host_mac) {
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;              /* R1 forwards it: one hop */
        hdr.ethernet.srcAddr = my_mac;
        hdr.ethernet.dstAddr = host_mac;
        standard_metadata.egress_spec = port;
    }

    /* Destinations through the tunnel (B's network). */
    table to_tunnel {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { encap; drop; }
        default_action = drop();
    }

    /* GRE packets addressed to this tunnel end. */
    table from_tunnel {
        key = { hdr.ipv4.dstAddr: exact; }
        actions = { decap; drop; }
        default_action = drop();
    }

    /* Hosts on A's network. */
    table lan {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { forward; drop; }
        default_action = drop();
    }

    apply {
        if (hdr.gre.isValid() && hdr.inner_ipv4.isValid()) {
            from_tunnel.apply();
            if (!hdr.gre.isValid()) {
                lan.apply();
            }
        } else if (hdr.ipv4.isValid()) {
            to_tunnel.apply();
        } else {
            drop();
        }
    }
}

control MyEgress(inout headers hdr, inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(hdr.ipv4.isValid(),
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv, hdr.ipv4.totalLen,
              hdr.ipv4.identification, hdr.ipv4.flags, hdr.ipv4.fragOffset, hdr.ipv4.ttl,
              hdr.ipv4.protocol, hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum, HashAlgorithm.csum16);
        update_checksum(hdr.inner_ipv4.isValid(),
            { hdr.inner_ipv4.version, hdr.inner_ipv4.ihl, hdr.inner_ipv4.diffserv,
              hdr.inner_ipv4.totalLen, hdr.inner_ipv4.identification, hdr.inner_ipv4.flags,
              hdr.inner_ipv4.fragOffset, hdr.inner_ipv4.ttl, hdr.inner_ipv4.protocol,
              hdr.inner_ipv4.srcAddr, hdr.inner_ipv4.dstAddr },
            hdr.inner_ipv4.hdrChecksum, HashAlgorithm.csum16);
    }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.gre);
        packet.emit(hdr.inner_ipv4);
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(),
         MyComputeChecksum(), MyDeparser()) main;
