# Skeleton — fixed_point_pid

Three files and what goes in each, as pseudocode. Read it, **close it**, then
write from a blank file in your scratch directory. Working reference for the
three-file shape in real C: [template/](../template/). The task itself:
[BRIEF.md](BRIEF.md).

**This is the hardest of the six** — control theory and fixed-point arithmetic at
the same time. Expect the first attempt to run well over fifteen minutes. That is
what the log is for.

---

## File 1 — `pid.h` (the menu)

```
OPEN include guard  (PID_H)

    INCLUDE stdint.h    for int32_t and int64_t

    DEFINE a type name q16_t meaning "an int32_t holding a value scaled by 65536"
        this is documentation for humans - the compiler still sees a plain
        int32_t - but it makes mixing scaled and unscaled numbers visible

    DEFINE Q16_ONE      the scale factor itself, 1 shifted left 16
    DEFINE TO_Q16(x)    turn a readable number into the scaled form
                        (this uses floating point, but at COMPILE time, which
                         is free - no float exists at runtime)
    DEFINE Q16_MUL(a,b) multiply two scaled numbers:
                          promote to 64-bit FIRST
                          multiply
                          shift back down by 16
                        wrap every parameter in parentheses - macros paste
                        text, so without them Q16_MUL(a+1, b) means the wrong
                        thing entirely

    DEFINE a struct type pid_t holding:
        kp, ki, kd       - the three gains
        integral         - the running total of every error seen
        prev_error       - last call's error, for the derivative
        out_min, out_max - output saturation limits
        integral_limit   - the anti-windup clamp

    DECLARE pid_init    takes it, three gains, output min and max
    DECLARE pid_update  takes it, a setpoint, a measurement -> the output
    DECLARE pid_reset   takes it - clears the accumulated history

CLOSE include guard
```

Nothing in this kata includes `math.h`, and nothing uses `float` or `double` at
runtime. If you type either, you have left the exercise.

---

## File 2 — `pid.c` (the kitchen)

```
INCLUDE "pid.h"


FUNCTION clamp (value, lo, hi) -> value        <- static, used three times
    if it is below lo, return lo
    if it is above hi, return hi
    otherwise return it unchanged


FUNCTION pid_init (p, kp, ki, kd, out_min, out_max)
    store the three gains and the two output limits
    choose and store integral_limit
        <- this is NOT a parameter, so YOU decide it. Derive it from the
           output range and write your reasoning in NOTES.md. This is exactly
           the kind of design decision that file exists for.
    zero the accumulated state (call pid_reset)


FUNCTION pid_reset (p)
    zero the integral
    zero prev_error
    (needed whenever the loop is re-enabled after being off, or you act on
     stale history from minutes ago)


FUNCTION pid_update (p, setpoint, measured) -> output

    STEP 1 - the error
        error = setpoint - measured

    STEP 2 - the integral term
        add the error to the running total
        CLAMP the running total to plus/minus integral_limit
        <- this clamp is anti-windup. Without it, a controller held against a
           stop accumulates a colossal total and then overshoots wildly when
           released. Without this line the kata is not finished.
        integral term = the gain ki, multiplied by the running total

    STEP 3 - the derivative term
        change = error - prev_error
        derivative term = the gain kd, multiplied by that change

    STEP 4 - the proportional term
        proportional term = the gain kp, multiplied by the error

    STEP 5 - combine and saturate
        output = the three terms added together
        CLAMP the output between out_min and out_max
        <- the most safety-relevant line in the file

    STEP 6 - remember for next time
        store error as prev_error
        RETURN the output


    EVERY multiply of a gain by a quantity goes through Q16_MUL. Two scaled
    numbers multiplied directly apply the scale factor twice and the answer is
    65536 times too big. Adding and subtracting scaled numbers needs no
    adjustment; multiplying always does.

    ASK YOURSELF: in step 5 you add three scaled values together. Can that sum
    overflow 32 bits BEFORE the clamp gets a chance to run? Signed overflow is
    undefined behaviour and UBSan will stop the program. Decide what to do.
```

---

## File 3 — `test_pid.c` (the critic)

Work the expected numbers out by hand. A test that recomputes the answer using
the implementation's own logic tests nothing.

```
INCLUDE assert.h, stdio.h, "pid.h"


FUNCTION test_zero_error_gives_zero_output
    init with any gains
    update with setpoint equal to measurement
    ASSERT the output is exactly zero


FUNCTION test_proportional_only_gives_the_exact_product
    init with ki and kd both zero, kp set to something like 2.0
    update with a known error, say 3.0
    ASSERT the output is exactly 6.0 in Q16 form
    compute that number BY HAND and write the literal in the assert


FUNCTION test_integral_accumulates_then_stops_at_the_clamp
    init with only ki non-zero
    call update 1000 times with the SAME constant error
    ASSERT the integral sits exactly at integral_limit, not beyond it
    ASSERT it has not silently wrapped around to a negative number
    then repeat with a constant NEGATIVE error and check the other side


FUNCTION test_output_never_leaves_its_limits
    init with huge gains and a modest output range
    throw a large error at it
    ASSERT the output is exactly out_max, never more
    same again with a large negative error and out_min


FUNCTION test_it_actually_controls_something
    a toy first-order plant - six lines, no physics:

        position = 0
        REPEAT 30 times
            output   = pid_update(pid, setpoint, position)
            position = position + a small fraction of output   <- a lazy motor
        ASSERT the final error is small

    then, once it passes: DELETE your anti-windup clamp and run it again with
    the plant held at zero for the first 20 iterations. Watch the overshoot.
    That is the moment the concept lands. Put the clamp back.


FUNCTION test_extreme_inputs_do_not_overflow
    feed the largest and smallest q16 values you can
    the assert hardly matters - you are checking UBSan stays silent
    this test has teeth precisely because of the sanitizer


FUNCTION main
    call every test function
    print "all tests passed"
```

---

## The order to write them in

1. **The macros first**, and a test that just checks `Q16_MUL(TO_Q16(2.0),
   TO_Q16(3.0))` equals `TO_Q16(6.0)`. If the arithmetic is wrong, nothing above
   it can be right.
2. Then P-only, and the exact-product test.
3. Then the integral, then the clamp, then the derivative.
4. The plant simulation last.

Compile after every step:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    pid.c -o pid && ./pid
```

When it is clean, **log the session** ([LOGGING.md](../LOGGING.md)) and delete the
file.
