# Kata 01 — Ring Buffer

**In one sentence.** A fixed-size queue laid over a fixed array, where the write
position wraps back to the start when it reaches the end.

New to this? Read [GETTING_STARTED.md](../GETTING_STARTED.md) first — it explains
the headers, types, and test style assumed here.

---

## The problem, in plain language

You have a fast producer and a slow consumer, and no way to pause the producer.

Bytes arrive from a serial cable one at a time, at unpredictable moments. Something
has to hold them until the main program is ready. A normal queue would need to
allocate memory (not allowed here) or shuffle every element down by one on each read
(too slow, and it gets slower as the queue grows).

The trick: use one fixed array and two position markers.

- **`head`** — where the next byte gets written.
- **`tail`** — where the next byte gets read.

Both only ever move forward. When either reaches the end of the array, it wraps
around to index 0 — hence "ring." Nothing is ever shuffled. Pushing and popping are
the same cost whether the buffer holds 1 item or 1000.

```
capacity 8, three bytes in it:

  index:  0    1    2    3    4    5    6    7
        [ .    .    A    B    C    .    .    . ]
                    ^              ^
                   tail           head
                (read here)   (write here)

after wrapping around, five bytes in it:

  index:  0    1    2    3    4    5    6    7
        [ X    Y    .    .    .    .    V    W ]
                    ^                   ^
                   head                tail
```

Notice the second picture: the data is "in order" V, W, X, Y even though it looks
scrambled in the array. Order is defined by walking forward from `tail`, wrapping at
the end — not by array position.

### The one genuinely interesting question

When `head == tail`, is the buffer **empty** or **completely full**?

Both states look identical. You cannot tell them apart from the indices alone. There
are exactly two standard answers:

1. **Keep a `count` field.** Increment on push, decrement on pop. Empty is
   `count == 0`, full is `count == capacity`. Simple, uses the whole array, and you
   have the count for free when someone asks. But three variables must stay
   consistent with each other, which becomes a problem when an interrupt is involved
   (see *Levelling up*).
2. **Sacrifice one slot.** Never let `head` catch up to `tail`; "full" means head is
   one position behind tail. Empty is `head == tail`. Now only two variables exist,
   and each one is written by exactly one party — which is what makes the lock-free
   version possible. The cost is one wasted byte of an eight-byte buffer.

**Choosing between these and being able to explain the tradeoff is most of what this
exercise is for.** Do the `count` version first because it's easier to get right.
Put your reasoning in `NOTES.md`.

---

## Why firmware needs this

This is the structure for every place data crosses from an interrupt into the main
loop, which is to say: everywhere.

A UART receive interrupt fires once per arriving byte. At 115200 baud that's roughly
every 87 microseconds. That handler cannot parse a command, cannot write to a
display, cannot do anything slow — the next byte is already on its way and if you're
still busy when it lands, the hardware overwrites it and the byte is **gone**. So the
handler does exactly one thing: drop the byte into a ring buffer and return. The main
loop drains the buffer whenever it gets around to it.

Same structure for ADC samples, CAN frames, log messages, keypress events, and audio.

It is also the single most common embedded whiteboard question. You will be asked to
write this at an interview.

---

## What you need from C

```c
#include <stdint.h>   /* uint8_t  */
#include <stdbool.h>  /* bool, true, false */
#include <stddef.h>   /* size_t */
```

Three concepts, if they're new:

**The modulo operator `%`** gives the remainder of a division, and it's how wrapping
is expressed: `(head + 1) % capacity`. If capacity is 8 and head is 7, that's
`8 % 8` = 0 — back to the start. If head is 3, that's `4 % 8` = 4 — just forward one.
One expression, both cases.

**Pointers.** `rb_t *rb` means "the address of an `rb_t`, not a copy of it." C passes
copies by default, so a function taking `rb_t rb` could not modify the caller's
buffer. You reach through a pointer with `->`: `rb->head` means "the `head` field of
the thing `rb` points at." And `*out = value` means "write into the variable the
caller gave me the address of" — that's how `rb_pop` hands a byte back while also
returning true/false.

**`const` on a parameter** (`const rb_t *rb`) is a promise that the function only
reads, never modifies. It's documentation the compiler enforces. The three query
functions take `const`; push and pop don't.

---

## The API you are writing

```c
typedef struct {
    uint8_t  *buf;       /* points at storage the caller owns */
    size_t    capacity;  /* how many bytes that storage holds */
    size_t    head;      /* write index */
    size_t    tail;      /* read index  */
    size_t    count;     /* how many bytes are currently in it */
} rb_t;

void   rb_init(rb_t *rb, uint8_t *storage, size_t capacity);
bool   rb_push(rb_t *rb, uint8_t byte);   /* false if full  */
bool   rb_pop (rb_t *rb, uint8_t *out);   /* false if empty */
bool   rb_is_empty(const rb_t *rb);
bool   rb_is_full (const rb_t *rb);
size_t rb_count   (const rb_t *rb);
```

