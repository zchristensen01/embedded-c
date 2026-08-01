# Kata 03 — Finite State Machine

**In one sentence.** An explicit model of a system as a set of named states plus the
events that move between them — one variable holding what the system is currently
doing, instead of a thicket of boolean flags.

New to this? Read [GETTING_STARTED.md](../GETTING_STARTED.md) first.

---

## The problem, in plain language

Here is how control code goes wrong. You start with a flag:

```c
bool is_moving;
```

Then you need homing, so you add `bool is_homing`. Then faults: `bool has_fault`.
Then `bool is_enabled`. Four booleans is sixteen combinations, and only about five of
them are meaningful. What does `is_moving && has_fault` mean? What about
`is_homing && is_moving`? Nothing — but nothing in the code prevents them, and
eventually a code path sets both and the machine does something nobody designed.

A state machine replaces all of that with **one variable that holds exactly one value
at a time**:

```
        EV_ENABLE            EV_HOME_DONE          EV_MOVE_CMD
  IDLE ───────────► HOMING ───────────────► READY ────────────► MOVING
                                              ▲                    │
                                              └────────────────────┘
                                                 EV_TARGET_REACHED

  ...and from ANY state above, EV_ESTOP ───► FAULT ───► IDLE (only via EV_CLEAR)
```

Two ideas do all the work:

- **State** — where you are now. Exactly one, always.
- **Event** — something that happened: a command arrived, a sensor tripped, a timer
  expired.

The machine's entire job is: *given the state I'm in and the event that just
happened, what state am I in next?* Everything else is bookkeeping.

The discipline this forces is the actual lesson. You enumerate the states, enumerate
the events, and then decide what happens for **every combination** — including the
ones that should never occur. `EV_HOME_DONE` while in `ST_MOVING` shouldn't happen…
but what does your code do if it does? "Nothing, stay put" is a decision. Falling
through into an arbitrary branch is a bug. **The bugs in embedded systems live in the
transitions nobody thought about**, and this structure forces you to look at all of
them.

---

## Why firmware needs this

Nearly every embedded system is a superloop dispatching a state machine. Device
startup sequences, battery charging controllers, communication protocols, menu
systems, motion controllers.

Your arm has one whether you've written it down or not: *idle → homing → ready →
moving → fault*. The interesting question — and the one an interviewer will ask —
is what happens when a fault arrives **mid-move**. With flags, the answer is "depends
which branch we were in." With an explicit machine, the answer is written down in one
place and testable.

Note the E-stop requirement in the API below: it must be accepted from *every* state.
That's a safety property, and it's the requirement most first drafts miss because
they only draw the happy path.

---

## What you need from C

```c
#include <stdint.h>   /* uint32_t */
#include <stdbool.h>  /* bool */
```

**`enum`** is the piece you may not have met. It creates a type whose values are a
fixed set of names:

```c
typedef enum { ST_IDLE, ST_HOMING, ST_READY, ST_MOVING, ST_FAULT, ST_COUNT } state_t;
```

Underneath these are just integers — `ST_IDLE` is 0, `ST_HOMING` is 1, and so on —
but the names make the code readable and let the compiler warn you when a `switch`
doesn't handle every case.

`ST_COUNT` is a deliberate trick: because it's last, it equals the number of real
states. That gives you `state_t` array sizes and loop bounds that stay correct
automatically when you add a state later. Same for `EV_COUNT`. This idiom is
everywhere in C; learn to recognise it.

**`switch`** is how you branch on an enum:

```c
switch (f->state) {
case ST_IDLE:   /* ... */ break;
case ST_HOMING: /* ... */ break;
/* ... */
}
```

Do **not** put a `default:` case in while drilling. Without it, `-Wall` warns you
when you've forgotten a state — which is exactly the safety net this kata is about.
Adding `default:` silences the one warning you most want.

> **The `break` trap.** C `switch` cases *fall through* into the next one unless you
> `break`. Forget it and `ST_IDLE` silently runs the `ST_HOMING` code too. This is
> the single most common C-specific bug in this kata.

---

## The API you are writing

```c
typedef enum { ST_IDLE, ST_HOMING, ST_READY,
               ST_MOVING, ST_FAULT, ST_COUNT } state_t;

typedef enum { EV_ENABLE, EV_HOME_DONE, EV_MOVE_CMD,
               EV_TARGET_REACHED, EV_ESTOP,
               EV_CLEAR, EV_COUNT } event_t;

typedef struct {
    state_t  state;
    uint32_t ticks_in_state;
} fsm_t;

void        fsm_init  (fsm_t *f);
state_t     fsm_handle(fsm_t *f, event_t ev);
const char *state_name(state_t s);
```

