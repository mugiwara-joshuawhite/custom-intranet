# Shared build rules. Each part's Makefile sets P4 (its program) and TOPO,
# then includes this file. Everything runs as root inside the course container.
#
#   make          compile the P4 program
#   make run      start the network with a Mininet prompt (type exit to leave)
#   make check    start the network, run this part's checks, and stop it
#   make test     run this part's packet tests against one switch (parts with tests/)
#   make stop     clean up a network left running by a crash
#   make clean    remove build output and logs

BUILD  := build
NAME   := $(basename $(notdir $(P4)))
JSON   := $(BUILD)/$(NAME).json
P4INFO := $(BUILD)/$(NAME).p4.p4info.txt
UTILS  := ../utils

all: $(JSON)

$(JSON): $(P4)
	mkdir -p $(BUILD) logs pcaps
	p4c-bm2-ss --p4v 16 --p4runtime-files $(P4INFO) -o $(JSON) $(P4)

run: $(JSON)
	python3 $(UTILS)/run_exercise.py -t $(TOPO) -j $(JSON) -b simple_switch_grpc

check: $(JSON)
	python3 check.py

test:
	python3 $(UTILS)/ptfrun.py $(P4) --ports $(PORTS) --setup "$(SETUP)"

stop:
	mn -c > /dev/null 2>&1 || true

clean: stop
	rm -rf $(BUILD) logs pcaps

.PHONY: all run check test stop clean
