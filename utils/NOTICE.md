# Third-party code in this folder

`run_exercise.py`, `p4_mininet.py`, `p4runtime_switch.py`, `netstat.py`, and
`p4runtime_lib/` come from [p4lang/tutorials](https://github.com/p4lang/tutorials)
(commit 098ce0b, `utils/`), under the Apache License 2.0 in
`LICENSE-Apache-2.0.txt`. `topo/pod-topo.png` comes from the same repository
(`exercises/basic/pod-topo/`).

Changes for CS 4220: none to the code. Our Makefile names P4Info files
`.p4info.txt` rather than `.p4info.txtpb`, because the p4c in the course image
predates the new suffix.

`checklib.py` and `part.mk` are ours. The P4 programs in `2-switching/` to
`2-tunnel/` are ours, written after the structure of p4lang's `basic`,
`load_balance`, and `source_routing` exercises.
