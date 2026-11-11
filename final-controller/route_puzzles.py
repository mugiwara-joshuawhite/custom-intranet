"""The controller (final option) practice: three puzzles against flawed controllers.

Given; you do not change it.

Each puzzle's controller is recorded in route_suspects.json as the tables it
installs for every set of failed switch links. An answer names a source host, a
destination host and the links to fail. This runner looks up that controller's
tables, then forwards one packet hop by hop over ../topo/topology.json, where a
failed link carries nothing. The goal of each puzzle is on the Canvas page.

    python3 route_puzzles.py --student your_id                    # every answer in route_answers.py
    python3 route_puzzles.py R-loop --student your_id             # one answer
    python3 route_puzzles.py R-loop --student your_id --src h1 --dst h4 --down s1-s4
    python3 route_puzzles.py R-loop --show --down s1-s4           # that controller's tables

A solved puzzle prints a proof token tied to your id and your input.
Standard library only. Reference: https://docs.python.org/3/library/hashlib.html
"""

import argparse
import hashlib
import json
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.join(HERE, "..", "topo", "topology.json")
SUSPECTS = os.path.join(HERE, "route_suspects.json")
PUZZLES = ("R-asym", "R-blackhole", "R-loop")


class Network:
    """The physical topology: which port leads where, and where each host attaches."""

    def __init__(self, topo):
        self.ip = {h: info["ip"].split("/")[0] for h, info in topo["hosts"].items()}
        self.mac = {h: info["mac"] for h, info in topo["hosts"].items()}
        self.switches = sorted(topo["switches"])
        self.wire = {}        # (switch, port) -> the node at the other end
        self.home = {}        # host -> its switch
        self.links = set()    # switch-to-switch links, as sorted pairs
        for left, right in topo["links"]:
            (a, ap), (b, bp) = (self.end(left), self.end(right))
            if ap is not None:
                self.wire[(a, ap)] = b
            if bp is not None:
                self.wire[(b, bp)] = a
            if ap is None:
                self.home[a] = b
            elif bp is None:
                self.home[b] = a
            else:
                self.links.add(tuple(sorted((a, b))))
        self.spines = [s for s in self.switches if s not in self.home.values()]

    @staticmethod
    def end(text):
        node, _, port = text.partition("-p")
        return node, (int(port) if port else None)

    def connected(self, src, dst, cut):
        """Is there any working path from src's switch to dst's switch?"""
        start, goal = self.home[src], self.home[dst]
        seen, queue = {start}, deque([start])
        while queue:
            s = queue.popleft()
            for a, b in self.links:
                if s in (a, b) and (a, b) not in cut:
                    n = b if s == a else a
                    if n not in seen:
                        seen.add(n)
                        queue.append(n)
        return goal in seen


def canonical_down(net, down):
    """Each failed link as "sA-sB" with endpoints sorted; reject anything that is
    not a switch link."""
    out = set()
    for text in down:
        ends = tuple(sorted(text.strip().split("-")))
        if len(ends) != 2 or ends not in net.links:
            raise ValueError(f"{text!r} is not a link between two switches; the switch links are "
                             + ", ".join("-".join(link) for link in sorted(net.links)))
        out.add(ends)
    return sorted(out)


def forward(net, tables, cut, src, dst):
    """Follow one packet from src toward dst. Returns (outcome, hops, reason).

    outcome is "delivered", "dropped" or "loop"; hops lists every node reached.
    """
    ip, at, hops = net.ip[dst], net.home[src], [src]
    while True:
        if at in hops:
            hops.append(at)
            return "loop", hops, (f"the packet came back to {at}, "
                                  "so it circles until its TTL runs out")
        hops.append(at)
        entry = tables[at].get(ip)
        if entry is None:
            return "dropped", hops, f"{at} has no entry for {ip}"
        mac, port = entry
        nxt = net.wire.get((at, port))
        if nxt is None:
            return "dropped", hops, f"{at} sends out port {port}, which leads nowhere"
        if tuple(sorted((at, nxt))) in cut:
            return "dropped", hops, f"{at} sends out port {port}, onto the failed {at}-{nxt} link"
        if nxt in net.home:
            hops.append(nxt)
            if nxt != dst:
                return "dropped", hops, f"{at} delivers to {nxt}, not {dst}"
            if mac != net.mac[dst]:
                return "dropped", hops, f"{dst} ignores a frame addressed to {mac}"
            return "delivered", hops, f"{dst} receives it"
        at = nxt


def path_text(hops):
    return " -> ".join(hops)


