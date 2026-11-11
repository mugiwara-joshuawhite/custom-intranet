/* -*- P4_16 -*- */
/*
 * Part 2: a learning Ethernet switch in P4 (week 4). You complete each YOUR TASK.
 *
 * The switch does what the week 4 switch did: it forwards a frame out the
 * port where its destination MAC was last seen, and floods it to every other
 * port when the destination is unknown or the frame is a broadcast, such as
 * an ARP request. The difference is who learns. A Linux bridge learns inside
 * the box. Here the switch sends a copy of any frame from an unknown source
 * MAC to the controller (controller.py, given), and the controller writes the
 * table entries.
 *
 * Language reference: https://p4.org/specifications/
 */
#include <core.p4>
#include <v1model.p4>

typedef bit<9>  port_t;
typedef bit<48> macAddr_t;

const port_t CPU_PORT        = 255;
const bit<32> TO_CONTROLLER  = 100;  /* clone session that copies to the controller */
const bit<16> FLOOD_GROUP    = 1;    /* multicast group: every host port */

/* What the controller receives with each copied frame. */
@controller_header("packet_in")
header packet_in_t {
    bit<9> ingress_port;
    bit<7> pad;
}

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

struct metadata {
    @field_list(1)
    port_t ingress_port;
}

struct headers {
    packet_in_t packet_in;
    ethernet_t  ethernet;
}

parser MyParser(packet_in packet, out headers hdr, inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        transition accept;
    }
}

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control MyIngress(inout headers hdr, inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action learn() {
        meta.ingress_port = standard_metadata.ingress_port;
        clone_preserving_field_list(CloneType.I2E, TO_CONTROLLER, 1);
    }

    /* Source MACs the controller already knows. A miss means "new here". */
    table learned {
        key = { hdr.ethernet.srcAddr: exact; }
        actions = { learn; NoAction; }
        default_action = learn();
        size = 1024;
    }

    action forward(port_t port) {
        /* YOUR TASK: send the frame out `port` only. The output port is
         * standard_metadata.egress_spec. */
    }

    action flood() {
        /* YOUR TASK: send the frame to every host port. The controller made
         * multicast group FLOOD_GROUP hold every port; a frame joins it by
         * setting standard_metadata.mcast_grp. */
    }

    /* Destination MAC -> the port it was learned on. */
    table mac_table {
        key = { hdr.ethernet.dstAddr: exact; }
        actions = { forward; flood; }
        default_action = flood();
        size = 1024;
    }

    apply {
        /* YOUR TASK, in week 4's order: first learn the source (apply
         * `learned`), then decide where the frame goes (apply `mac_table`). */
    }
}

control MyEgress(inout headers hdr, inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply {
        if (standard_metadata.instance_type == 1) {
            /* The copy for the controller: say which port it came in on. */
            hdr.packet_in.setValid();
            hdr.packet_in.ingress_port = meta.ingress_port;
        }
        /* YOUR TASK: a flood goes to every port in the group, including the
         * one the frame came in on. Drop that copy: compare
         * standard_metadata.egress_port with standard_metadata.ingress_port,
         * and use mark_to_drop(standard_metadata). */
    }
}

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.packet_in);
        packet.emit(hdr.ethernet);
    }
}

V1Switch(MyParser(), MyVerifyChecksum(), MyIngress(), MyEgress(),
         MyComputeChecksum(), MyDeparser()) main;
