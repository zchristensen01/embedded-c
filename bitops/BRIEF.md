# Kata 04 — Bit Manipulation

**In one sentence.** Setting, clearing, toggling and testing individual bits, and
reading or writing multi-bit fields inside a word.

New to this? Read [GETTING_STARTED.md](../GETTING_STARTED.md) first.

---

## The problem, in plain language

A `uint32_t` is 32 individual on/off switches that happen to be stored together. In
firmware you constantly need to flip switch number 7 without disturbing the other 31.

You cannot address a bit directly — the smallest thing C can load or store is a byte.
So you do arithmetic on the whole word using four operators:

| Operator | Name | What it does |
| --- | --- | --- |
| `&` | AND | Result bit is 1 only if **both** inputs are 1. Used to **keep** bits. |
| `\|` | OR | Result bit is 1 if **either** input is 1. Used to **set** bits. |
| `^` | XOR | Result bit is 1 if inputs **differ**. Used to **flip** bits. |
| `~` | NOT | Flips every bit. Turns a "keep these" mask into a "clear these" mask. |
| `<<` `>>` | shift | Slide every bit left or right by n places. |

> **Careful:** `&` and `|` are *bitwise*; `&&` and `||` are *logical* (true/false).
> `5 & 2` is `0`. `5 && 2` is `1`. Typing the wrong one compiles fine and does
> something completely different. This is a genuine, common bug.

Everything is built from one idea: **make a mask, then combine it.**

`1u << n` produces a word with a single 1 in position n:

```
1u << 0  ->  0000 0000 0000 0000 0000 0000 0000 0001
1u << 3  ->  0000 0000 0000 0000 0000 0000 0000 1000
1u << 31 ->  1000 0000 0000 0000 0000 0000 0000 0000
```

From there: OR with it to set that bit, AND with its inverse to clear it, XOR to
toggle, AND to test.

A **field** is several adjacent bits treated as one number. A datasheet says "bits
5:4 select the clock prescaler" — that's a 2-bit field at position 4, holding 0–3. To
read it you shift the word right until the field is at the bottom, then mask off
everything above it. To write it you clear the old field, mask the new value to size,
shift it into place, and OR it in.

---

## Why firmware needs this

**Register access *is* bit manipulation.** This is the most directly employable item
on the list.

Configuring any peripheral means reading a datasheet sentence like "bits 5:4 select
the clock prescaler; 00 = /1, 01 = /2, 10 = /4" and turning it into code. Enabling a
GPIO clock, unmasking an interrupt, setting a UART baud divisor, packing a status
word into a CAN frame — all the same handful of operations, all day, for your entire
career in this field.

The failure mode this kata is really about: **read-modify-write on a hardware
register is not atomic.** `REG |= (1u << 3)` looks like one operation. It is three:
load the register, OR in the bit, store it back. If an interrupt fires in the middle
and modifies a *different* bit of the same register, your store writes back the stale
value and that other change silently vanishes. Hunting that bug for two days is a
rite of passage. Some chips provide bit-band aliases or separate set/clear registers
precisely to avoid it.

---

## What you need from C

```c
#include <stdint.h>   /* uint32_t */
#include <stdbool.h>  /* bool */
```

Three details that separate people who have done this from people who have read about
it. Expect to be asked about all three.

**Why `1u << n` and not `1 << n`.** Plain `1` is a *signed* `int`. `1 << 31`
therefore shifts a bit into the sign position of a signed type, which is undefined
behaviour — the compiler may do anything. `1u` is unsigned, where the same shift is
perfectly defined. It costs one character and removes a whole class of bug. UBSan
will catch you if you forget.

**Why `uint32_t` and not `int`.** `int` has no guaranteed width and is signed, so
shifts and overflow have surprising rules. Hardware registers are a specific number
of bits and you should say which. Also: C's *integer promotion* rules silently
convert `uint8_t` and `uint16_t` to `int` in arithmetic, which is a frequent source
of sign-comparison warnings. Using `uint32_t` sidesteps most of it.

**Shifting by the full word width is undefined.** `1u << 32` on a 32-bit type is not
"zero" — it's UB, and on x86 it typically produces `1` because the CPU only looks at
the bottom 5 bits of the shift count. Real output from this repo's flags:

```
runtime error: shift exponent 32 is too large for 32-bit type 'unsigned int'
```

This matters here because the obvious way to build a mask —
`(1u << width) - 1u` — breaks exactly when `width == 32`, which is a legitimate
argument to `field_get`. Handle it deliberately.

---

## The API you are writing

