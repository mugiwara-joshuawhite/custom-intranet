# Custom Intranet (Project 4): a software-defined network in P4

You build a small network's switches in P4, one job at a time. The folders are in the order you work through them. The instructions and questions are on each part's Canvas page; keep this one folder for the whole project.

| Folder | Who does it | Due |
| :--- | :--- | :--- |
| 1-routing/ | Part 1, routing: everyone | Wed Nov 18 |
| 2-switching/ and 2-tunnel/ | Part 2, switching and a tunnel: everyone, one submission | Wed Dec 2 |
| final-controller/ and final-ecmp/ | The final option, controller and ECMP: only if you choose it in place of the written final | Fri Dec 11 |
| extra-source-routing/ | Extra credit, source routing: optional | Mon Dec 14 |

## Files

| Folder | Contents | What you do |
| :--- | :--- | :--- |
| topo/ | Four hosts, two edge switches, two spines: pod-topo.png and topology.json | nothing, it is given |
| 1-routing/ | The routing data plane: forwarding.p4, the supplied runtime entries, check.py and tests/ | complete forwarding.p4 at YOUR TASK |
| 1-routing/analyze/ | Recorded make check runs of a correct data plane and three bugged ones (mystery-A to mystery-C), each with check.txt, trace.txt, frames.txt and pcaps/. Practice, and the fallback if your container will not run | read them |
| 1-routing/lpm_puzzles.py, lpm_tables.json, lpm_answers.py | Four longest-prefix-match puzzles and every switch's table entries, for practice | optional: fill in ANSWERS |
| 2-switching/ | A learning switch: switching.p4, the given controller.py, linux.sh (a Linux bridge) and tests/ | complete switching.p4 at YOUR TASK |
| 2-tunnel/ | A GRE tunnel: tunnel.p4, tables.json, linux.sh (a Linux GRE tunnel) and tests/ | complete tunnel.p4 at YOUR TASK |
| final-controller/ | The controller: routing.py and the P4Runtime driver controller.py | write next_hops() in routing.py |
| final-controller/analyze/ | Recorded next_hops() tables: the correct controller before and after s1-s3 fails, and mystery-A to mystery-D, for practice | read them |
| final-controller/route_puzzles.py, route_suspects.json, route_answers.py | Three controller puzzles, for practice | optional: fill in ANSWERS |
| final-ecmp/ | ECMP: ecmp.p4, routing_ecmp.py (which imports your final-controller/routing.py), controller.py and tests/ | complete both at YOUR TASK |
| final-ecmp/analyze/ | Recorded make check runs (reference, mystery-D, mystery-F) and nine recorded iperf3 runs in flow-runs.txt, for practice | read them |
| final-ecmp/hash_puzzles.py, hash_answers.py | Two puzzles on s1's ECMP hash, for practice | optional: fill in ANSWERS |
| extra-source-routing/ | Source routing: source_routing.p4 and the helper send_route.py | complete source_routing.p4 at YOUR TASK |
| extra-source-routing/analyze/, stack_puzzles.py, stack_answers.py | Recorded runs (reference, mystery-E) and two port-stack puzzles, for practice | optional: fill in ANSWERS |
| utils/ | The p4lang runner, the P4Runtime library, the check harness and ptfrun.py, which runs the packet tests | nothing, it is given |

Leave these as they are, because grading restores clean copies: check.py, controller.py, send_route.py, every tests/ folder, linux.sh, tables.json, ptf-tables.json, the puzzle runners and their data files, every analyze/ folder, the runtime entries and utils/.

## Run

Start the course container from a part's folder (the course environment help page says how to build or pull the image):

```text
docker run --rm -it --privileged --network none -v "$PWD":/work cs4220-net
```

Then, inside it:

| Command | What it does |
| :--- | :--- |
| make | Compile the P4 program |
| make test | Parts 1 and 2 and ECMP: compile, start the switch, run the packet tests; ends with how many passed and which capture to open |
| make linux | Part 2: run the same tests against the Linux bridge or GRE tunnel in linux.sh, to compare |
| make check | Part 1, the controller and source routing: start the network, run the checks, then stop it |
| make run | Open an interactive Mininet prompt |
| make stop | Clean up after an interrupted run |
| make clean | Remove build/ |

Captures land in build/pcaps/ (your switch: _in.pcap arrived on a port, _out.pcap left it) and build/pcaps-linux/ (the Linux device). If you set up the container before 9 November, run `docker pull git.trevon.dev/cs4220/cs4220-net:fall26` once first: the image now includes the packet-test tool, PTF.

Some parts also run on plain Python 3, without the container, each from its own folder:

```text
python3 routing.py                      # final-controller/: print the next-hop tables
python3 routing.py --down s1-s3         # the same, with one link cut
python3 lpm_puzzles.py --student your_id
python3 route_puzzles.py --student your_id
python3 hash_puzzles.py --student your_id
python3 stack_puzzles.py --student your_id
```

Source routing's helper runs on a host at the Mininet prompt:

```text
h1 python3 send_route.py DEST_IP "PORT PORT..." [MESSAGE]
```

For a second shell in the running container, see [docker exec](https://docs.docker.com/reference/cli/docker/container/exec/).
