# Kata 02 — Switch Debouncer

**In one sentence.** A function that turns the electrically noisy signal from a
mechanical switch into clean, single, trustworthy edges.

New to this? Read [GETTING_STARTED.md](../GETTING_STARTED.md) first.

---

## The problem, in plain language

**Hardware lies.** This kata is usually where that lands for the first time.

A button is two pieces of metal springing together. They are not clean about it —
they touch, bounce apart, touch again, several times, over roughly 1 to 20
milliseconds before settling. Your microcontroller reads that pin thousands of times
a second, so it sees the whole mess:

```
what your finger did:      ________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾

what the pin actually did: ________|‾|_|‾‾|_|‾|__|‾‾‾‾‾‾‾‾
                                   <-- ~5 ms ->
                                    bouncing

what naive code reports:        press press press press press
                                   (five presses, not one)
```

One press, eleven events. If that button increments a counter, the counter jumps by
eleven. If it's a limit switch telling your robot arm "you've reached home," your
zero position is wrong and every move afterwards inherits the error.

**The fix:** stop trusting any single reading. Sample the pin at a fixed rate and
only believe a change once the new value has held steady for N consecutive samples.
Bouncing never stays still that long; a real press does.

```
raw:       0 0 0 1 0 1 1 0 1 1 1 1 1 1 1 1 1 1
counter:   . . . 1 . 1 2 . 1 2 3 4 5 . . . . .     (threshold = 5)
                 ^   ^ ^   ^         ^
              starts  restarts       reaches 5 -> ONE event fired here
```

The counter counts consecutive agreeing samples and resets to zero the instant the
input disagrees. Only when it reaches the threshold do you accept the change.

That's the whole idea. The subtlety is in the bookkeeping.

---

## Why firmware needs this

Every switch, button, limit switch, relay contact, and encoder index pulse.

On a robot arm, homing works by driving an axis slowly toward a limit switch until it
trips, then calling that position zero. A bouncing switch means you take the *first*
spurious edge — possibly a millimetre early — as zero. Every subsequent move is
offset, and the error is silent and reproducible, which makes it maddening to
diagnose.

The general pattern — *reject a transition until the input has been stable for N
samples* — recurs far beyond buttons: sensor validation, fault detection ("only
declare an overtemperature fault if it's been hot for 100 ms"), and communications
link-loss detection all use exactly this shape.

The broader lesson this kata teaches is that **time is an input to your logic**, not
something that merely happens while your code runs.

---

## What you need from C

```c
#include <stdint.h>   /* uint16_t */
#include <stdbool.h>  /* bool */
```

Nothing exotic. Two concepts:

**State that persists across calls.** This function is called once per millisecond,
forever, and each call must remember what the previous ones saw. In a higher-level
language you'd use a class instance. In C you put the memory in a struct and the
caller passes a pointer to it every time. The struct *is* the object; the function is
just a method that takes `this` explicitly.

**Why no timestamp parameter.** The API takes no clock reading. It assumes you call
it at a fixed rate — say every 1 ms from a timer interrupt — so "5 samples" *means*
"5 milliseconds" without arithmetic. This is how it's nearly always done, because
reading a clock costs time, invites rollover bugs, and needs a clock that exists.
Being able to explain that tradeoff is worth as much as the code.

---

## The API you are writing

```c
typedef struct {
    bool     stable_state;  /* what we currently believe the switch is */
    bool     last_raw;      /* what we saw on the previous call */
    uint16_t counter;       /* how many consecutive samples have agreed */
    uint16_t threshold;     /* how many are required to accept a change */
} debounce_t;

void debounce_init(debounce_t *d, uint16_t threshold, bool initial_state);

/* Call at a fixed rate, e.g. every 1 ms.
   Returns true on the tick where a confirmed change occurred;
   *out holds the new state. */
bool debounce_update(debounce_t *d, bool raw, bool *out);
```

Line by line:

- `stable_state` — the debounced, trustworthy answer. This is what the rest of your
  program should ever act on.
- `last_raw` — the previous raw reading, so you can tell whether the input just
  changed (reset the counter) or is holding steady (keep counting).
- `counter` vs `threshold` — how far along you are, and how far you need to get.
- `debounce_update` returns `true` **only on the single tick** where a change is
  confirmed — an *event*, not a status. If you want "is the button down right now,"
  that's `stable_state`. Distinguishing edge from level is the design decision here.
- `bool *out` — same two-return pattern as the ring buffer: the return value says
  *whether* something happened, the out-pointer says *what*.

---

## How to think about it

On paper, before typing:

1. After `debounce_init(&d, 5, false)`, what is in each field?
2. On each call there are two possibilities: `raw` matches `last_raw`, or it doesn't.
   What happens to `counter` in each case?
3. The counter has just reached `threshold`. What now — and what if `raw` already
   equals `stable_state`? (You must not fire an event when the input wobbled and came
   back to where it started. This is the case most first drafts get wrong.)
4. After firing an event, what does `counter` need to be for the *next* change to be
   detected correctly?
5. Does your logic care whether the change was false→true or true→false? It must not.
   **A half-finished implementation only debounces the press and lets the release
   through raw** — and releases bounce exactly as much as presses do.

Then write it. It's about 20 lines. The brevity is deceptive; the state bookkeeping
is where it goes wrong.

---

## Tests it must pass

This is the easiest kata to test properly, because you can feed it an exact sequence
of samples and know precisely what should happen on every tick. Write a helper that
feeds an array of 0/1 values and counts events.

| Test | What it's protecting against |
| --- | --- |
| A steady input produces no events | Firing on every call instead of on change |
| A clean transition held past the threshold produces **exactly one** event, on the correct tick | Off-by-one on the threshold — `>` vs `>=` is one tick early or late |
| A burst of alternating noise shorter than the threshold produces **zero** events | The counter not resetting properly on disagreement |
| Noise, then a settled state, produces exactly one event at the right time | The realistic case: real switches do both |
| Release is debounced as well as press | The half-finished implementation described above |
| Two presses in a row both register | State not being reset after an event |

"On the correct tick" matters — assert *when*, not just *how many*. Count the ticks
and check the event lands on the one you predicted on paper.

---

## Once it's boring

**Second pass — the integrator.** Instead of resetting to zero on disagreement, let
a counter climb toward a ceiling while the input is high and fall toward zero while
it's low, flipping the output only at the extremes. Slightly more code, noticeably
more tolerant of intermittent noise — a single spurious sample in an otherwise clean
signal doesn't restart the whole count. It also gives you hysteresis for free.

**Third pass — the shift register trick.**

```c
history = (uint8_t)((history << 1) | raw);
/* then test the whole byte against 0xFF and 0x00 */
```

Each call shifts the history left and drops the newest sample into bit 0, so the byte
always holds the last eight readings. `history == 0xFF` means eight consecutive highs
— confirmed press. `history == 0x00` means confirmed release. Eight samples of
debouncing in two lines and one byte of RAM, no counter and no branches. When you
have written the counter version three times, this one is a genuinely satisfying
thing to arrive at.

---

> **Log slugs:** `counter` → `integrator` → `shiftreg`. Record each session in
> [log.tsv](../log.tsv) under the variant you actually wrote — time is only
> comparable within a variant. See [LOGGING.md](../LOGGING.md).

## The publishable angle

**This is the best first writeup you can produce.** Put a real switch on a logic
analyzer or scope and capture it bouncing — actual milliseconds, actual spurious
edges, from your bench. Then the same button through your debouncer. Two images,
maybe 400 words.

Nobody argues with a trace, it proves you touched hardware rather than just reading
about it, and unlike the code it is genuinely yours.