def judge(net, suspects, puzzle, src, dst, down):
    """Check one answer. Returns (solved, canonical input, lines to print)."""
    if src not in net.home or dst not in net.home or src == dst:
        hosts = ", ".join(sorted(net.home))
        return False, None, [f"src and dst must be two different hosts from {hosts}"]
    try:
        links = canonical_down(net, down)
    except ValueError as err:
        return False, None, [str(err)]
    key = ",".join("-".join(link) for link in links)
    cut = set(links)
    tables = suspects[puzzle][key]
    canon = f"{src}>{dst}|{key}"
    out_come, out_hops, out_why = forward(net, tables, cut, src, dst)
    lines = [f"failed links: {key or 'none'}",
             f"{src} to {dst}: {path_text(out_hops)}; {out_come}: {out_why}"]

    if puzzle == "R-asym":
        back, back_hops, back_why = forward(net, tables, cut, dst, src)
        lines.append(f"{dst} to {src}: {path_text(back_hops)}; {back}: {back_why}")
        if out_come != "delivered" or back != "delivered":
            lines.append("not solved: both directions must be delivered")
            return False, canon, lines
        there = [n for n in out_hops if n in net.spines]
        again = [n for n in back_hops if n in net.spines]
        if set(there) == set(again):
            lines.append(f"not solved: both directions cross {', '.join(there) or 'no spine'}")
            return False, canon, lines
        lines.append(f"solved: there through {', '.join(there)}, back through {', '.join(again)}")
        return True, canon, lines

    if puzzle == "R-blackhole":
        if out_come == "delivered":
            lines.append("not solved: the packet arrived")
            return False, canon, lines
        if out_come == "loop":
            lines.append("not solved: the packet loops; this puzzle asks for a drop")
            return False, canon, lines
        if not net.connected(src, dst, cut):
            lines.append(f"not solved: with these links failed no path from {src} to {dst} "
                         "exists, so a drop is expected")
            return False, canon, lines
        lines.append(f"solved: a working path from {src} to {dst} exists, "
                     "yet the packet is dropped")
        return True, canon, lines

    if out_come != "loop":
        lines.append("not solved: the packet does not loop")
        return False, canon, lines
    lines.append("solved: the packet loops")
    return True, canon, lines


def token(puzzle, student, canon):
    return hashlib.sha256(f"p4p2|{puzzle}|{student}|{canon}".encode()).hexdigest()[:16]


def show(net, suspects, puzzle, down):
    links = canonical_down(net, down)
    tables = suspects[puzzle][",".join("-".join(link) for link in links)]
    for switch in sorted(tables):
        for ip, (mac, port) in sorted(tables[switch].items()):
            print(f"{switch}  {ip:<10} -> port {port}, MAC {mac}")


def load():
    with open(TOPO) as f:
        net = Network(json.load(f))
    with open(SUSPECTS) as f:
        return net, json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", nargs="?", choices=PUZZLES, help="one puzzle; all three if left out")
    ap.add_argument("--student", help="your student id, which the proof token includes")
    ap.add_argument("--src", help="try this source host instead of route_answers.py")
    ap.add_argument("--dst", help="try this destination host")
    ap.add_argument("--down", action="append", default=[], help="a switch link to fail, like s1-s3")
    ap.add_argument("--show", action="store_true",
                    help="print the puzzle controller's tables for --down")
    args = ap.parse_args()
    net, suspects = load()

    if args.show:
        if not args.puzzle:
            ap.error("--show needs a puzzle name")
        show(net, suspects, args.puzzle, args.down)
        return 0
    if not args.student:
        ap.error("--student is required")

    if args.src or args.dst:
        if not args.puzzle:
            ap.error("--src and --dst need a puzzle name")
        answers = {args.puzzle: {"src": args.src, "dst": args.dst, "down": args.down}}
    else:
        sys.path.insert(0, HERE)
        import route_answers
        answers = route_answers.ANSWERS

    all_solved = True
    for puzzle in [args.puzzle] if args.puzzle else PUZZLES:
        answer = answers.get(puzzle)
        print(f"== {puzzle}")
        if not answer:
            print("no answer yet in route_answers.py")
            all_solved = False
            continue
        solved, canon, lines = judge(net, suspects, puzzle, answer.get("src"), answer.get("dst"),
                                     answer.get("down", []))
        for line in lines:
            print(line)
        if solved:
            print(f"proof token {token(puzzle, args.student, canon)}  for {canon}")
        all_solved = all_solved and solved
    return 0 if all_solved else 1


if __name__ == "__main__":
    sys.exit(main())
