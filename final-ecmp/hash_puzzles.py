"""Part 3 challenge route: two hash puzzles on s1's ECMP choice. Given; you do not change it.

From h1 to h3, s1 has two equally short next hops: select 0 is port 3 (to the
spine s3) and select 1 is port 4 (to the spine s4). bmv2 computes the select
with HashAlgorithm.crc16 over the flow's fields packed in this order, 13 bytes:
IPv4 source address (4), destination address (4), protocol (1), source port (2),
destination port (2). The select is that 16-bit value modulo the group's count,
2. This runner computes the same thing for UDP flows from h1 (10.0.1.1) to h3
(10.0.3.3), and TCP flows with --tcp, so you can test flows without the
network. The goal of each puzzle is on the Canvas page.

    python3 hash_puzzles.py --flow 40000 5201        # one flow: source port, destination port
    python3 hash_puzzles.py --flow 44240 5201 --tcp  # the same for a TCP flow
    python3 hash_puzzles.py --student your_id        # every answer in hash_answers.py
    python3 hash_puzzles.py H-split --student your_id --sport 40000 --dports 5201 5202

A solved puzzle prints a proof token tied to your id and your input.
Standard library only. References: https://docs.python.org/3/library/ipaddress.html
and https://docs.python.org/3/library/hashlib.html
"""

import argparse
import hashlib
import ipaddress
import os
import sys

PUZZLES = ("H-same", "H-split")
SRC, DST, TCP, UDP = "10.0.1.1", "10.0.3.3", 6, 17
SPINE = {3: "s3", 4: "s4"}


def crc16(data):
    """CRC-16 as bmv2's crc16: polynomial 0x8005, bits taken least significant
    first, start 0, no final XOR."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def flow_bytes(src, dst, protocol, sport, dport):
    return (ipaddress.IPv4Address(src).packed + ipaddress.IPv4Address(dst).packed
            + protocol.to_bytes(1, "big") + sport.to_bytes(2, "big") + dport.to_bytes(2, "big"))


def s1_port(src, dst, protocol, sport, dport, count=2):
    """The port s1 sends this flow out of: select 0 is port 3, select 1 is port 4."""
    return 3 + crc16(flow_bytes(src, dst, protocol, sport, dport)) % count


def show_flow(sport, dport, protocol=UDP):
    value = crc16(flow_bytes(SRC, DST, protocol, sport, dport))
    port = 3 + value % 2
    name = "TCP" if protocol == TCP else "UDP"
    return port, (f"  {name} {SRC}:{sport} -> {DST}:{dport}  crc16 0x{value:04x}"
                  f"  select {value} % 2 = {value % 2}"
                  f"  -> s1 port {port} ({SPINE[port]})")


def port_number(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise ValueError(f"{value!r} is not a port number from 1 to 65535")
    return value


def judge(puzzle, answer):
    """Check one answer. Returns (solved, canonical input, lines to print)."""
    try:
        if puzzle == "H-same":
            sports = [port_number(p) for p in answer.get("sports", [])]
            dport = port_number(answer.get("dport"))
            if len(sports) != 4 or len(set(sports)) != 4:
                return False, None, ["H-same needs four different source ports"]
            if max(sports) - min(sports) > 7:
                return False, None, ["H-same's four source ports must lie within 8 consecutive "
                                     "numbers (largest minus smallest at most 7)"]
            flows = [(p, dport) for p in sports]
            canon = f"sports={','.join(map(str, sorted(sports)))}|dport={dport}"
        else:
            sport = port_number(answer.get("sport"))
            dports = [port_number(p) for p in answer.get("dports", [])]
            if len(dports) != 2 or dports[0] == dports[1]:
                return False, None, ["H-split needs two different destination ports"]
            flows = [(sport, p) for p in dports]
            canon = f"sport={sport}|dports={','.join(map(str, sorted(dports)))}"
    except (ValueError, TypeError, AttributeError) as err:
        return False, None, [str(err)]
    ports, lines = [], []
    for sport, dport in flows:
        port, line = show_flow(sport, dport)
        ports.append(port)
        lines.append(line)
    spines = sorted({SPINE[p] for p in ports})
    if puzzle == "H-same":
        if len(spines) != 1:
            return False, canon, lines + ["not solved: the four flows do not all use one spine"]
        return True, canon, lines + [f"solved: all four flows cross {spines[0]}"]
    if len(spines) != 2:
        return False, canon, lines + [f"not solved: both flows cross {spines[0]}"]
    return True, canon, lines + ["solved: the two flows cross different spines"]


def token(puzzle, student, canon):
    return hashlib.sha256(f"p4p3|{puzzle}|{student}|{canon}".encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", nargs="?", choices=PUZZLES, help="one puzzle; both if left out")
    ap.add_argument("--student", help="your student id, which the proof token includes")
    ap.add_argument("--flow", nargs=2, type=int, metavar=("SPORT", "DPORT"),
                    help="show one flow's hash and port")
    ap.add_argument("--tcp", action="store_true", help="with --flow, a TCP flow instead of UDP")
    ap.add_argument("--sports", nargs="+", type=int, help="H-same: try these four source ports")
    ap.add_argument("--dport", type=int, help="H-same: their destination port")
    ap.add_argument("--sport", type=int, help="H-split: try this source port")
    ap.add_argument("--dports", nargs="+", type=int, help="H-split: its two destination ports")
    args = ap.parse_args()

    if args.flow:
        try:
            protocol = TCP if args.tcp else UDP
            print(show_flow(port_number(args.flow[0]), port_number(args.flow[1]), protocol)[1])
        except ValueError as err:
            ap.error(str(err))
        return 0
    if not args.student:
        ap.error("--student is required")
    if args.sports or args.sport is not None:
        if not args.puzzle:
            ap.error("--sports and --sport need a puzzle name")
        answers = {args.puzzle: {"sports": args.sports or [], "dport": args.dport,
                                 "sport": args.sport, "dports": args.dports or []}}
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import hash_answers
        answers = hash_answers.ANSWERS

    all_solved = True
    for puzzle in [args.puzzle] if args.puzzle else PUZZLES:
        answer = answers.get(puzzle)
        print(f"== {puzzle}")
        if not answer:
            print("no answer yet in hash_answers.py")
            all_solved = False
            continue
        solved, canon, lines = judge(puzzle, answer)
        for line in lines:
            print(line)
        if solved:
            print(f"proof token {token(puzzle, args.student, canon)}  for {canon}")
        all_solved = all_solved and solved
    return 0 if all_solved else 1


if __name__ == "__main__":
    sys.exit(main())