```c
static inline uint32_t bit_set   (uint32_t w, unsigned n);
static inline uint32_t bit_clear (uint32_t w, unsigned n);
static inline uint32_t bit_toggle(uint32_t w, unsigned n);
static inline bool     bit_test  (uint32_t w, unsigned n);

/* Multi-bit fields */
uint32_t field_get(uint32_t word, unsigned lsb, unsigned width);
uint32_t field_set(uint32_t word, unsigned lsb, unsigned width,
                   uint32_t value);

/* Common utilities */
unsigned popcount           (uint32_t w);  /* how many bits are set */
unsigned count_leading_zeros(uint32_t w);
uint32_t reverse_bits       (uint32_t w);
bool     is_power_of_two    (uint32_t w);
```

Notes:

- These take a word and **return a new word** rather than modifying in place. Easier
  to test, and it composes: `w = bit_set(bit_clear(w, 3), 7);`
- `static inline` in a header means "paste this function body at each call site
  instead of making a real call." For a one-line bit operation the function call
  overhead would exceed the work, and in firmware that matters. `static` keeps it
  from colliding across files.
- `lsb` = least significant bit, the position where the field starts. `width` = how
  many bits it spans. "Bits 5:4" is `lsb = 4, width = 2`.
- `count_leading_zeros` counts zeros above the highest set bit. It's how you find the
  top bit quickly, and ARM has a single instruction for it (`CLZ`). Decide what your
  version returns for input `0` and write it down — the hardware instruction and
  various libraries disagree, which is itself a good thing to know.

**`field_set` must mask the incoming value to `width` bits** so that an oversized
argument cannot spill into neighbouring fields. Get this wrong and passing `7` to a
2-bit field silently corrupts the setting next door — which on real hardware might be
a clock source or an interrupt enable. It's a real bug and it is miserable to find.

---

## How to think about it

For each operation, write the mask first and the expression second:

1. To **set** bit n: what mask, combined with which operator?
2. To **clear** bit n: you need a word that's all 1s except position n. How do you
   build it from `1u << n`?
3. To **test** bit n: masking gives you `0` or `1u << n`, not `0` or `1`. How do you
   turn that into a `bool` cleanly?
4. To **read** a field: shift then mask, or mask then shift? Both can work — which is
   simpler?
5. To **write** a field: there are four steps and the order matters. Clearing the old
   field is the one people forget, which makes `field_set` behave like OR — it can set
   bits but never clear them.
6. What does your mask expression do when `width == 32`? (See above. Handle it.)

`popcount` and `reverse_bits` are simple loops on the first pass. Write the obvious
version; the clever version is the third pass.

---

## Tests it must pass

The good news: this kata has exact, checkable answers. Use hex literals and known
values.

| Test | What it's protecting against |
| --- | --- |
| Bit 0 **and** bit 31 both behave | The edges — bit 31 is where the `1u` problem shows up |
| `field_get`/`field_set` round-trip for several positions and widths, **including a field at the very top of the word** | Shift-by-32 and sign issues at the boundary |
| `field_set` with an oversized value does not disturb bits outside the field | The masking bug described above |
| A width equal to the full word width does not shift by 32 | Undefined behaviour. UBSan will catch it if you let it happen |
| `popcount` and `reverse_bits` against known values, including `0` and `0xFFFFFFFF` | Loop bounds and the empty/full edges |

Round-tripping is the highest-value test here: for a range of `lsb` and `width`
combinations, `field_get(field_set(w, lsb, width, v), lsb, width) == v`. One nested
loop covers dozens of cases you'd never enumerate by hand.

---

## Once it's boring

**Second pass — a fake peripheral.** Define a struct of `volatile uint32_t` registers
and write a small driver against it, so you practise the real shape rather than free
functions on plain integers:

```c
typedef struct {
    volatile uint32_t CTRL;
    volatile uint32_t STATUS;
    volatile uint32_t DATA;
} fake_uart_t;
```

On real hardware you'd point that struct at a fixed address from the datasheet; in a
test you point it at a normal variable and can inspect what your driver wrote. This
is exactly how vendor headers (CMSIS on ARM) are structured.

**Third pass — branchless and loopless.** Implement `popcount` and `reverse_bits`
with no loops or branches (look up the parallel bit-counting and shift-and-mask
techniques), then compare in [Compiler Explorer](https://godbolt.org) against
`__builtin_popcount`. On ARM with the right flags the compiler emits a single
instruction, and seeing your twelve clever lines lose to one intrinsic is a useful
lesson about when to be clever.

---

> **Log slugs:** `plain` → `peripheral` → `branchless`. Record each session in
> [log.tsv](../log.tsv) under the variant you actually wrote — time is only
> comparable within a variant. See [LOGGING.md](../LOGGING.md).

## The publishable angle

**The highest depth-per-word writeup available to you: "what `volatile` actually
does."** Take a loop that polls a status register, compile it twice — once with
`volatile`, once without — and show the ARM assembly side by side. In one build the
read is inside the loop; in the other the compiler has hoisted it out and your code
polls a value that can never change, so it hangs forever.

Short, unambiguously technical, and it demonstrates that you read generated code —
which most candidates do not.
