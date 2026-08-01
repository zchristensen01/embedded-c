# Kata 05 — Fixed-Point PID

**In one sentence.** A proportional-integral-derivative controller implemented in
integer arithmetic, with no floating point anywhere.

New to this? Read [GETTING_STARTED.md](../GETTING_STARTED.md) first. This is the
hardest kata of the six — it's two subjects at once. Expect the first attempt to take
well over the fifteen minutes.

---

## Part A: what a PID controller is

You want something to be at a value, and you can only influence it indirectly. The
arm should be at 90°; you control motor power, not position. A controller closes that
gap:

```
error = setpoint - measured
```

Then it decides what to output based on that error, using three terms added together.

**P — proportional.** Output a multiple of the current error. Far away, push hard;
close, push gently. `P = kp * error`.

Alone this isn't enough. As the error shrinks so does the push, and eventually the
push is too weak to overcome friction or gravity. The arm parks slightly below 90°
forever. That permanent gap is called **steady-state error**.

**I — integral.** Add up every error you've ever seen, and output a multiple of that
running total. `integral += error; I = ki * integral`.

This kills steady-state error: while any error persists, the sum keeps growing, so
the push keeps growing until the error is actually gone. The integral term is
"how long have we been wrong, and by how much."

**D — derivative.** Look at how fast the error is *changing* and push against that
change. `D = kd * (error - prev_error)`.

This is damping. Approaching the target fast, D pushes back so you don't overshoot
and oscillate.

**Output = P + I + D**, and `kp`, `ki`, `kd` are the tuning knobs.

### The two failure modes you must handle

**Integral windup** is the important one. Your arm is blocked — someone's holding it,
or it's against a hard stop. The error never goes away, so the integral keeps
accumulating: 100, 500, 20000, 500000. Then the obstruction is removed and the
controller is commanding maximum output based on a colossal integral that takes just
as long to unwind. The arm slams past the target and oscillates wildly.

The fix is **anti-windup**: clamp the integral accumulator to a maximum magnitude.
Without it, the controller is not finished. It's also a great thing to demonstrate on
video — the failure is dramatic and obvious.

**Derivative kick.** When the setpoint jumps suddenly, the error jumps with it, so
`error - prev_error` is enormous for one iteration and the output spikes. Fixed in
the second pass by taking the derivative of the *measurement* instead of the error.

---

## Part B: what fixed-point is

Microcontrollers frequently have no floating-point unit. A `float` multiply becomes a
software routine costing tens or hundreds of cycles — unaffordable in a 10 kHz
control loop where you have maybe 7,000 cycles for everything.

So you represent fractions using integers, by agreeing on a scale factor. **Q16.16**
means: store the real value multiplied by 65536 (which is 2^16), in a 32-bit signed
integer. The top 16 bits are the whole part, the bottom 16 are the fraction.

| Real value | Stored as | Why |
| --- | --- | --- |
| 1.0 | 65536 | 1 × 65536 |
| 0.5 | 32768 | 0.5 × 65536 |
| 2.75 | 180224 | 2.75 × 65536 |
| −1.0 | −65536 | |

Resolution is 1/65536 ≈ 0.000015 — plenty. Range is about ±32,768 — the thing to
watch.

**Addition and subtraction just work.** `(2.0 × 65536) + (0.5 × 65536)` is
`(2.5 × 65536)`. No adjustment.

**Multiplication needs a correction.** Multiply two scaled numbers and you've applied
the scale factor twice:

```
(a × 65536) × (b × 65536) = a × b × 65536 × 65536
```

You want `a × b × 65536`, so divide by 65536 once — which is a right shift by 16.
Hence:

```c
#define Q16_MUL(a,b) ((q16_t)(((int64_t)(a) * (b)) >> 16))
```

**The `int64_t` cast is the whole point of that macro.** Before shifting back down,
the product is genuinely huge — 2.0 × 3.0 in Q16.16 is 65536×2 × 65536×3 ≈ 2.6×10^10,
which does not fit in 32 bits. Promote to 64-bit, do the multiply, shift, then come
back to 32. Omit the cast and it overflows silently — signed overflow, undefined
behaviour, and UBSan will stop you.

This is the real lesson of fixed-point: **arithmetic has a budget.** You are
constantly asking "can this intermediate value fit?"

---

## Why firmware needs this

Motor position and velocity control, temperature control, current regulation, battery
charging. Any time software is closing a loop around a physical quantity.

**This is the kata closest to your own project — it is the loop that runs on your
arm.** Everything you learn here about windup and saturation shows up as physical
behaviour you can film.

---

## What you need from C

```c
#include <stdint.h>   /* int32_t, int64_t */
```

No `math.h`, no `float`, no `double`. If you type `float` you've left the exercise.

**Macros.** `#define Q16_ONE (1 << 16)` is a straight text substitution done before
compilation. Note the parentheses everywhere in `Q16_MUL` — macros paste text, so
without them `Q16_MUL(a+1, b)` would expand into something that means the wrong thing.
Wrapping every parameter is not paranoia, it's required.