Line by line:

- `uint8_t *buf` — the ring buffer does **not** contain the storage; it points at an
  array somebody else declared. The caller writes
  `static uint8_t storage[64]; rb_t rb; rb_init(&rb, storage, 64);` (`&storage` is
  "the address of").
- `rb_push` returns `bool` because it can fail. A full buffer must return `false`,
  and critically must **not** overwrite anything or corrupt its own indices.
- `rb_pop` needs to return two things — did it work, and the byte. C functions return
  one value, so the answer is: return the `bool`, and write the byte through the
  `out` pointer. This two-part pattern is everywhere in C.

**Caller supplies the storage — no `malloc` anywhere.** That constraint is not
stylistic. A lot of firmware forbids dynamic allocation outright, because a failed
allocation at 3am on a device in a field has no good recovery, and memory
fragmentation on a system that runs for a year is fatal. Writing to that rule from
the start is part of the point.

---

## How to think about it

Don't write code yet. Answer these on paper:

1. After `rb_init`, what are `head`, `tail`, and `count`? What does `rb_is_empty`
   return?
2. On a push: in what order do you write the byte, advance `head`, and increment
   `count`? Does the order matter? (Right now, no. After the levelling-up pass, it
   matters enormously.)
3. `head` has just been incremented and now equals `capacity`. What must happen?
4. What is the *first thing* `rb_push` does, before touching anything? (Check
   whether it's full.) Same question for `rb_pop`.
5. State the invariant that must be true at all times, no matter what sequence of
   calls happened. Something like: *count always equals the number of pushes that
   returned true, minus the number of pops that returned true.* Now assert that in
   your tests.

Then write it. It's about 50 lines.

---

## Tests it must pass

| Test | What it's protecting against |
| --- | --- |
| Empty on init; `rb_pop` returns `false` | Uninitialised fields; popping garbage out of a fresh buffer |
| Push three, pop three — same values, same order | It's a FIFO, not a stack. Getting C, B, A back means you're reading from the wrong end |
| Fill to capacity; next push returns `false` and corrupts nothing | The off-by-one that ASan exists to catch |
| Drain completely; next pop returns `false` | The empty check, from the other direction |
| Push and pop alternately many times past the end of the array | Wraparound happening repeatedly. Bugs here often survive one wrap and fail on the second |
| Interleaved partial fills — push 3, pop 1, push 3, pop 4 — checking `count` throughout | The invariant. This is the test that catches subtle index drift |

Make the capacity small in tests — 4 or 8. With a capacity of 1024 you'd need a
thousand operations before the interesting case happens.

---

## Once it's boring

*Boring* means: blank file to working, sanitizer-clean, in under fifteen minutes,
never unsure what to type next. Then add a constraint.

**Second pass — make it interrupt-safe without a lock.** The `count` field is the
problem: both the ISR and the main loop write it, and `count++` is not atomic. It's
really *read, add one, write back* — and if the interrupt fires between the read and
the write, one of the two updates vanishes. The fix is discipline rather than
machinery: delete `count`, use the sacrificed-slot scheme, and arrange that **only
the ISR writes `head` and only the main loop writes `tail`**. Each variable now has
exactly one writer, so there's nothing to corrupt. Mark both `volatile` so the
compiler doesn't cache them in a register and miss changes made by the other side.
This is a *single-producer, single-consumer lock-free queue* — an impressive-sounding
thing that is really just "one writer each."

**Third pass — power-of-two capacity.** Constrain capacity to 8, 16, 32… and replace
`% capacity` with `& (capacity - 1)`. They give identical results for powers of two.
Then paste both into [godbolt.org](https://godbolt.org), set the compiler to an ARM
target, and look at the assembly: the modulo becomes a division routine costing tens
of cycles on a chip with no hardware divider; the mask becomes one instruction. This
is where "the real cost of division" stops being an abstraction.

---

> **Log slugs:** `naive` → `lockfree` → `bitmask`. Record each session in
> [log.tsv](../log.tsv) under the variant you actually wrote — time is only
> comparable within a variant. See [LOGGING.md](../LOGGING.md).

## The publishable angle

Not the implementation — every bootcamp graduate has a ring buffer repo. What's worth
publishing is the interrupt-safety discussion **with a capture**: the naive version
dropping bytes at a baud rate where the ISR outruns the main loop, and the lock-free
version not dropping them. The measurement is the piece nobody else has.
