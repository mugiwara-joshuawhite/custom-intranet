"""Part 1 practice: four longest-prefix-match puzzles. Given; you do not change it.

lpm_tables.json holds every switch's ipv4_lpm entries during part 1's last
check: the supplied runtime entries plus the overlapping /16, /24 and probe /32
entries check.py adds. An answer names a source host, a destination address and,
for a delivered packet, the TTL it arrives with. This runner sends one packet
with TTL 64 from the source host and follows it switch by switch over
topology.json: each switch picks the longest matching prefix, drops the packet
when no entry matches, and otherwise lowers the TTL by one, rewrites the
destination MAC and sends it out the entry's port. The goal of each puzzle is on
the Canvas page.

    python3 lpm_puzzles.py --student your_id     # every answer in lpm_answers.py
    python3 lpm_puzzles.py L-16 --student your_id --src h1 --dst 10.0.2.2 --ttl 63
    python3 lpm_puzzles.py --show s1             # one switch's entries

A solved puzzle prints a proof token tied to your id and your input.
Standard library only. References: https://docs.python.org/3/library/ipaddress.html
and https://docs.python.org/3/library/hashlib.html
"""

import argparse
import hashlib
import ipaddress
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOPO = os.path.join(HERE, "topology.json")
TABLES = os.path.join(HERE, "lpm_tables.json")
PUZZLES = ("L-32", "L-24", "L-16", "L-miss")
START_TTL = 64


def load():
    with open(TOPO) as f:
        topo = json.load(f)
    with open(TABLES) as f:
        tables = json.load(f)
    wire, home, mac = {}, {}, {}
    for h, info in topo["hosts"].items():
        mac[h] = info["mac"]
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
    return {"wire": wire, "home": home, "mac": mac, "tables": tables}


def matches(entries, address):
    """Every entry whose prefix contains address, longest first."""
    ip = ipaddress.ip_address(address)
    found = [e for e in entries if ip in ipaddress.ip_network(e["prefix"])]
    return sorted(found, key=lambda e: -ipaddress.ip_network(e["prefix"]).prefixlen)


def forward(net, src, dst):
    """Follow one packet from host src to address dst.

    Returns (outcome, steps, ttl). outcome is "delivered" or "dropped"; each step
    is a dict naming the switch, every matching entry, the winner and what happened.
    """
    at, ttl, steps = net["home"][src], START_TTL, []
    for _ in range(16):
        hits = matches(net["tables"]["switches"][at], dst)
        step = {"switch": at, "hits": hits, "winner": hits[0] if hits else None}
        steps.append(step)
        if not hits:
            step["what"] = "no entry matches, so the default action drops it"
            return "dropped", steps, ttl
        win = hits[0]
        if win["action"] == "drop":
            step["what"] = f"the longest match {win['prefix']} drops it"
            return "dropped", steps, ttl
        ttl -= 1
        nxt = net["wire"].get((at, win["port"]))
        step["what"] = (f"the longest match {win['prefix']} forwards it out port {win['port']} "
                        f"to {nxt}, TTL now {ttl}")
        if nxt is None:
            step["what"] = (f"the longest match {win['prefix']} sends it out port {win['port']}, "
                            "which leads nowhere")
            return "dropped", steps, ttl
        if nxt in net["mac"]:
            if win["mac"] != net["mac"][nxt]:
                step["what"] += f"; {nxt} ignores a frame addressed to {win['mac']}"
                return "dropped", steps, ttl
            if dst not in net["tables"]["host_addresses"][nxt]:
                step["what"] += f"; {nxt} does not hold {dst}, so it does not accept the packet"
                return "dropped", steps, ttl
            step["what"] += f"; {nxt} receives it"
            return "delivered", steps, ttl
        at = nxt
    return "dropped", steps, ttl


def describe(steps):
    lines = []
    for s in steps:
        hits = ", ".join(f"{e['prefix']} {e['action']}" for e in s["hits"]) or "nothing"
        lines.append(f"  {s['switch']}: matches {hits}; {s['what']}")
    return lines


def shorter_also_matched(first, action):
    """True when a shorter prefix with this action also matched at the first switch."""
    win = ipaddress.ip_network(first["winner"]["prefix"]).prefixlen
    return any(ipaddress.ip_network(e["prefix"]).prefixlen < win and e["action"] == action
               for e in first["hits"])