- `fsm_handle` takes an event and returns the state you ended up in. It is the whole
  machine.
- `ticks_in_state` counts how long you've been here, resetting to zero on entry to a
  new state. Nothing uses it yet — it's the foundation for timeouts in the
  levelling-up pass ("fault if homing takes longer than 5 seconds").
- `state_name` returns a human-readable string. `const char *` means "pointer to
  characters I promise not to modify." Return a string literal — `return "ST_IDLE";`
  — which lives in flash and needs no storage. It exists so your test failures say
  `ST_MOVING` instead of `3`, and so a debug log is readable.

**Two hard requirements:**

1. An unhandled event must leave the state **unchanged** rather than falling through
   to something arbitrary.
2. `EV_ESTOP` must be accepted from **every** state and land in `ST_FAULT`.

---

## How to think about it

Draw the table before writing any code. Literally on paper — states down the side,
events across the top, and fill in every cell:

|            | EV_ENABLE | EV_HOME_DONE | EV_MOVE_CMD | EV_TARGET_REACHED | EV_ESTOP | EV_CLEAR |
| ---------- | --------- | ------------ | ----------- | ----------------- | -------- | -------- |
| ST_IDLE    | HOMING    | —            | —           | —                 | FAULT    | —        |
| ST_HOMING  | —         | READY        | —           | —                 | FAULT    | —        |
| ST_READY   | —         | —            | MOVING      | —                 | FAULT    | —        |
| ST_MOVING  | —         | —            | —           | READY             | FAULT    | —        |
| ST_FAULT   | —         | —            | —           | —                 | FAULT    | IDLE     |

`—` means "ignore, stay put." Thirty cells, and you had to make a decision about each
one. That's the exercise. Notice how obvious the E-stop column and the fault row
become once it's a grid — and how easy they'd be to miss while drawing arrows.

Then ask:

1. Where does `ticks_in_state` get reset — and does it reset when an event leaves you
   in the *same* state? (Say what you decided in `NOTES.md`.)
2. If someone passes an event value that isn't a valid `event_t` at all, what
   happens?
3. Can you leave `ST_FAULT` any way other than `EV_CLEAR`? Prove it.

Then write the `switch` version. Roughly 60 lines.

---

## Tests it must pass

| Test | What it's protecting against |
| --- | --- |
| Each legal path walks through the expected sequence of states | The basic wiring |
| **Every illegal event in every state is ignored** | Fall-through and missing `break` |
| E-stop from any state lands in `ST_FAULT` | The safety requirement, from all five states |
| Fault can only be left via `EV_CLEAR` | A machine that quietly recovers from a fault is dangerous |
| `ticks_in_state` resets on entry | Timeouts depend on it later |

The second one is the important test, and it should be a **loop over the full state ×
event matrix**, not spot checks:

```
for each state s in 0..ST_COUNT:
    for each event e in 0..EV_COUNT:
        if the table says (s,e) is illegal:
            put the machine in s
            fire e
            assert the state is still s
```

Thirty assertions from six lines of test code, and it stays correct when you add a
state later. Writing this loop rather than picking three cases by hand is the habit
that transfers to the job.

---

## Once it's boring

**Second pass — make it a table.** Replace the whole `switch` with a
two-dimensional array indexed by state and event:

```c
static const transition_t table[ST_COUNT][EV_COUNT] = { /* ... */ };
```

where each entry holds `{next_state, action_fn}`. Now `fsm_handle` is about four
lines: look up the cell, call the action if there is one, assign the next state. The
logic has disappeared into data. This is how large protocol stacks are actually
written, and the table is the same grid you drew on paper — which is the point.

`action_fn` is a **function pointer** — a variable holding the address of a function
so you can call it without knowing which one it is at compile time. If that's new,
it's worth the detour; it's C's answer to polymorphism and it shows up everywhere in
driver code.

**Third pass — entry and exit actions**, plus a timeout on `ST_HOMING` that faults if
the limit switch never arrives. That's `ticks_in_state` finally earning its place,
and it's the real behaviour: a homing move that never completes must not hang
forever.

---

> **Log slugs:** `switch` → `table` → `actions`. Record each session in
> [log.tsv](../log.tsv) under the variant you actually wrote — time is only
> comparable within a variant. See [LOGGING.md](../LOGGING.md).

## The publishable angle

Switch version versus table version, compared on **flash size taken from the linker
map file** and **cycles per transition**. Two implementations, two numbers each,
one short post.

That's a concrete engineering tradeoff with measurements attached rather than a
style opinion — and reading a linker map is a skill that signals you've shipped
something.
