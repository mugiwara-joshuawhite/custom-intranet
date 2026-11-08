"""Run a segment's packet tests against your P4 program. Given; do not edit.

    python3 ../utils/ptfrun.py switching.p4 --ports 3 --setup "python3 controller.py --ports 3"

What it does, in order:
  1. compiles the program with p4c into build/
  2. makes one virtual cable (a veth pair) per switch port
  3. starts the BMv2 switch on one end of each cable, recording every packet
     each port sends and receives as build/pcaps/<port>_in.pcap and _out.pcap
  4. runs the setup command (the controller, or the table loader) until it
     prints "ready"
  5. runs PTF, which sends packets into the other end of each cable and checks
     what comes out
Open the .pcap files in Wireshark to see exactly what the switch did.

    python3 ../utils/ptfrun.py switching.p4 --ports 3 --linux "sh linux.sh"

--linux runs the same tests against an ordinary Linux device built by the
given linux.sh (a bridge, a router, a tunnel) on the same cables, and records
build/pcaps-linux/. If both pass, the two behave the same on the wire; compare
the captures to see whether every byte is the same too.

PTF: https://github.com/p4lang/ptf    BMv2: https://github.com/p4lang/behavioral-model
"""

import argparse
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path


def sh(cmd, check=True):
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)


def cables(ports):
    """veth{2p} is the switch's end of port p; veth{2p+1} is the test's end."""
    for p in range(ports):
        a, b = f"veth{2 * p}", f"veth{2 * p + 1}"
        sh(f"ip link del {a}", check=False)
        sh(f"ip link add {a} type veth peer name {b}")
        for dev in (a, b):
            sh(f"ip link set {dev} up")
            sh(f"sysctl -qw net.ipv6.conf.{dev}.disable_ipv6=1", check=False)
            sh(f"ethtool -K {dev} tx off rx off", check=False)


def run_tests(cmd, captures):
    """Run PTF, show its lines as they come, then end with a summary a student can act on."""
    proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    results, why = [], {}
    current = None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.startswith("Using packet manipulation module"):
            continue
        if line.endswith(" ... ok") or line.endswith(" ... FAIL") or line.endswith(" ... ERROR"):
            name, _, outcome = line.rpartition(" ... ")
            name = name.split(".")[-1]
            results.append((name, "PASS" if outcome == "ok" else "FAIL"))
            print(f"  {results[-1][1]}  {name}", flush=True)
            continue
        if line.startswith(("FAIL: ", "ERROR: ")):
            current = line.split(".")[-1]
        elif line.startswith("AssertionError: ") and current:
            why[current] = line[len("AssertionError: "):]
        elif "Error" in line and current and current not in why and not line.startswith(" "):
            why[current] = line
    proc.wait()
    passed = sum(1 for _, r in results if r == "PASS")
    print(f"\n{passed} of {len(results)} packet tests passed.")
    failed = [n for n, r in results if r == "FAIL"]
    if not results:
        print("No test ran. Check that the tests folder exists and that the switch started "
              "(see the logs below).")
    for n in failed:
        print(f"  {n}: {why.get(n, 'see build/ptf.log')}")
    if failed:
        print(f"\nStart with {failed[0]}. Open the captures in {captures}/ in Wireshark: "
              "_in.pcap is what entered the switch on that port, _out.pcap is what left it.")
    return 0 if results and not failed else 1


