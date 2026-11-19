# Shared rules for part 2's packet tests (2-switching/, 2-tunnel/). Each Makefile
# sets P4, PORTS and SETUP, then includes this file. Run inside the course
# container, started with --privileged.
#
#   make test    compile your program and run the packet tests against it
#   make linux   run the same tests against the Linux bridge or tunnel in linux.sh
#   make clean   remove build/
UTILS := ../utils

test:
	python3 $(UTILS)/ptfrun.py $(P4) --ports $(PORTS) --setup "$(SETUP)"

linux:
	python3 $(UTILS)/ptfrun.py $(P4) --ports $(PORTS) --linux "sh linux.sh"

clean:
	rm -rf build

.PHONY: test linux clean
