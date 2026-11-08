"""The learning switch's controller. Given; you do not change it.

Week 4's switch learned by itself: every frame's source MAC and arrival port
went into its table. This switch cannot write its own table, so it copies any
frame from a source MAC it does not know to this program, which writes two
entries: "this MAC is known" (learned) and "frames for this MAC leave by that
port" (mac_table). Until those entries arrive, frames to that MAC are flooded.

    python3 controller.py --ports 3           # started for you by make test

Reference: P4Runtime specification, PacketIn and multicast groups,
https://p4.org/p4-spec/p4runtime/main/P4Runtime-Spec.html
"""

import argparse
import sys
import time

sys.path.insert(0, "../utils")
import p4runtime_lib.bmv2  # noqa: E402
import p4runtime_lib.helper  # noqa: E402

CPU_PORT = 255
TO_CONTROLLER = 100
FLOOD_GROUP = 1


def connect(p4info, bmv2_json, address):
    helper = p4runtime_lib.helper.P4InfoHelper(p4info)
    sw = p4runtime_lib.bmv2.Bmv2SwitchConnection(name="s1", address=address, device_id=0)
    sw.MasterArbitrationUpdate()
    sw.SetForwardingPipelineConfig(p4info=helper.p4info, bmv2_json_file_path=bmv2_json)
    return helper, sw


def install_groups(helper, sw, ports):
    """Flood to every host port; copy new sources to the controller."""
    replicas = [{"egress_port": p, "instance": 1} for p in range(ports)]
    sw.WritePREEntry(helper.buildMulticastGroupEntry(FLOOD_GROUP, replicas))
    to_cpu = [{"egress_port": CPU_PORT, "instance": 1}]
    sw.WritePREEntry(helper.buildCloneSessionEntry(TO_CONTROLLER, to_cpu))


def learn(helper, sw, mac, port, known):
    """Write the two entries for one source MAC, once."""
    if mac in known:
        return
    known[mac] = port
    sw.WriteTableEntry(helper.buildTableEntry(
        table_name="MyIngress.learned",
        match_fields={"hdr.ethernet.srcAddr": mac},
        action_name="NoAction"))
    sw.WriteTableEntry(helper.buildTableEntry(
        table_name="MyIngress.mac_table",
        match_fields={"hdr.ethernet.dstAddr": mac},
        action_name="MyIngress.forward",
        action_params={"port": port}))
    print(f"learned {mac} on port {port}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--p4info", default="build/switching.p4.p4info.txt")
    ap.add_argument("--json", default="build/switching.json")
    ap.add_argument("--address", default="127.0.0.1:50051")
    ap.add_argument("--ports", type=int, default=3)
    args = ap.parse_args()

    helper, sw = connect(args.p4info, args.json, args.address)
    install_groups(helper, sw, args.ports)
    print("controller ready", flush=True)
    known = {}
    while True:
        msg = sw.PacketIn()
        port = int.from_bytes(msg.metadata[0].value, "big")
        frame = msg.payload
        mac = ":".join(f"{b:02x}" for b in frame[6:12])
        try:
            learn(helper, sw, mac, port, known)
        except Exception as exc:  # noqa: BLE001 - keep learning after one bad write
            print(f"could not learn {mac}: {exc}", flush=True)
            time.sleep(0.1)


if __name__ == "__main__":
    main()