**Clamping** is the operation you'll write three times here (integral limit, output
min, output max), so consider a small `static` helper for it.

---

## The API you are writing

```c
/* Q16.16: value stored as (real * 65536) */
typedef int32_t q16_t;
#define Q16_ONE   (1 << 16)
#define TO_Q16(x) ((q16_t)((x) * Q16_ONE))
#define Q16_MUL(a,b) ((q16_t)(((int64_t)(a) * (b)) >> 16))

typedef struct {
    q16_t kp, ki, kd;
    q16_t integral;
    q16_t prev_error;
    q16_t out_min, out_max;
    q16_t integral_limit;
} pid_t;

void  pid_init  (pid_t *p, q16_t kp, q16_t ki, q16_t kd,
                 q16_t out_min, q16_t out_max);
q16_t pid_update(pid_t *p, q16_t setpoint, q16_t measured);
void  pid_reset (pid_t *p);
```

- `typedef int32_t q16_t` creates a name that documents the *interpretation*. The
  compiler still sees a plain `int32_t` — this is for humans, and it's worth doing
  because mixing a Q16 value with a plain integer is the mistake this type name is
  there to make visible.
- `TO_Q16(1.5)` uses floating point at **compile time**, which is free — the compiler
  folds it into the constant `98304`. No float ever exists at runtime. Fine for test
  constants.
- `pid_update` is called once per control period and returns the output to apply.
- `pid_reset` clears `integral` and `prev_error` — needed whenever the loop is
  re-enabled after being off, or you'll act on stale history.

**Three things must be present or it is not finished:**

1. The intermediate multiply promoted to `int64_t` before shifting.
2. A clamp on the integral accumulator (anti-windup).
3. Output saturation to `out_min`/`out_max`.

---

## How to think about it

Write `pid_update` as five lines of pseudocode before any C:

1. Compute the error.
2. Accumulate it into `integral`, **then clamp** `integral` to ±`integral_limit`.
3. Compute the derivative from `error` and `prev_error`.
4. Sum the three terms — each one a `Q16_MUL` of a gain and a quantity.
5. Clamp the output to `[out_min, out_max]`, store `prev_error`, return.

Then interrogate it:

- What sets `integral_limit`? It's not in `pid_init`'s parameter list. Pick a
  sensible default derived from the output range and say why in `NOTES.md` — this is
  exactly the kind of design decision the notes file exists for.
- In step 4 you add three `q16_t` values. Can that sum overflow 32 bits before you
  clamp it? What would you do about it?
- Should the clamp in step 2 happen before or after the multiply by `ki`? (Both are
  defensible. Know which you chose.)
- Where is the loop period in these equations? Nowhere — the gains absorb it, so they
  are "per iteration" fudge factors. That's fine for pass one, and it's what the third
  pass fixes.

---

## Tests it must pass

You can compute the expected answers by hand, so do — a test that recomputes the
result using the implementation's own logic tests nothing.

| Test | What it's protecting against |
| --- | --- |
| Zero error with zero integral produces zero output | Sign errors and stray offsets |
| P-only (`ki`=`kd`=0) with a known error produces **exactly** the expected product | Your Q16 multiply. Compute the number by hand |
| The integral accumulates over repeated calls and **stops at the clamp** | Anti-windup. Call it 1000 times with constant error and assert the integral is at the limit, not beyond |
| Output saturates at the configured limits and never exceeds them | The most safety-relevant property |
| A simulated first-order plant converges to the setpoint | That it actually controls anything |
| Extreme inputs do not overflow | UBSan is watching signed overflow, so this test has teeth |

The plant simulation is simpler than it sounds — about six lines, no physics:

```
position = 0
repeat 30 times:
    output   = pid_update(&pid, setpoint, position)
    position = position + (output scaled down a bit)   /* a lazy motor */
assert final error is small
```

That's a "first-order plant." It's a toy, and it is enough to prove the loop closes.
Feed it a step, watch the error shrink. Then delete the anti-windup clamp and watch
this same test fail — that's the moment the concept lands.

---

## Once it's boring

**Second pass — derivative on measurement.** Replace `error - prev_error` with
`-(measured - prev_measured)`. Mathematically near-identical while the setpoint is
constant, but when the setpoint jumps the derivative term no longer spikes. Standard
practice in real controllers.

**Third pass — filter the derivative and make the loop rate explicit.** Derivative
amplifies noise (it's a difference of two noisy numbers, so the noise doubles while
the signal may not) — put a simple low-pass filter on it. Then pass `dt` in, so
`ki` and `kd` have real units (per second) instead of being per-iteration fudge
factors, and changing your loop rate stops silently retuning your controller.

---

## The publishable angle

**Strong, and it ties straight into your arm.** Float versus fixed-point on your
actual microcontroller: cycle counts for both, plus step-response plots showing the
fixed-point version holds position just as well. Then a second plot with and without
anti-windup — that failure is visible, dramatic, and makes the same post twice as
convincing.

And per the guide: a thirty-second video of a joint holding position against a load
outranks all six writeups combined.
