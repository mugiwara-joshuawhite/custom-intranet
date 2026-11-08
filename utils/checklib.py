"""Start the network, run checks against it, and always stop it. Used by each part's check.py.

A check is a function taking the running Mininet network. It returns None to
pass, or a string saying what went wrong. Anything it raises counts as a
failure too, so one broken check never hides the others.
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_exercise import ExerciseRunner          # noqa: E402  (after the path fix above)


def run_checks(topo, p4_json, checks, before=None):
    """Run each (name, function) in checks against one fresh network.

    `before(net)` runs once after the switches are programmed, for a part
    whose controller installs the table entries.
    """
    results = []
    subprocess.run(["mn", "-c"], capture_output=True)
    # With IPv6 on, the kernel announces every new interface, and those packets
    # would show up in the per-port counters some checks read.
    for scope in ("all", "default"):
        subprocess.run(["sysctl", "-qw", f"net.ipv6.conf.{scope}.disable_ipv6=1"],
                       capture_output=True)
    runner = ExerciseRunner(topo, "logs", "pcaps", p4_json, "simple_switch_grpc", quiet=True)
    try:
        runner.create_network()
        runner.net.start()
        time.sleep(1)
        runner.program_hosts()
        runner.program_switches()
        time.sleep(1)
        if before is not None:
            try:
                before(runner.net)
            except Exception as e:                   # the checks still run, and fail
                results.append(False)
                print(f"FAIL  setting up the tables: {type(e).__name__}: {e}")
        for name, check in checks:
            try:
                problem = check(runner.net)
            except Exception as e:                   # reported, then the next check runs
                problem = f"{type(e).__name__}: {e}"
            results.append(problem is None)
            if problem is None:
                print("PASS  " + name)
            else:
                print("FAIL  " + name + f": {problem}")
    finally:
        runner.net.stop()
    print(f"\n{sum(results)} passed, {len(results) - sum(results)} failed")
    return all(results)


def ping(net, src, dst_ip, count=2):
    """(packets received, reply TTL or None) for `count` pings from host src."""
    out = net.get(src).cmd(f"ping -c {count} -W 1 {dst_ip}")
    received = 0
    for line in out.splitlines():
        if "received" in line:
            received = int(line.split(",")[1].split()[0])
    ttls = [int(w.split("=")[1]) for w in out.split() if w.startswith("ttl=")]
    return received, (ttls[0] if ttls else None)
