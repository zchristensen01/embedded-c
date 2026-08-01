# Verifying — how to know a kata is actually correct

Nobody is reviewing your code. Everything below is a substitute for that reviewer,
in rough order of how much work it saves you per minute spent.

---

## The short version

```bash
make test                    # all modules, sanitizers on
make test MODULE=ring_buffer # just one
make analyze                 # deep static analysis, finds bugs without running
make valgrind MODULE=fsm     # second opinion on memory behaviour
```

Green on all four, plus the checklist at the bottom, and it's good enough to commit.

---

## Layer 1 — the compiler, made strict

`-Wall -Wextra -Werror` means the compiler refuses to produce a program while
anything looks suspicious. Beginners often treat warnings as advisory noise; in
firmware they are usually the bug. Making them fatal removes the choice.

Warnings you'll hit constantly at first, and what they actually mean:

| Message | What it means | Usual fix |
| --- | --- | --- |
| `comparison of integer expressions of different signedness` | You compared a signed to an unsigned value. C converts the signed one, so `-1 > 5u` is **true**. A real source of infinite loops. | Make both `size_t`, or cast deliberately. |
| `unused parameter 'x'` | You declared a parameter you never used — often a sign you forgot part of the logic. | Use it, or delete it. |
| `'x' may be used uninitialized` | You're reading a variable before assigning it. Its value is whatever garbage was in that memory. | Initialise at declaration. |
| `implicit declaration of function` | You called a function the compiler has never seen. You forgot an `#include`, or misspelled it. | Add the header. |
| `control reaches end of non-void function` | A path through your function returns nothing. The caller gets garbage. | Add the missing `return`. |

Do not silence these with casts to make them go away. Understand each one. That's
the layer doing the most teaching.

---

## Layer 2 — the sanitizers

These add runtime checks. Your program gets slower and larger, and in exchange the
moment it does something illegal it stops and points at the line. This is the
closest thing you have to an experienced engineer looking over your shoulder.

### AddressSanitizer catches memory errors

Off-by-one, reading past the end of an array, use-after-free. Without ASan, an
off-by-one in a ring buffer silently reads a neighbouring byte and the program
*appears to work* — until it doesn't, on hardware, three weeks later.

Here is real output from a four-byte array written with `i <= 4` instead of `i < 4`:

```
==297893==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x72b8d7600024
WRITE of size 1 at 0x72b8d7600024 thread T0
    #0 0x5828144d53e0 in main asan_demo.c:7

Address 0x72b8d7600024 is located in stack of thread T0 at offset 36 in frame
    #0 0x5828144d52b8 in main

  This frame has 1 object(s):
    [32, 36) 'storage' (line 5) <== Memory access at offset 36 overflows this variable
```

How to read it:

1. **`stack-buffer-overflow`** — the kind of error. `stack` = a local variable.
2. **`WRITE of size 1`** — you were writing one byte. (`READ` would mean reading.)
3. **`in main asan_demo.c:7`** — the line that did it. Start here.
4. **`[32, 36) 'storage' (line 5)`** — the variable you ran off the end of, and
   where it was declared. `storage` legally occupies bytes 32–35; you touched 36.

Note that the compiler compiled this **without a single warning**. Static checking
could not see it. That's the case for sanitizers in one example.

### UndefinedBehaviorSanitizer catches illegal arithmetic

Signed overflow, shifting by too much, misaligned access — things that often
"work" on x86 and fail on ARM. Real output from `1u << 32`:

```
ubsan_demo.c:7:25: runtime error: shift exponent 32 is too large for 32-bit type 'unsigned int'
```

This exact bug is waiting for you in `bitops`, when a field width equals the full
word width.

> **Important, and easy to miss.** By default UBSan prints that diagnostic and then
> **lets the program carry on** — so a run containing real undefined behaviour still
> prints "all tests passed" and exits 0, and CI goes green. ASan aborts; UBSan
> doesn't. This repo's `CFLAGS` therefore include `-fno-sanitize-recover=all`, which
> makes UBSan abort too. If you're compiling by hand in your scratch directory,
> include that flag — otherwise you have a checker that reports bugs and passes
> anyway.

