"""The controller (final option). Given; you do not change it.

Pushes your part 1 program to every switch over P4Runtime, then installs the
ipv4_lpm entries routing.next_hops() computes. Run it while the network is up
(make run in one terminal, this in another), or let `make check` run it.

    python3 controller.py
    python3 controller.py --down s1-s3

Every run starts from empty tables, so it can be run again after a change.
Uses p4lang's p4runtime_lib (../utils); P4Runtime spec: https://p4.org/specifications/
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "utils"))

import p4runtime_lib.bmv2                     # noqa: E402  (after the path fix above)
import p4runtime_lib.helper                   # noqa: E402
from p4runtime_lib.switch import ShutdownAllSwitchConnections   # noqa: E402

import routing                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def install(topo_path, p4info_path, bmv2_json, down=()):
    with open(topo_path) as f:
        topo = json.load(f)
    tables = routing.next_hops(topo, down)
    helper = p4runtime_lib.helper.P4InfoHelper(p4info_path)
    os.makedirs("logs", exist_ok=True)
    try:
        for device_id, name in enumerate(topo["switches"]):
            sw = p4runtime_lib.bmv2.Bmv2SwitchConnection(
                name=name, address=f"127.0.0.1:{50051 + device_id}", device_id=device_id,
                proto_dump_file=f"logs/{name}-controller-requests.txt")
            sw.MasterArbitrationUpdate()
            # pushing the program again empties every table, so each run starts clean
            sw.SetForwardingPipelineConfig(p4info=helper.p4info, bmv2_json_file_path=bmv2_json)
            for ip, (mac, port) in tables.get(name, {}).items():
                sw.WriteTableEntry(helper.buildTableEntry(
                    table_name="MyIngress.ipv4_lpm",
                    match_fields={"hdr.ipv4.dstAddr": (ip, 32)},
                    action_name="MyIngress.ipv4_forward",
                    action_params={"dstAddr": mac, "port": port}))
            print(f"{name}: {len(tables.get(name, {}))} entries")
    finally:
        ShutdownAllSwitchConnections()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topo", default=os.path.join(HERE, "..", "topo", "topology.json"))
    ap.add_argument("--p4info", default="build/forwarding.p4.p4info.txt")
    ap.add_argument("--json", default="build/forwarding.json")
    ap.add_argument("--down", action="append", default=[])
    args = ap.parse_args()
    install(args.topo, args.p4info, args.json, args.down)


if __name__ == "__main__":
    main()
