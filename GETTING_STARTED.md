# Getting started

Read this once, properly. It covers the things that are assumed knowledge in every
kata brief: what C actually gives you, how a module is laid out, and how to write a
test when there is no test framework.

---

## 1. The uncomfortable answer about libraries

> "I don't understand what libraries I need to call in, or what methods to use from
> them."

**There aren't any.** That is not a gap in your knowledge — it is the actual answer,
and it is the reason these six exercises exist.

In JavaScript or Python you would `npm install` a ring buffer. In firmware you
cannot, for reasons that are practical rather than ideological:

- There is often no filesystem, no package manager, and no operating system.
- You may have 20 KB of RAM total. A general-purpose library is unaffordable.
- Somebody has to be able to read every line that ships, because a bug means a
  physical device in someone's hands stops working and cannot be hot-fixed.

So embedded C has a tiny standard library and you write the rest. These katas *are*
the things that would be libraries elsewhere. When a brief says "implement
`rb_push`", there is no import that does it for you — you are the library.

### The entire set of headers you will use

A "header" (`#include <something.h>`) is C's version of an import. Here is
realistically all you need across all six katas:

| Header | What it gives you | You'll use it for |
| --- | --- | --- |
| `<stdint.h>` | `uint8_t`, `uint16_t`, `uint32_t`, `int32_t`, `int64_t` | Exact-width integers. Nearly every kata. |
| `<stdbool.h>` | `bool`, `true`, `false` | Return values like "did that work?" |
| `<stddef.h>` | `size_t`, `NULL` | Sizes, counts, and array indices. |
| `<string.h>` | `memcpy`, `memset` | Copying/zeroing blocks of bytes. |
| `<assert.h>` | `assert(...)` | Your entire test framework. |
| `<stdio.h>` | `printf` | Printing in tests **only** — see the note below. |

That's it. No third-party anything. If you find yourself wanting a header that isn't
on this list, you have probably drifted away from the exercise.

> **Note on `printf`.** It's fine in a test file that runs on your laptop. On a real
> microcontroller `printf` can pull in 10–20 KB of formatting code and blow your
> entire flash budget, which is why embedded people are strange about it. Never put
> it inside a module — only inside `test_*.c`.

### Why `uint8_t` and not `int`

This trips up everyone coming from a higher-level language. In C, `int` does not
have a guaranteed size. On your laptop it's 32 bits; on some microcontrollers it's
16. Code that assumes 32 works on your desk and corrupts data on the target.

`<stdint.h>` gives you types that state their size out loud:

| Type | Size | Range | Read it as |
| --- | --- | --- | --- |
| `uint8_t` | 8 bits | 0 … 255 | "one byte" |
| `uint16_t` | 16 bits | 0 … 65,535 | "two bytes" |
| `uint32_t` | 32 bits | 0 … ~4.29 billion | "a register" |
| `int32_t` | 32 bits | ~±2.1 billion | "a signed register" |
| `int64_t` | 64 bits | very large | "scratch space for a multiply" |
| `size_t` | platform | 0 … big, **never negative** | "a count or an index" |

The `u` means unsigned — no negative values. This matters more than it sounds:
unsigned types wrap around cleanly from max back to zero, which several of these
katas depend on, while signed overflow is *undefined behaviour* and UBSan will stop
your program dead for it.

---

## 2. What a module looks like

Every kata directory ends up with the same three files. The split is not decoration
— it's how firmware is organised, and it's the thing that makes each directory
liftable into a real project.

```
ring_buffer/
    ring_buffer.h        the menu    — what exists, for other people to read
    ring_buffer.c        the kitchen — how it works, nobody needs to read this
    test_ring_buffer.c   the critic  — proof it does what the menu claims
    NOTES.md             three lines about what you learned
```

### The header (`.h`) — the menu

Contains your `typedef struct`s and your function **declarations** (signature and
semicolon, no body). Anyone who wants to use your module reads only this file.

```c
#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ... your types and function declarations go here ... */

#endif /* RING_BUFFER_H */
```

The `#ifndef / #define / #endif` sandwich is an **include guard**. `#include`
literally pastes the file's text in place, so if two files both include this one,
the compiler would see your struct defined twice and error out. The guard means
"if this hasn't been pasted yet, paste it; otherwise skip." Every header has one.
Get in the habit — it's muscle memory, not a decision.

### The implementation (`.c`) — the kitchen

Starts with `#include "ring_buffer.h"` (quotes for your own files, angle brackets
for system ones) and then contains the function **definitions** — the same
signatures, now with bodies.

Anything that is a helper used only inside this file should be marked `static`.
That means "not visible outside this file," which is C's version of `private`.

### The test (`test_*.c`) — the critic

Includes the header and contains `main()`. This is the program that actually runs.
`make test` compiles all the `.c` files in the directory together, so the test file
and the implementation become one binary.

---

## 3. Writing tests when there is no test framework

There is no Jest, no pytest. There is `assert()`, and it is enough.

`assert(condition)` does nothing if the condition is true, and if it's false it
prints the file and line number and kills the program immediately. That's the whole
API.

Here is a complete, working example. It is deliberately **not** one of the six
katas — it's a `clamp` function, so you can see the shape without being handed an
answer:

