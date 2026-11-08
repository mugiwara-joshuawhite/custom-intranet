"""Part 3 challenge route: your answers. You fill in both.

Every flow is UDP from h1 (10.0.1.1) to h3 (10.0.3.3).
H-same: four different source ports within 8 consecutive numbers and one
destination port, for example {"sports": [1000, 1001, 1002, 1003], "dport": 5201}.
H-split: one source port and two different destination ports, for example
{"sport": 1000, "dports": [5201, 5202]}.
Check them with python3 hash_puzzles.py --student your_id.
"""

ANSWERS = {
    "H-same": None,
    "H-split": None,
}
