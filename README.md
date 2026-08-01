# embedded-c

Six embedded C fundamentals, each as a standalone module: header, implementation,
and a separate test file. C11, built with `-Werror` under AddressSanitizer and
UBSan, CI on every push.

```
make test
```

That is the bar: clone it, run that, watch everything pass.

## Modules

| Module | What it is |
| --- | --- |
| `ring_buffer/` | Fixed-size queue over a fixed array; the ISR-to-main-loop handoff |
| `debouncer/` | Mechanical switch noise into single trustworthy edges |
| `fsm/` | Explicit state machine for a motor controller |
| `bitops/` | Bit and multi-bit field access, the shape of register work |
| `fixed_point_pid/` | Q16.16 PID with anti-windup and output saturation, no floating point |
| `protocol_parser/` | Byte-at-a-time framed-message parser that recovers from garbage |

Each directory carries a `NOTES.md`: what it does, one design decision and why,
and one thing that bit me.

## Build flags

```
-std=c11 -Wall -Wextra -Werror -O1 -fsanitize=address,undefined
```

`-Werror` removes the option of ignoring a warning. ASan catches overruns and
use-after-free at the moment they happen instead of silently corrupting memory.
UBSan catches signed overflow, bad shifts, and misaligned access — the undefined
behaviour that happens to work on x86 and fails on ARM. `-O1` is enough
optimisation that the warnings needing dataflow analysis actually fire.

## How this repo relates to the drill

The daily practice is writing these from a blank file in a scratch directory and
deleting the result. This repo holds only the best version of each so far. A
module is replaced when a rewrite comes out genuinely better — interrupt-safe,
table-driven, branchless — not on a schedule. The history is meant to read as
iteration, not as a commit streak.
