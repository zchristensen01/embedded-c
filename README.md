# embedded-c

[![ci](https://github.com/zchristensen01/embedded-c/actions/workflows/ci.yml/badge.svg)](https://github.com/zchristensen01/embedded-c/actions/workflows/ci.yml)

Six embedded C fundamentals, each as a standalone module: header, implementation,
and a separate test file. C11, built with `-Werror` under AddressSanitizer and
UBSan, GCC and Clang, CI on every push.

```bash
make test
```

That is the bar: clone it, run that, watch everything pass.

## Modules

| Module | What it is | Brief |
| --- | --- | --- |
| `ring_buffer/` | Fixed-size queue over a fixed array; the ISR-to-main-loop handoff | [brief](ring_buffer/BRIEF.md) |
| `debouncer/` | Mechanical switch noise into single trustworthy edges | [brief](debouncer/BRIEF.md) |
| `fsm/` | Explicit state machine for a motor controller | [brief](fsm/BRIEF.md) |
| `bitops/` | Bit and multi-bit field access, the shape of register work | [brief](bitops/BRIEF.md) |
| `fixed_point_pid/` | Q16.16 PID with anti-windup and output saturation, no floating point | [brief](fixed_point_pid/BRIEF.md) |
| `protocol_parser/` | Byte-at-a-time framed-message parser that recovers from garbage | [brief](protocol_parser/BRIEF.md) |

Each directory carries a `NOTES.md`: what it does, one design decision and why,
and one thing that bit me.

## Documentation

| File | What's in it |
| --- | --- |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Which headers and types C actually gives you, how a module is laid out, how to write tests with no test framework, and a first session end to end |
| [VERIFYING.md](VERIFYING.md) | How to know a kata is correct — reading sanitizer output, what each warning means, and the checklist before a version earns a commit |
| `<module>/BRIEF.md` | What that kata is, why firmware needs it, the API, how to think about it, and what to test |
| [KATA_IDEAS.md](KATA_IDEAS.md) | Candidates for a seventh kata, and why not to start one yet |

## Build targets

```bash
make test                     # build + run every module under ASan/UBSan
make test MODULE=ring_buffer  # ... just one
make debug MODULE=ring_buffer # -g -O0 build for gdb
make analyze                  # gcc -fanalyzer: finds bugs without running the code
make valgrind MODULE=fsm      # second opinion on memory behaviour
make test CC=clang            # second compiler, different warnings
make list                     # which modules exist
```

## Build flags

```
-std=c11 -Wall -Wextra -Werror -O1
-fsanitize=address,undefined -fno-sanitize-recover=all
```

`-Werror` removes the option of ignoring a warning. ASan catches overruns and
use-after-free at the moment they happen instead of silently corrupting memory.
UBSan catches signed overflow, bad shifts, and misaligned access — the undefined
behaviour that happens to work on x86 and fails on ARM. `-O1` is enough
optimisation that the warnings needing dataflow analysis actually fire.
`-fno-sanitize-recover=all` makes UBSan abort rather than print a diagnostic and
continue, so a run with undefined behaviour in it cannot exit 0 and go green.

## How this repo relates to the drill

The daily practice is writing these from a blank file in a scratch directory and
deleting the result. This repo holds only the best version of each so far. A
module is replaced when a rewrite comes out genuinely better — interrupt-safe,
table-driven, branchless — not on a schedule. The history is meant to read as
iteration, not as a commit streak.