def wait_ready(setup, log, seconds=30):
    """Copy the setup's output into log until it prints "ready"; False if it stops first."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        line = setup.stdout.readline()
        if not line:
            return False
        log.write(line)
        log.flush()
        if "ready" in line:
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("program", help="your .p4 file")
    ap.add_argument("--ports", type=int, required=True)
    ap.add_argument("--setup", help="command that configures the P4 switch and prints 'ready'")
    ap.add_argument("--linux",
                    help="command that builds the Linux equivalent on the switch's cable ends")
    ap.add_argument("--tests", default="tests")
    ap.add_argument("--keep", action="store_true", help="leave the switch running (debugging)")
    args = ap.parse_args()

    if args.linux:
        return run_linux(args)
    if not args.setup:
        ap.error("--setup is required unless --linux is given")
    name = Path(args.program).stem
    build = Path("build")
    (build / "pcaps").mkdir(parents=True, exist_ok=True)
    for old in (build / "pcaps").glob("*.pcap"):
        old.unlink()

    print(f"[1/5] compiling {args.program}")
    r = sh(f"p4c-bm2-ss --p4v 16 --p4runtime-files build/{name}.p4.p4info.txt "
           f"-o build/{name}.json {args.program}", check=False)
    if r.returncode:
        print(r.stdout + r.stderr)
        print("The program did not compile: fix the first error p4c names above, then run again.")
        return 1

    print(f"[2/5] {args.ports} virtual cables")
    cables(args.ports)

    print("[3/5] starting the switch (log: build/switch.log, captures: build/pcaps/)")
    ifs = " ".join(f"-i {p}@veth{2 * p}" for p in range(args.ports))
    switch = subprocess.Popen(
        shlex.split(f"simple_switch_grpc --device-id 0 {ifs} --pcap build/pcaps "
                    f"--log-file build/switch --log-flush --no-p4 -- "
                    f"--grpc-server-addr 127.0.0.1:50051 --cpu-port 255"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    print(f"[4/5] setup: {args.setup}")
    setup = subprocess.Popen(shlex.split(args.setup), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
    # Left open on success: the drain thread below keeps writing to it.
    log = open(build / "setup.log", "w")  # noqa: SIM115
    if not wait_ready(setup, log):
        log.close()
        tail = (build / "setup.log").read_text().strip().splitlines()[-6:]
        print("The setup stopped before the switch was ready. "
              "Its last lines (all of it is in build/setup.log):")
        for line in tail:
            print(f"    {line}")
        if any("NotImplementedError" in line for line in tail):
            print("A function the setup calls is not written yet: "
                  "finish the one named above, then run again.")
        setup.kill()
        switch.kill()
        return 1

    def drain():  # keep the setup's later output (for example, what the controller learned)
        for line in setup.stdout:
            log.write(line)
            log.flush()
    import threading
    threading.Thread(target=drain, daemon=True).start()

    print("[5/5] running the packet tests\n")
    ifaces = " ".join(f"--interface {p}@veth{2 * p + 1}" for p in range(args.ports))
    code = run_tests(f"ptf --test-dir {args.tests} --pypath {os.getcwd()} {ifaces} "
                     "--log-file build/ptf.log", "build/pcaps")

    if not args.keep:
        setup.kill()
        switch.kill()
    print("Switch log (every table hit, per packet): build/switch.log   "
          "Setup log: build/setup.log")
    return code


def run_linux(args):
    """The same tests, with a Linux bridge, router or tunnel in place of the P4 switch."""
    pcaps = Path("build/pcaps-linux")
    pcaps.mkdir(parents=True, exist_ok=True)
    for old in pcaps.glob("*.pcap"):
        old.unlink()
    print(f"[1/3] {args.ports} virtual cables, then the Linux device: {args.linux}")
    cables(args.ports)
    r = sh(args.linux, check=False)
    if r.returncode:
        print(r.stdout + r.stderr)
        return 1
    dumps = [subprocess.Popen(shlex.split(f"tcpdump -q -U -i veth{2 * p} "
                                          f"-w {pcaps}/veth{2 * p}.pcap"),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for p in range(args.ports)]
    time.sleep(1)
    print("[2/3] running the same packet tests\n")
    ifaces = " ".join(f"--interface {p}@veth{2 * p + 1}" for p in range(args.ports))
    code = run_tests(f"ptf --test-dir {args.tests} --pypath {os.getcwd()} {ifaces} "
                     "--log-file build/ptf-linux.log", str(pcaps))
    time.sleep(1)
    for d in dumps:
        d.terminate()
    print(f"[3/3] Linux captures (one file per port, both directions): {pcaps}/")
    return code


if __name__ == "__main__":
    sys.exit(main())
