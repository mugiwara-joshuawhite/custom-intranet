"""Part 4 challenge route: two source-route puzzles. Given; you do not change it.

An answer is a destination host and the port stack send_route.py would put on
a packet from h1, top entry first. This runner follows the packet over
../topo/topology.json the way the part 4 data plane handles it: a switch takes
the top entry, sends the packet out that port and removes the entry, lowering
the IPv4 TTL by one; the switch that uses the last entry changes the EtherType
back to IPv4. A switch that receives a packet with no entry left drops it. A
host accepts the packet only once no entries remain and only if it is addressed
to that host. The goal of each puzzle is on the Canvas page.

    python3 stack_puzzles.py --student your_id     # every answer in stack_answers.py
    python3 stack_puzzles.py S-via --student your_id --dst h3 --ports "3 2 1"

A solved puzzle prints a proof token tied to your id and your input.
Standard library only. Reference: https://docs.python.org/3/library/hashlib.html
"""

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.join(HERE, "..", "topo", "topology.json")
PUZZLES = ("S-via", "S-revisit")
SOURCE = "h1"
START_TTL = 64
MAX_ENTRIES = 9  # the size of the program's source-route header stack


def load():
    with open(TOPO) as f:
        topo = json.load(f)
    wire, home = {}, {}
    for left, right in topo["links"]:
        a, _, ap = left.partition("-p")
        b, _, bp = right.partition("-p")
        if ap:
            wire[(a, int(ap))] = b
        if bp:
            wire[(b, int(bp))] = a
        if not ap:
            home[a] = b
        if not bp:
            home[b] = a
    return {"wire": wire, "home": home}


def follow(net, dst, ports):
    """Returns (outcome, switches visited in order, arrival TTL, lines)."""
    at, ttl, stack, visited, lines = net["home"][SOURCE], START_TTL, list(ports), [], []
    while True:
        visited.append(at)
        if not stack:
            lines.append(f"  {at}: no source-route entry left, so it drops the packet")
            return "dropped", visited, ttl, lines
        port = stack.pop(0)
        ttl -= 1
        last = " (the last entry, so the EtherType goes back to IPv4)" if not stack else ""
        nxt = net["wire"].get((at, port))
        if nxt is None:
            lines.append(f"  {at}: top entry port {port}{last}, TTL {ttl}; "
                         f"port {port} leads nowhere, so the packet is lost")
            return "dropped", visited, ttl, lines
        lines.append(f"  {at}: top entry port {port}{last}, TTL {ttl}; out to {nxt}")
        if nxt in net["home"]:
            if stack:
                left = "1 entry is" if len(stack) == 1 else f"{len(stack)} entries are"
                lines.append(f"  {nxt}: {left} still on the packet, "
                             f"so it is not IPv4 and {nxt} ignores it")
                return "dropped", visited, ttl, lines
            if nxt != dst:
                lines.append(f"  {nxt}: the packet is addressed to {dst}, "
                             f"so {nxt} does not accept it")
                return "dropped", visited, ttl, lines
            lines.append(f"  {nxt}: receives it with TTL {ttl}")
            return "delivered", visited, ttl, lines
        at = nxt


def judge(net, puzzle, dst, ports):
    """Check one answer. Returns (solved, canonical input, lines to print)."""
    if dst not in net["home"] or dst == SOURCE:
        others = ", ".join(h for h in sorted(net["home"]) if h != SOURCE)
        return False, None, [f"dst must be one of {others}"]
    try:
        if isinstance(ports, str):
            ports = ports.split()
        ports = [int(p) for p in ports]
    except (TypeError, ValueError):
        return False, None, ["ports must be a list of port numbers, like [3, 2, 1] or \"3 2 1\""]
    if not 1 <= len(ports) <= MAX_ENTRIES or any(not 1 <= p <= 511 for p in ports):
        return False, None, [f"give 1 to {MAX_ENTRIES} ports, each from 1 to 511"]
    canon = f"{dst}|{' '.join(map(str, ports))}"
    outcome, visited, ttl, lines = follow(net, dst, ports)
    lines = [f"{SOURCE} sends to {dst} with TTL {START_TTL} "
             f"and ports {' '.join(map(str, ports))}"] + lines
    lines.append(f"outcome: {outcome}; switches in order: {' '.join(visited)}")
    if outcome != "delivered":
        return False, canon, lines + ["not solved: the packet must be delivered"]
    if puzzle == "S-via":
        if dst != "h4" or "s3" not in visited or ttl != 59:
            return False, canon, lines + [
                "not solved: the goal is h4, through s3, arriving with TTL 59"]
        return True, canon, lines + ["solved: h4 receives it through s3 with TTL 59"]
    if dst != "h3" or visited.count("s1") < 2 or ttl != 57:
        return False, canon, lines + [
            "not solved: the goal is h3, leaving s1 twice, arriving with TTL 57"]
    return True, canon, lines + ["solved: h3 receives it with TTL 57 after passing s1 twice"]


def token(puzzle, student, canon):
    return hashlib.sha256(f"p4p4|{puzzle}|{student}|{canon}".encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", nargs="?", choices=PUZZLES, help="one puzzle; both if left out")
    ap.add_argument("--student", help="your student id, which the proof token includes")
    ap.add_argument("--dst", help="try this destination host instead of stack_answers.py")
    ap.add_argument("--ports", help='the port stack, top first, like "3 2 1"')
    args = ap.parse_args()
    net = load()
    if not args.student:
        ap.error("--student is required")
    if args.dst or args.ports:
        if not args.puzzle:
            ap.error("--dst and --ports need a puzzle name")
        answers = {args.puzzle: {"dst": args.dst, "ports": args.ports or ""}}
    else:
        sys.path.insert(0, HERE)
        import stack_answers
        answers = stack_answers.ANSWERS

    all_solved = True
    for puzzle in [args.puzzle] if args.puzzle else PUZZLES:
        answer = answers.get(puzzle)
        print(f"== {puzzle}")
        if not answer:
            print("no answer yet in stack_answers.py")
            all_solved = False
            continue
        solved, canon, lines = judge(net, puzzle, answer.get("dst"), answer.get("ports"))
        for line in lines:
            print(line)
        if solved:
            print(f"proof token {token(puzzle, args.student, canon)}  for {canon}")
        all_solved = all_solved and solved
    return 0 if all_solved else 1


if __name__ == "__main__":
    sys.exit(main())
