# Skeleton — ring_buffer

Three files and what goes in each, as pseudocode. Read it, **close it**, then
write from a blank file in your scratch directory. Working reference for the
three-file shape in real C: [template/](../template/). The task itself:
[BRIEF.md](BRIEF.md).

While drilling, one file is fine — the split matters when you promote a version
into this repo.

---

## File 1 — `ring_buffer.h` (the menu)

```
OPEN include guard  (RING_BUFFER_H)

    INCLUDE stdint.h    for uint8_t
    INCLUDE stdbool.h   for bool
    INCLUDE stddef.h    for size_t

    DEFINE a struct type rb_t holding:
        a pointer to the caller's storage array
        capacity   - how many bytes that array holds
        head       - where the next byte gets WRITTEN
        tail       - where the next byte gets READ
        count      - how many bytes are in it right now

    DECLARE rb_init      takes buffer, storage array, capacity   returns nothing
    DECLARE rb_push      takes buffer, one byte                  returns worked/failed
    DECLARE rb_pop       takes buffer, somewhere to put a byte   returns worked/failed
    DECLARE rb_is_empty  takes buffer (read-only)                returns yes/no
    DECLARE rb_is_full   takes buffer (read-only)                returns yes/no
    DECLARE rb_count     takes buffer (read-only)                returns a number

CLOSE include guard
```

---

## File 2 — `ring_buffer.c` (the kitchen)

```
INCLUDE "ring_buffer.h"


FUNCTION rb_init (buffer, storage, capacity)
    remember the storage pointer and the capacity
    set head, tail and count to their starting values
    (what ARE the starting values? decide before you type)


FUNCTION rb_push (buffer, byte) -> worked / failed
    IF the buffer is full
        RETURN failed              <- and change NOTHING. no partial writes.

    write the byte at the head position
    advance head by one, wrapping back to 0 when it runs off the end
    record that there is one more byte in the buffer
    RETURN worked


FUNCTION rb_pop (buffer, place-to-put-the-byte) -> worked / failed
    IF the buffer is empty
        RETURN failed

    read the byte at the tail position
    write it into the place the caller gave us
    advance tail by one, wrapping back to 0 when it runs off the end
    record that there is one fewer byte in the buffer
    RETURN worked


FUNCTION rb_is_empty (buffer) -> yes / no
    one comparison


FUNCTION rb_is_full (buffer) -> yes / no
    one comparison
    NOTE: this is the design decision from BRIEF.md. head == tail looks
    identical whether the buffer is empty or completely full. How you answer
    this question is the whole exercise — write your answer in NOTES.md.


FUNCTION rb_count (buffer) -> a number
    just hand back what you already track
```

**The wrapping step appears twice.** Both push and pop advance an index and wrap
it. Notice that before you write it — if you find yourself typing the same thing
twice, that is usually a small `static` helper asking to exist.

---

## File 3 — `test_ring_buffer.c` (the critic)

```
INCLUDE assert.h, stdio.h, "ring_buffer.h"

Use a SMALL capacity — 4 or 8. With 1024 you would need a thousand operations
before anything interesting happens.


FUNCTION test_starts_empty
    declare a storage array and an rb_t
    init them
    ASSERT it reports empty
    ASSERT count is zero
    ASSERT popping from it fails


FUNCTION test_three_in_three_out_in_order
    push A, then B, then C
    pop three times
    ASSERT you got A, then B, then C
    (if you get C, B, A you built a stack, not a queue)


FUNCTION test_full_buffer_rejects_a_push
    push until it is exactly full
    ASSERT it reports full
    ASSERT the next push FAILS
    ASSERT count did not change
    ASSERT the contents are still intact - pop everything and check


FUNCTION test_drain_then_pop_fails
    fill it, empty it completely
    ASSERT the next pop fails


FUNCTION test_wraparound_survives_repeated_laps
    LOOP many more times than the capacity:
        push one byte, pop one byte, ASSERT you got back what you put in
    this walks head and tail around the array several times over
    (bugs here often survive the first lap and fail on the second)


FUNCTION test_count_stays_correct_through_interleaving
    push 3, ASSERT count is 3
    pop 1,  ASSERT count is 2
    push 3, ASSERT count is 5
    pop 4,  ASSERT count is 1
    this is the invariant test: count == successful pushes - successful pops


FUNCTION main
    call every test function
    print "all tests passed"
    return 0
```

---

## The order to write them in

1. **The header first.** Deciding the names and shapes is half the exercise.
2. **Then one test**, `test_starts_empty`. It will fail to compile — nothing is
   implemented yet. That's fine.
3. **Then `rb_init` and the query functions** until that one test passes.
4. **Then push and pop**, one test at a time.

Writing a test before the thing it tests feels backwards for about two days and
then feels obvious. It also stops you writing tests that merely describe whatever
you happened to build.

Compile after every step:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    ring_buffer.c -o rb && ./rb
```

When it is clean, **log the session** ([LOGGING.md](../LOGGING.md)) and delete the
file.
