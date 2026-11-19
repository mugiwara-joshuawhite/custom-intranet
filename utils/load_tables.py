"""Load a part's table entries into the switch, then say ready. Given; do not edit.

    python3 ../utils/load_tables.py tables.json      # started for you by make test

tables.json names the compiled program and lists every table entry, the way
a router's configuration lists its routes. Each entry it writes is printed,
so a missing or rejected entry is visible here and in build/setup.log.
"""

import json
import sys

sys.path.insert(0, "../utils")
from p4runtime_lib import simple_controller  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("usage: python3 ../utils/load_tables.py tables.json")
        return 1
    conf = sys.argv[1]
    with open(conf) as f:
        entries = json.load(f).get("table_entries", [])
    print(f"loading {len(entries)} table entries from {conf}", flush=True)
    for e in entries:
        print(f"  {e['table']}: {e.get('match', 'default')} -> {e['action_name']} "
              f"{e.get('action_params', {})}", flush=True)
    try:
        with open(conf) as sw_conf:
            simple_controller.program_switch(addr="127.0.0.1:50051", device_id=0,
                                             sw_conf_file=sw_conf, workdir=".",
                                             proto_dump_fpath="build/p4runtime-requests.txt",
                                             runtime_json=conf)
    except Exception as exc:  # noqa: BLE001 - say what failed instead of a stack trace
        print(f"could not load the tables: {exc}")
        if "list" in str(exc):
            print("An entry gives a prefix, [address, length], but that table's key is not lpm.")
            print("Check the match kind in your table's key: "
                  "a prefix needs `lpm`, a single value `exact`.")
        else:
            print(f"Check that the table, action and parameter names in {conf} match your program.")
        return 1
    print("tables loaded; switch ready", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
