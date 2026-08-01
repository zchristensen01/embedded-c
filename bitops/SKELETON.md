# Skeleton — bitops

Three files and what goes in each, as pseudocode. Read it, **close it**, then
write from a blank file in your scratch directory. Working reference for the
three-file shape in real C: [template/](../template/). The task itself:
[BRIEF.md](BRIEF.md).

---

## File 1 — `bitops.h` (the menu)

Unusual for this kata: the single-bit operations go **in the header** as
`static inline`, because a function call costs more than the work they do.

```
OPEN include guard  (BITOPS_H)

    INCLUDE stdint.h    for uint32_t
    INCLUDE stdbool.h   for bool

    DEFINE static inline bit_set    (word, n) -> new word    <- body right here
    DEFINE static inline bit_clear  (word, n) -> new word
    DEFINE static inline bit_toggle (word, n) -> new word
    DEFINE static inline bit_test   (word, n) -> yes/no

    DECLARE field_get  (word, lsb, width)        -> the field's value
    DECLARE field_set  (word, lsb, width, value) -> new word

    DECLARE popcount            (word) -> how many bits are set
    DECLARE count_leading_zeros (word) -> zeros above the highest set bit
    DECLARE reverse_bits        (word) -> bits in the opposite order
    DECLARE is_power_of_two     (word) -> yes/no

CLOSE include guard
```

`static inline` means "paste this body at each call site instead of making a real
call." `static` keeps it from colliding when several files include the header.

Note these take a word and **return a new word** rather than modifying in place.
Easier to test, and it composes.

---

## File 2 — `bitops.c` (the kitchen)

```
INCLUDE "bitops.h"

The mask is always the first thing you build. Write the mask, then the
expression that uses it.


THE FOUR SINGLE-BIT OPERATIONS  (these live in the header)

    bit_set     make a word with a single 1 at position n, then combine so
                that bit becomes 1 and every other bit is untouched
    bit_clear   make that same single-1 word, INVERT it so it is all 1s
                except position n, then combine so only that bit is cleared
    bit_toggle  the operator that means "1 if the two inputs differ"
    bit_test    mask the word down to just that bit, then turn the result
                into a true/false (careful: masking gives 0 or 1<<n, not 0 or 1)

    Always write the single-1 word as 1u, not 1. Plain 1 is a SIGNED int, and
    shifting into bit 31 of a signed type is undefined behaviour. One character.


FUNCTION field_get (word, lsb, width) -> value
    build a mask of `width` 1s at the bottom
    shift the word down so the field sits at the bottom
    combine the two so everything above the field is discarded
    RETURN that

    CAREFUL: the obvious way to build that mask breaks when width is 32,
    because shifting a 32-bit type by 32 is undefined. Handle it deliberately.
    UBSan WILL catch you.


FUNCTION field_set (word, lsb, width, value) -> new word
    four steps, and the order matters:
      1. mask the incoming value down to `width` bits
         <- skip this and an oversized value spills into the NEIGHBOURING
            field. On real hardware that might be a clock source or an
            interrupt enable. This is the bug this kata exists to teach.
      2. CLEAR the existing field in the word
         <- skip this and field_set behaves like OR: it can set bits but
            never clear them, so writing 0 over a 1 silently does nothing
      3. shift the masked value up into position
      4. combine it into the cleared word
    RETURN the result


FUNCTION popcount (word) -> count
    first pass: loop over all 32 bit positions, count the ones that are set
    (the clever branchless version is the third pass, not now)


FUNCTION count_leading_zeros (word) -> count
    walk down from the top bit until you find a 1, counting as you go
    DECIDE what you return for an input of 0, and write it in NOTES.md
    (the ARM instruction and various libraries disagree - knowing that is
    itself worth something)


FUNCTION reverse_bits (word) -> new word
    first pass: loop 32 times, taking bits off one end and building the
    result from the other end


FUNCTION is_power_of_two (word) -> yes/no
    a power of two has exactly one bit set
    handle zero explicitly - zero has no bits set and is not a power of two
```

---

## File 3 — `test_bitops.c` (the critic)

Good news: this kata has exact, checkable answers. Use hex literals.

```
INCLUDE assert.h, stdio.h, "bitops.h"


FUNCTION test_single_bit_ops_at_both_edges
    ASSERT bit_set on an empty word at position 0  gives 0x00000001
    ASSERT bit_set on an empty word at position 31 gives 0x80000000
    ASSERT bit_clear removes exactly that bit and nothing else
    ASSERT bit_toggle twice returns the original word
    ASSERT bit_test agrees with what you set
    bit 0 and bit 31 are the whole point - the edges are where 1u shows up


FUNCTION test_field_round_trip
    FOR lsb from 0 to 31
        FOR width from 1 to (32 - lsb)
            pick a value that fits in `width` bits
            write it into a word with field_set
            read it back with field_get
            ASSERT you got the same value back
    one nested loop, hundreds of cases you would never write by hand
    includes a field at the very top of the word, and width == 32


FUNCTION test_oversized_value_does_not_spill
    start with a word that has KNOWN values in the bits either side
    field_set a 2-bit field with the value 7 (which does not fit)
    ASSERT the neighbouring bits are completely unchanged


FUNCTION test_full_width_field_does_not_shift_by_32
    field_get with lsb 0 and width 32
    ASSERT it returns the whole word
    the assert barely matters here - you are really checking UBSan stays quiet


FUNCTION test_utilities_against_known_values
    ASSERT popcount of 0x00000000 is 0
    ASSERT popcount of 0xFFFFFFFF is 32
    ASSERT popcount of 0x80000001 is 2
    ASSERT reverse_bits of 0x00000001 is 0x80000000
    ASSERT reverse_bits applied twice returns the original
    ASSERT is_power_of_two says no for 0, yes for 1, yes for 0x80000000, no for 3


FUNCTION main
    call every test function
    print "all tests passed"
```

---

## The order to write them in

1. Header with the four `static inline` bit operations, and the edge test.
   Get bit 31 working before anything else.
2. `field_get`, then `field_set`, then the round-trip test.
3. The utilities last — they're the least interesting part.

Compile after every step:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    bitops.c -o bits && ./bits
```

When it is clean, **log the session** ([LOGGING.md](../LOGGING.md)) and delete the
file.
