"""Part 3: the ECMP controller. Given; you do not change it.

Like part 2's controller, but for each switch and host it installs one
ecmp_group entry (the destination's group number and size) and one ecmp_nhop
entry per next hop in the group. Groups come from routing_ecmp.ecmp_next_hops().

    python3 controller.py
    python3 controller.py --only s1    # one switch, for make test's packet tests
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "utils"))

import p4runtime_lib.bmv2                     # noqa: E402
import p4runtime_lib.helper                   # noqa: E402
from p4runtime_lib.switch import ShutdownAllSwitchConnections   # noqa: E402

import routing_ecmp                           # noqa: E402


def install(topo_path, p4info_path, bmv2_json, down=(), only=None):
    with open(topo_path) as f:
        topo = json.load(f)
    groups = routing_ecmp.ecmp_next_hops(topo, down)
    helper = p4runtime_lib.helper.P4InfoHelper(p4info_path)
    os.makedirs("logs", exist_ok=True)
    try:
        for device_id, name in enumerate(topo["switches"]):
            if only and name != only:
                continue
            if only:
                device_id = 0  # the packet tests run one switch, at the first address
            sw = p4runtime_lib.bmv2.Bmv2SwitchConnection(
                name=name, address=f"127.0.0.1:{50051 + device_id}", device_id=device_id,
                proto_dump_file=f"logs/{name}-controller-requests.txt")
            sw.MasterArbitrationUpdate()
            sw.SetForwardingPipelineConfig(p4info=helper.p4info, bmv2_json_file_path=bmv2_json)
            for group, (ip, hops) in enumerate(sorted(groups.get(name, {}).items())):
                sw.WriteTableEntry(helper.buildTableEntry(
                    table_name="MyIngress.ecmp_group",
                    match_fields={"hdr.ipv4.dstAddr": (ip, 32)},
                    action_name="MyIngress.set_ecmp_select",
                    action_params={"group": group, "count": len(hops)}))
                for select, (mac, port) in enumerate(hops):
                    sw.WriteTableEntry(helper.buildTableEntry(
                        table_name="MyIngress.ecmp_nhop",
                        match_fields={"meta.ecmp_group": group, "meta.ecmp_select": select},
                        action_name="MyIngress.set_nhop",
                        action_params={"dstAddr": mac, "port": port}))
            sizes = sorted(groups.get(name, {}).items())
            print(f"{name}: " + ", ".join(f"{ip} x{len(h)}" for ip, h in sizes))
    finally:
        ShutdownAllSwitchConnections()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topo", default=os.path.join(HERE, "..", "topo", "topology.json"))
    ap.add_argument("--p4info", default="build/ecmp.p4.p4info.txt")
    ap.add_argument("--json", default="build/ecmp.json")
    ap.add_argument("--down", action="append", default=[])
    ap.add_argument("--only", help="install one switch only (the packet tests use s1)")
    args = ap.parse_args()
    install(args.topo, args.p4info, args.json, args.down, args.only)
    if args.only:
        print(f"{args.only} installed; switch ready", flush=True)


if __name__ == "__main__":
    main()
