# Skeleton — debouncer

Three files and what goes in each, as pseudocode. Read it, **close it**, then
write from a blank file in your scratch directory. Working reference for the
three-file shape in real C: [template/](../template/). The task itself:
[BRIEF.md](BRIEF.md).

---

## File 1 — `debouncer.h` (the menu)

```
OPEN include guard  (DEBOUNCER_H)

    INCLUDE stdint.h    for uint16_t
    INCLUDE stdbool.h   for bool

    DEFINE a struct type debounce_t holding:
        stable_state  - what we currently BELIEVE the switch is
        last_raw      - what we saw on the previous call
        counter       - how many consecutive samples have agreed so far
        threshold     - how many are required before we believe a change

    DECLARE debounce_init    takes it, a threshold, a starting state
    DECLARE debounce_update  takes it, one raw reading, somewhere to put
                             the new state; returns "a change was confirmed
                             on THIS call" - true for exactly one tick

CLOSE include guard
```

Note what is **not** in there: a timestamp. This assumes you call it at a fixed
rate, so "5 samples" means "5 milliseconds" with no arithmetic. Being able to
explain why that's preferable to reading a clock is worth as much as the code.

---

## File 2 — `debouncer.c` (the kitchen)

```
INCLUDE "debouncer.h"


FUNCTION debounce_init (d, threshold, initial_state)
    store the threshold
    set stable_state and last_raw to the initial state
    set the counter to its starting value


FUNCTION debounce_update (d, raw, place-to-put-the-new-state) -> event / no event

    STEP 1 - has the input changed since last time?
        IF raw is different from last_raw
            the input just moved, so any progress we had made is void
            reset the counter to the start
        ELSE
            the input is holding steady
            count one more agreeing sample

        remember raw as last_raw for next time

    STEP 2 - have we seen enough agreeing samples to believe it?
        IF the counter has NOT reached the threshold
            RETURN no event

        IF raw is the same as what we already believe (stable_state)
            RETURN no event
            <- this is the case first drafts miss. The input wobbled and
               settled back where it started. Nothing actually changed, so
               firing an event here would be a phantom press.

    STEP 3 - a real change
        update stable_state to raw
        write the new state into the place the caller gave us
        reset whatever needs resetting so the NEXT change is detected properly
        RETURN event
```

**Do not special-case press versus release.** If you find yourself writing
"if it went from low to high…", stop. The logic above is direction-agnostic, and
a half-finished implementation that only debounces the press is the single most
common way this kata is got wrong — releases bounce exactly as much as presses.

---

## File 3 — `test_debouncer.c` (the critic)

```
INCLUDE assert.h, stdio.h, "debouncer.h"

This is the easiest kata to test properly, because you can feed it an exact
sequence of samples and know precisely what should happen on every tick.

FUNCTION feed (d, array of 0/1 samples, how many) -> number of events
    a small helper: call debounce_update once per sample, count the events
    OPTIONALLY also record WHICH tick each event landed on


FUNCTION test_steady_input_produces_nothing
    feed 20 samples that are all 0
    ASSERT zero events
    feed 20 samples that are all 1 ... after it has settled high
    ASSERT zero further events


FUNCTION test_clean_press_fires_exactly_once_on_the_right_tick
    threshold of 5
    feed: 0 0 0 then 1 1 1 1 1 1 1 1
    ASSERT exactly ONE event
    ASSERT it landed on the tick you predicted on paper, not just "somewhere"
    (this is where > versus >= shows up as one tick early or late)


FUNCTION test_short_noise_burst_produces_nothing
    threshold of 5
    feed alternating noise: 0 1 0 1 1 0 1 0
    ASSERT zero events - nothing ever held still long enough


FUNCTION test_noise_then_settled_fires_once_at_the_right_time
    feed noise, then a clean run of 1s past the threshold
    ASSERT exactly one event, at the tick after the run began


FUNCTION test_release_is_debounced_too
    settle high, then feed bouncy 0s, then steady 0s
    ASSERT exactly one event
    ASSERT the state reported is the released state


FUNCTION test_two_presses_both_register
    press, release, press again - all cleanly held
    ASSERT three events total
    (catches state that isn't reset properly after an event)


FUNCTION main
    call every test function
    print "all tests passed"
```

---

## The order to write them in

1. Header first — the struct fields *are* the design.
2. `test_steady_input_produces_nothing`, then make it pass.
3. `test_clean_press_fires_exactly_once` — this one forces the real logic.
4. Then the noise tests, then release.

Compile after every step:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    debouncer.c -o db && ./db
```

When it is clean, **log the session** ([LOGGING.md](../LOGGING.md)) and delete the
file.