```c
/* test_example.c — the pattern, on a throwaway function */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>

static int32_t clamp(int32_t v, int32_t lo, int32_t hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static void test_inside_range(void)
{
    assert(clamp(5, 0, 10) == 5);
}

static void test_outside_range(void)
{
    assert(clamp(-3, 0, 10) == 0);
    assert(clamp(99, 0, 10) == 10);
}

static void test_exact_boundaries(void)
{
    /* The edges are where bugs live. > vs >= is an entire class of bug. */
    assert(clamp(0,  0, 10) == 0);
    assert(clamp(10, 0, 10) == 10);
}

int main(void)
{
    test_inside_range();
    test_outside_range();
    test_exact_boundaries();

    printf("all tests passed\n");
    return 0;
}
```

Four things to copy from this shape:

1. **One `static void test_thing(void)` per behaviour**, called from `main`. When an
   assert fires you get a line number, but a named function tells you what you
   *meant*, and it stops the tests turning into forty unlabelled lines.
2. **Test the boundaries, not the middle.** `clamp(5, 0, 10)` was never going to
   fail. `clamp(10, 0, 10)` is where you find out whether you wrote `>` or `>=`.
3. **Print something at the end.** A passing assert is silent, so with no final
   `printf` a successful run looks identical to a run that did nothing.
4. **Assert the failures too.** Not just "push works" but "push into a full buffer
   returns false *and doesn't corrupt anything*." Deciding what would break the
   thing is the part that transfers to the job.

> **Gotcha:** `assert` is compiled out entirely if `NDEBUG` is defined. This repo
> never defines it, so you're fine — but if you ever see all your tests
> mysteriously "pass" instantly, that's why.

---

## 4. Your first session, end to end

**Do not start in this repo.** The drill is writing from a blank file; the repo only
receives a version once it's genuinely good. Work in a scratch directory:

```bash
mkdir -p ~/scratch && cd ~/scratch
```

Read `ring_buffer/BRIEF.md` from this repo, then close it and open an empty file.
Write the struct, the functions, and a `main()` with four or five assertions that
try to break it. All in one file is fine while drilling — the three-file split is a
repo concern, not a drill concern.

Then compile it. This single line is doing most of the teaching:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    ring_buffer.c -o rb && ./rb
```

| Part | What it does |
| --- | --- |
| `gcc` | The compiler. |
| `-std=c11` | Use the 2011 version of C. Fixes which language you're writing. |
| `-Wall -Wextra` | Turn on the warnings that catch real bugs. |
| `-Werror` | Make warnings **fatal**. Removes the option of ignoring them, which is the entire point. |
| `-O1` | Optimise a little — enough that the warnings needing dataflow analysis actually fire. |
| `-fsanitize=address` | Add runtime checks for buffer overruns and use-after-free. |
| `-fsanitize=undefined` | Add runtime checks for signed overflow, bad shifts, misaligned access. |
| `-fno-sanitize-recover=all` | Make a sanitizer error **stop the program**. Without it UBSan prints a complaint and carries on, so your tests "pass" with a real bug in them. |
| `ring_buffer.c` | Your file. |
| `-o rb` | Name the output program `rb`. |
| `&& ./rb` | If it compiled, run it. |

When it's clean and the assertions pass — **delete the file**. That's the exercise.
Next week you write it again, and the second time the wraparound arithmetic will be
automatic and you'll be thinking about whether it's safe to call from an interrupt.
That shift is the entire point, and there is no way to buy it other than repeating.

See [VERIFYING.md](VERIFYING.md) for how to read the output when it isn't clean, and
for the checklist a version has to pass before it earns a place in this repo.

---

## 5. Jargon decoder

Terms that appear in the briefs without explanation.

| Term | Plain version |
| --- | --- |
| **Firmware** | Software that runs on a device with no operating system, controlling hardware directly. |
| **MCU / microcontroller** | A whole computer on one chip. Slow, tiny memory, no OS. An Arduino or STM32 is one. |
| **Register** | A special memory address wired to hardware. Writing a number to it physically changes a pin, starts a timer, etc. |
| **ISR / interrupt** | A function the hardware calls *immediately*, interrupting whatever was running, when an event occurs (a byte arrived, a timer expired). It must finish in microseconds. |
| **Main loop / superloop** | `while (1) { ... }` — the thing running forever when no interrupt is firing. |
| **UART / serial** | The most common way two devices exchange bytes over two wires. |
| **Baud rate** | Bits per second on a serial line. 115200 baud ≈ a byte every 87 microseconds. |
| **Polling** | Repeatedly asking "has it happened yet?" — the opposite of interrupts. |
| **Datasheet** | The chip manufacturer's manual. Says things like "bits 5:4 select the clock prescaler." |
| **Flash** | Where the program is stored. Usually the tightest budget you have. |
| **Undefined behaviour (UB)** | Code the C standard gives no meaning to. The compiler may do anything, including something that works on your laptop and fails on ARM. |
| **`volatile`** | "This value can change without the compiler seeing it change" — so don't optimise away reads of it. Required for hardware registers and for variables shared with an ISR. |
| **Atomic** | Happens all at once; can't be interrupted halfway through. Most operations are *not* atomic, which is where the hard bugs live. |