def judge_delivered(puzzle, ttl, outcome, steps, arrived, canon, lines):
    """L-32 and L-16: delivered through a /32 or /16, with the arrival TTL given."""
    first = steps[0]
    want = 32 if puzzle == "L-32" else 16
    if ttl is None:
        return False, canon, lines + [
            "not solved: give the TTL you expect the packet to arrive with"]
    canon += f"|ttl={ttl}"
    if outcome != "delivered":
        return False, canon, lines + ["not solved: the packet must be delivered"]
    win = first["winner"]
    if ipaddress.ip_network(win["prefix"]).prefixlen != want:
        return False, canon, lines + [
            f"not solved: at {first['switch']} the winning entry must be a /{want}"]
    if (puzzle == "L-32" and not shorter_also_matched(first, "forward")
            and not shorter_also_matched(first, "drop")):
        return False, canon, lines + [
            f"not solved: at {first['switch']} a shorter prefix must also match, "
            "so the /32 beats it"]
    if puzzle == "L-32" and len(steps) < 3:
        return False, canon, lines + [
            "not solved: the destination must be on the other edge switch, across a spine"]
    if int(ttl) != arrived:
        return False, canon, lines + [
            f"not solved: your TTL {ttl} is not the TTL the packet arrives with"]
    return True, canon, lines + [f"solved: delivered through the /{want} with TTL {arrived}"]


def judge_drop(outcome, steps, canon, lines):
    """L-24: the first switch drops it by a drop entry longer than a forwarding one."""
    first = steps[0]
    win = first["winner"]
    if outcome != "dropped" or len(steps) != 1 or win is None or win["action"] != "drop":
        return False, canon, lines + ["not solved: the first switch must drop it by a drop entry"]
    if not shorter_also_matched(first, "forward"):
        return False, canon, lines + [
            "not solved: a shorter forwarding entry must also match, so the longer drop wins"]
    return True, canon, lines + [f"solved: {win['prefix']} drop beats a shorter forwarding entry"]


def judge_miss(outcome, steps, canon, lines):
    """L-miss: forwarded at least once, then dropped because no entry matches."""
    if outcome != "dropped" or steps[-1]["hits"]:
        return False, canon, lines + [
            "not solved: the packet must be dropped because no entry matches"]
    if len(steps) < 2:
        return False, canon, lines + ["not solved: at least one switch must forward it first"]
    return True, canon, lines + [
        f"solved: {steps[-1]['switch']} has no matching entry "
        f"after {steps[0]['switch']} forwarded it"]


def judge(net, puzzle, src, dst, ttl):
    """Check one answer. Returns (solved, canonical input, lines to print)."""
    if src not in net["home"]:
        return False, None, [f"src must be one of {', '.join(sorted(net['home']))}"]
    try:
        dst = str(ipaddress.IPv4Address(str(dst).strip()))
    except ValueError:
        return False, None, [f"{dst!r} is not an IPv4 address like 10.0.2.2"]
    outcome, steps, arrived = forward(net, src, dst)
    canon = f"{src}>{dst}"
    lines = ([f"{src} sends to {dst} with TTL {START_TTL}"] + describe(steps)
             + [f"outcome: {outcome}"])
    if puzzle in ("L-32", "L-16"):
        return judge_delivered(puzzle, ttl, outcome, steps, arrived, canon, lines)
    if puzzle == "L-24":
        return judge_drop(outcome, steps, canon, lines)
    return judge_miss(outcome, steps, canon, lines)


def token(puzzle, student, canon):
    return hashlib.sha256(f"p4p1|{puzzle}|{student}|{canon}".encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", nargs="?", choices=PUZZLES, help="one puzzle; all four if left out")
    ap.add_argument("--student", help="your student id, which the proof token includes")
    ap.add_argument("--src", help="try this source host instead of lpm_answers.py")
    ap.add_argument("--dst", help="try this destination address")
    ap.add_argument("--ttl", type=int, help="the arrival TTL you expect (L-32 and L-16)")
    ap.add_argument("--show", metavar="SWITCH", help="print one switch's entries")
    args = ap.parse_args()
    net = load()

    if args.show:
        for e in net["tables"]["switches"][args.show]:
            out = f"out port {e['port']}, MAC {e['mac']}" if e["action"] == "forward" else ""
            print(f"{args.show}  {e['prefix']:<15} {e['action']:<8} {out}")
        return 0
    if not args.student:
        ap.error("--student is required")
    if args.src or args.dst:
        if not args.puzzle:
            ap.error("--src and --dst need a puzzle name")
        answers = {args.puzzle: {"src": args.src, "dst": args.dst, "ttl": args.ttl}}
    else:
        sys.path.insert(0, HERE)
        import lpm_answers
        answers = lpm_answers.ANSWERS

    all_solved = True
    for puzzle in [args.puzzle] if args.puzzle else PUZZLES:
        answer = answers.get(puzzle)
        print(f"== {puzzle}")
        if not answer:
            print("no answer yet in lpm_answers.py")
            all_solved = False
            continue
        solved, canon, lines = judge(net, puzzle, answer.get("src"), answer.get("dst"),
                                     answer.get("ttl"))
        for line in lines:
            print(line)
        if solved:
            print(f"proof token {token(puzzle, args.student, canon)}  for {canon}")
        all_solved = all_solved and solved
    return 0 if all_solved else 1


if __name__ == "__main__":
    sys.exit(main())
