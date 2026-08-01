CC     ?= gcc
CSTD    = -std=c11
WARN    = -Wall -Wextra -Werror
# -fno-sanitize-recover is not optional: by default UBSan prints a diagnostic and
# lets the program carry on, so a run with real undefined behaviour still exits 0
# and CI goes green. This makes it abort like ASan does.
SAN     = -fsanitize=address,undefined -fno-sanitize-recover=all
CFLAGS  = $(CSTD) $(WARN) -O1 $(SAN)

# Any top-level directory containing .c files is a module. Modules land here as
# each kata gets good enough to promote out of the scratch directory.
ALL_MODULES := $(patsubst %/,%,$(sort $(dir $(wildcard */*.c))))

# `make test MODULE=ring_buffer` narrows any target to one module.
MODULES := $(if $(MODULE),$(MODULE),$(ALL_MODULES))

BUILD := build

help:
	@echo "make test                     build + run every module under ASan/UBSan"
	@echo "make test MODULE=ring_buffer  ... just one"
	@echo "make debug MODULE=ring_buffer build with -g -O0 for gdb (does not run it)"
	@echo "make analyze                  static analysis (gcc -fanalyzer), finds bugs without running"
	@echo "make valgrind MODULE=fsm      second opinion on memory behaviour (no sanitizers)"
	@echo "make test CC=clang            build with a second compiler"
	@echo "make list                     show which modules exist"
	@echo "make clean                    remove build/"
	@echo ""
	@echo "make log                      time curve per module, and who's at the 15-min bar"
	@echo "make check-log                validate log.tsv (CI runs this)"
	@echo ""
	@echo "See VERIFYING.md for how to read the output, LOGGING.md for the log."

test: | $(BUILD)
	@if [ -z "$(MODULES)" ]; then echo "no modules yet — see GETTING_STARTED.md"; fi
	@for m in $(MODULES); do \
	    echo "=== $$m ==="; \
	    $(CC) $(CFLAGS) $$m/*.c -o $(BUILD)/$$m && $(BUILD)/$$m || exit 1; \
	done

# Sanitizers stay on: they work fine under gdb and you want them there.
debug: | $(BUILD)
	@for m in $(MODULES); do \
	    echo "=== $$m (debug) ==="; \
	    $(CC) $(CSTD) $(WARN) -g -O0 $(SAN) $$m/*.c -o $(BUILD)/$$m-debug || exit 1; \
	    echo "built $(BUILD)/$$m-debug — run: gdb $(BUILD)/$$m-debug"; \
	done

# Advisory, not gating: -fanalyzer occasionally produces false positives, so read
# the path it prints rather than obeying it blindly. No -Werror for that reason.
analyze:
	@for m in $(MODULES); do \
	    echo "=== $$m (analyzer) ==="; \
	    for f in $$m/*.c; do \
	        $(CC) $(CSTD) -Wall -Wextra -fanalyzer -c $$f -o /dev/null || exit 1; \
	    done; \
	done
	@echo "analyzer clean"

# Valgrind and ASan conflict, so this build drops the sanitizers.
valgrind: | $(BUILD)
	@for m in $(MODULES); do \
	    echo "=== $$m (valgrind) ==="; \
	    $(CC) $(CSTD) $(WARN) -g -O1 $$m/*.c -o $(BUILD)/$$m-vg || exit 1; \
	    valgrind --error-exitcode=1 --leak-check=full \
	             --track-origins=yes $(BUILD)/$$m-vg || exit 1; \
	done

list:
	@echo "modules: $(if $(ALL_MODULES),$(ALL_MODULES),none yet)"

# The practice log. See LOGGING.md.
log:
	@python3 tools/check_log.py --summary

check-log:
	@python3 tools/check_log.py

$(BUILD):
	@mkdir -p $(BUILD)

clean:
	@rm -rf $(BUILD)

.PHONY: help test debug analyze valgrind list log check-log clean
.DEFAULT_GOAL := test
