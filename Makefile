CC     ?= gcc
CFLAGS  = -std=c11 -Wall -Wextra -Werror -O1 \
          -fsanitize=address,undefined

# Any top-level directory containing .c files is a module. Modules land here as
# each kata gets good enough to promote out of the scratch directory.
MODULES := $(patsubst %/,%,$(sort $(dir $(wildcard */*.c))))

BUILD := build

test: | $(BUILD)
	@if [ -z "$(MODULES)" ]; then echo "no modules yet"; fi
	@for m in $(MODULES); do \
	    echo "=== $$m ==="; \
	    $(CC) $(CFLAGS) $$m/*.c -o $(BUILD)/$$m && $(BUILD)/$$m || exit 1; \
	done

$(BUILD):
	@mkdir -p $(BUILD)

clean:
	@rm -rf $(BUILD)

.PHONY: test clean
