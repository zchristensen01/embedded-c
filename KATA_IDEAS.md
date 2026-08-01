# Future katas — candidates, and when to actually add one

## Read this before adding anything

The guide is blunt about this, and it's right:

> Thirty small programs is a beginner portfolio. Six modules that are genuinely good,
> tested, measured and explained is a better signal. Once the six are solid, spend the
> daily half hour on depth — hardware, measurement, breaking them — not on adding a
> seventh.

So: **do not start any of these until all six existing katas are boring** — blank
file to sanitizer-clean in fifteen minutes, no hesitation. Adding a seventh exercise
while the ring buffer still takes forty minutes is the enjoyable version of avoiding
the hard part.

A kata retires from the rotation when it's boring on hardware, not just on the desk.
That's when a slot opens up. Realistically that's months away, and by then you'll
have your own opinion about what's missing — which is a better guide than this list.

The list is ordered by how much it would actually add.

---

## 1. Rollover-safe software timer / scheduler

**The highest-value addition, and the one I'd add first.**

```c
typedef struct { uint32_t deadline; uint32_t period; void (*fn)(void); bool active; } timer_t;

void tick(void);                       /* called from a 1 ms interrupt */
bool timer_expired(uint32_t deadline); /* the interesting one */
void scheduler_run(void);              /* superloop: run whatever is due */
```

A millisecond counter that increments forever in a timer interrupt, plus tasks that
run when their deadline arrives. It is how a superloop firmware project without an
RTOS is structured — "blink the LED every 500 ms, read the sensor every 10 ms, check
the watchdog every second."

**Why it's worth a slot:** it contains one of the most famous bugs in embedded
software. A `uint32_t` millisecond counter overflows back to zero after 49.7 days. If
you write `if (now > deadline)`, everything works perfectly for seven weeks and then
your device wedges — and nobody's test run lasted seven weeks. The correct comparison
is:

```c
(int32_t)(now - deadline) >= 0
```

which works across the rollover because unsigned subtraction wraps correctly and the
signed cast gives you a relative distance. Understanding *why* that works is a
genuinely good interview answer, and a test that simulates the counter near
`0xFFFFFFFF` proves it in about six lines.

It also pairs naturally with the FSM (state timeouts) and the parser (frame timeouts),
so it makes two existing katas better rather than sitting alone.

## 2. Fixed-block memory pool

```c
void  pool_init(pool_t *p, void *storage, size_t block_size, size_t block_count);
void *pool_alloc(pool_t *p);       /* NULL if exhausted */
void  pool_free (pool_t *p, void *block);
```

`malloc` is banned in most firmware because allocation can fail at 3am with no
recovery, and fragmentation kills a device that runs for a year. The standard answer
is a pool: carve one static array into N equal blocks and hand them out, so
allocation is O(1), never fragments, and either succeeds or cleanly returns NULL.

**Why it's worth a slot:** it's the direct answer to a question you will be asked
("how do you do dynamic allocation in firmware?"), and the free-list implementation —
storing the "next free block" pointer *inside the free block itself*, costing zero
extra memory — is a properly satisfying trick. It also happens to cover the gap the
guide flags: if you're comfortable with a ring buffer but freeze on anything
involving pointers and data structures, this patches exactly that.

ASan is less helpful here (you're managing memory inside one big legal array), which
makes writing your own guard checks part of the exercise.

## 3. Byte packing / endianness

```c
void     put_u16_be(uint8_t *dst, uint16_t v);
uint32_t get_u32_le(const uint8_t *src);
```

Turning multi-byte numbers into byte sequences and back, explicitly, one byte at a
time. Sounds trivial; it's the thing that goes wrong whenever two devices from
different vendors talk to each other.

**Why it's worth a slot:** it teaches why you must never do this by casting a
`uint8_t *` to a `uint32_t *` and dereferencing it — that's both an alignment fault on
ARM (hard fault, device resets) and a strict-aliasing violation the optimiser is
allowed to miscompile. UBSan catches the alignment case, which makes the lesson land
hard. Small enough to be a 10-minute drill once learned.

Strong candidate to fold into the protocol parser rather than stand alone.

## 4. Moving average and IIR low-pass filter, in fixed point

```c
q16_t iir_update(iir_t *f, q16_t sample);   /* y += alpha * (x - y) */
```

Sensor readings are noisy; you smooth them before using them. The one-line
exponential filter above is what actually ships, because a proper moving average needs
a ring buffer of history and this needs one variable.

**Why it's worth a slot:** it's the missing half of the PID kata — the derivative term
amplifies noise and this is what you put in front of it. It reuses your Q16.16
arithmetic, so it's cheap to learn, and "choose alpha for a given cutoff frequency"
connects code to signal processing in a way that's very demonstrable with a plot.

Arguably belongs inside `fixed_point_pid` as its third pass rather than as kata 07.

## 5. Intrusive linked list

```c
typedef struct node { struct node *next; } node_t;   /* embedded IN your struct */
```

A list where the link pointers live inside the objects being listed, so the list
itself allocates nothing. This is how the Linux kernel and every RTOS do it.

**Why it might be worth a slot:** it's the one classic data structure that's genuinely
common in firmware, and it forces real pointer fluency — pointer-to-pointer for
removal is the moment pointers finally click for a lot of people. Lower priority than
the above because it's less specifically *embedded*.

## 6. Command dispatch table

```c
typedef struct { const char *name; void (*handler)(int argc, char **argv); } cmd_t;
```

A tiny serial command console: parse a line, look the verb up in a table, call its
handler. Every piece of hardware you build ends up with one for bring-up and testing,
and it's often the first thing you write on a new board.

**Why it might be worth a slot:** function-pointer tables again (so it reinforces the
table-driven FSM), plus string handling, which is otherwise absent from all six katas
and is a real source of C bugs. Pairs naturally with the protocol parser to make a
complete host↔device link — which is a demoable project rather than an exercise.

---

## Things I'd deliberately *not* add

- **A generic/void-pointer container library.** Templates-in-C via macros is a real
  technique, but it teaches you about macros rather than about firmware.
- **Sorting, searching, trees.** You will not be asked to balance a tree at a firmware
  company. If you freeze on data structures, the guide's own prescription applies: a
  dozen LeetCode problems in C patches that specific gap faster than a kata will.
- **A full RTOS or a context switcher.** Fantastic thing to build; it is a *project*,
  not a thirty-minute drill. It belongs in the evening slot next to the arm.
- **Bit-banged SPI/I²C.** Genuinely useful, but it's meaningless without hardware —
  which makes it a hardware-phase exercise, not a desk kata.

---

## The better move, most of the time

Before adding kata 07, ask whether the same half hour spent on an existing one would
teach more. Usually it would:

- Take the ring buffer to the **third** pass (power-of-two masking) and read the ARM
  assembly to see why it matters on a part with no hardware divider.
- Put the debouncer on **real hardware** with a scope on the pin.
- **Fuzz** the protocol parser with thousands of corrupted frames.
- **Measure** the switch-vs-table FSM: flash size from the linker map, cycles per
  transition.

Each of those produces something publishable. A seventh kata produces another
directory.