---

## Layer 3 — static analysis (`make analyze`)

`gcc -fanalyzer` simulates paths through your code without running it. It finds
things your tests never happened to trigger: a null pointer dereference on an
error path, a leak, a double free. It's slow and occasionally produces false
positives — read its reasoning rather than obeying it blindly. It prints the path
it took to reach the problem, which is the useful part.

---

## Layer 4 — Valgrind (`make valgrind MODULE=x`)

A second opinion. Valgrind emulates your program and watches every memory access.
It's much slower than ASan and overlaps with it heavily, but it catches
*uninitialised reads* particularly well — using a struct field you forgot to set in
your `init` function, for example. Worth running occasionally, not every session.

Note: Valgrind and ASan conflict, so `make valgrind` rebuilds without sanitizers.

---

## Layer 5 — a second compiler

GCC and Clang disagree about what's worth warning about, and the union of the two is
strictly better than either. CI runs both on every push. To reproduce locally:

```bash
sudo apt install clang
make test CC=clang
```

---

## The part no tool can do: deciding what would break it

Every layer above checks that your code doesn't do anything *illegal*. None of them
check that it does the *right thing*. That's your test file, and writing it is the
skill that actually transfers to the job — in an interview you will be asked how you
would test something far more often than you'll be asked to recite an algorithm.

A usable method: for each function, write down the answers to these, then assert
each one.

1. **What happens on an empty/fresh object?** Pop from an empty buffer. Update a
   debouncer that has never seen a change. Feed a parser one garbage byte.
2. **What happens at exactly the limit?** Not "nearly full" — *exactly* full, then
   one more. Not "around the threshold" — exactly on the tick the threshold is met.
3. **What happens one past the limit?** The push that must return `false`. The
   length byte larger than your payload buffer.
4. **What happens if it's used wrong?** An illegal event in a state that doesn't
   expect it. A field value too big for its width. The correct answer is usually
   "reject it and stay consistent," never "corrupt something."
5. **Does it still work the second time round?** Wrap the ring buffer past the end
   of the array several times. Parse two frames back to back. State that survives
   one cycle and breaks on the next is the classic embedded bug.
6. **Do the numbers still add up afterwards?** After any sequence of operations,
   `count` should equal pushes minus pops. Frames OK plus frames bad should equal
   frames fed. These invariant checks catch bugs your specific test cases missed.

If a test never fails while you're writing it, you probably wrote it to match the
code rather than the specification. Try deliberately breaking your implementation —
change a `<` to `<=` — and confirm a test goes red. A test suite that can't detect a
broken implementation isn't testing anything.

---

## Checklist before promoting a version into this repo

The drill version lives in a scratch directory and gets deleted. A version earns a
place here only when all of this is true:

- [ ] `make test MODULE=x` passes, with zero warnings and zero sanitizer output.
- [ ] `make analyze` is clean for that module.
- [ ] It is split into `x.h`, `x.c`, `test_x.c`, and the header has an include guard.
- [ ] No `malloc` anywhere. The caller supplies all storage.
- [ ] No `printf` outside the test file.
- [ ] Every function on the "tests it must pass" list in the brief has a test.
- [ ] You deliberately broke the implementation and watched a test catch it.
- [ ] `NOTES.md` is filled in — what it does, one design decision and why, one thing
      that bit you.
- [ ] **It is better than what is already in the repo.** Not different — better.
      Interrupt-safe, table-driven, branchless, or genuinely clearer. If it's merely
      equivalent, delete it and keep drilling.

That last one is the rule that keeps the commit history honest. In practice a file
gets replaced every third or fourth pass. Nobody is impressed by daily commits;
people are impressed by a module that visibly got better three times.
