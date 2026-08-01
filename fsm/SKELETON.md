# Skeleton — fsm

Three files and what goes in each, as pseudocode. Read it, **close it**, then
write from a blank file in your scratch directory. Working reference for the
three-file shape in real C: [template/](../template/). The task itself:
[BRIEF.md](BRIEF.md).

---

## File 1 — `fsm.h` (the menu)

```
OPEN include guard  (FSM_H)

    INCLUDE stdint.h    for uint32_t

    DEFINE an enum state_t listing every state:
        ST_IDLE, ST_HOMING, ST_READY, ST_MOVING, ST_FAULT, and last ST_COUNT

    DEFINE an enum event_t listing every event:
        EV_ENABLE, EV_HOME_DONE, EV_MOVE_CMD, EV_TARGET_REACHED,
        EV_ESTOP, EV_CLEAR, and last EV_COUNT

    DEFINE a struct type fsm_t holding:
        state           - the one variable that says what the system is doing
        ticks_in_state  - how long we have been here

    DECLARE fsm_init    takes it                    returns nothing
    DECLARE fsm_handle  takes it, an event          returns the state you ended in
    DECLARE state_name  takes a state               returns readable text

CLOSE include guard
```

`ST_COUNT` and `EV_COUNT` are last on purpose: each one ends up equal to the
number of real values before it, so array sizes and loop bounds stay correct
automatically when you add a state later.

---

## File 2 — `fsm.c` (the kitchen)

```
INCLUDE "fsm.h"


FUNCTION fsm_init (f)
    set the state to ST_IDLE
    zero the tick counter


FUNCTION fsm_handle (f, event) -> the resulting state

    remember which state we started in

    IF the event is EV_ESTOP
        go to ST_FAULT
        <- handle this FIRST, before the per-state logic. E-stop is accepted
           from every state, and doing it once up here means you cannot
           forget it in one of the five branches below.

    OTHERWISE switch on the current state:

        CASE ST_IDLE
            IF the event is EV_ENABLE       -> next state is ST_HOMING
            (anything else: fall out and change nothing)

        CASE ST_HOMING
            IF the event is EV_HOME_DONE    -> next state is ST_READY

        CASE ST_READY
            IF the event is EV_MOVE_CMD     -> next state is ST_MOVING

        CASE ST_MOVING
            IF the event is EV_TARGET_REACHED -> next state is ST_READY

        CASE ST_FAULT
            IF the event is EV_CLEAR        -> next state is ST_IDLE
            and NOTHING else may leave this state

    IF the state actually changed
        store the new state
        reset ticks_in_state to zero

    RETURN the current state
```

Two things to be careful about:

- **`break` in every case.** C `switch` cases fall through into the next one
  unless you break. Forget it and `ST_IDLE` silently runs the `ST_HOMING` code
  too. This is the most common C-specific bug in this kata.
- **No `default:` case** while drilling. Without one, `-Wall` warns you when
  you've forgotten a state — which is exactly the safety net this exercise is
  about. Adding `default:` silences the one warning you most want to hear.

```
FUNCTION state_name (state) -> readable text
    a switch returning a string literal per state: "ST_IDLE", "ST_HOMING", ...
    string literals live in flash and need no storage, so this is free
    it exists so your test failures say ST_MOVING instead of 3
```

---

## File 3 — `test_fsm.c` (the critic)

```
INCLUDE assert.h, stdio.h, "fsm.h"


FUNCTION test_the_happy_path
    init                          ASSERT state is ST_IDLE
    fire EV_ENABLE                ASSERT state is ST_HOMING
    fire EV_HOME_DONE             ASSERT state is ST_READY
    fire EV_MOVE_CMD              ASSERT state is ST_MOVING
    fire EV_TARGET_REACHED        ASSERT state is ST_READY


FUNCTION test_estop_from_every_state_lands_in_fault
    FOR each state s in 0 .. ST_COUNT-1
        put the machine into state s
        fire EV_ESTOP
        ASSERT the state is now ST_FAULT


FUNCTION test_fault_only_clears_via_the_clear_event
    get into ST_FAULT
    FOR each event e in 0 .. EV_COUNT-1
        IF e is EV_CLEAR, skip it
        put the machine back into ST_FAULT
        fire e
        ASSERT the state is STILL ST_FAULT
    now fire EV_CLEAR             ASSERT state is ST_IDLE


FUNCTION test_every_illegal_event_is_ignored
    THIS IS THE IMPORTANT ONE. Loop the whole grid, do not spot-check:

    FOR each state s in 0 .. ST_COUNT-1
        FOR each event e in 0 .. EV_COUNT-1
            IF your paper table says (s, e) is a LEGAL transition, skip it
            put the machine into state s
            fire e
            ASSERT the state is still s

    thirty assertions from six lines, and it stays correct when you add a state


FUNCTION test_ticks_reset_on_entry
    get into some state, let ticks_in_state be non-zero
    cause a transition
    ASSERT ticks_in_state is back to zero


FUNCTION main
    call every test function
    print "all tests passed"
```

You will need a way to force the machine into an arbitrary state for the loop
tests. Setting `f.state` directly from the test is fine — the test file is
allowed to know things a caller wouldn't.

---

## The order to write them in

1. **Draw the grid on paper first** — five states down, six events across, and
   fill in all thirty cells. That drawing IS the exercise; the code is a
   transcription of it.
2. Header, then `test_the_happy_path`, then the switch.
3. Then the matrix test. Expect it to catch something.

Compile after every step:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    fsm.c -o fsm && ./fsm
```

When it is clean, **log the session** ([LOGGING.md](../LOGGING.md)) and delete the
file.
