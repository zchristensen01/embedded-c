# Skeleton — protocol_parser

Three files and what goes in each, as pseudocode. Read it, **close it**, then
write from a blank file in your scratch directory. Working reference for the
three-file shape in real C: [template/](../template/). The task itself:
[BRIEF.md](BRIEF.md).

**Do this one last.** It is the ring buffer and the state machine doing a real
job together.

---

## File 1 — `parser.h` (the menu)

```
OPEN include guard  (PARSER_H)

    INCLUDE stdint.h    for uint8_t and uint32_t
    INCLUDE stdbool.h   for bool

    DEFINE MAX_PAYLOAD    a fixed size, 32 or 64. No allocation anywhere.
    DEFINE START_BYTE     0xAA

    DEFINE an enum pstate_t listing the four parser states:
        P_SYNC     hunting for the start byte
        P_LEN      next byte is the length
        P_PAYLOAD  collecting payload bytes
        P_CRC      next byte is the checksum

    DEFINE a struct type parser_t holding:
        state                       - which of the four we are in
        payload[MAX_PAYLOAD]        - the bytes collected so far
        len                         - how many the length byte promised
        index                       - how many we have actually collected
        crc                         - the running checksum
        frames_ok, frames_bad,
        bytes_dropped               - diagnostics. NOT decoration.

    DECLARE parser_init  takes it
    DECLARE parser_feed  takes it, ONE byte -> true only on the byte that
                         completes a valid frame

    NOTE in a comment that the payload lives inside the struct, so the caller
    must consume it before feeding the next byte. That is a real constraint
    and the kind of thing a reviewer will ask about.

CLOSE include guard
```

---

## File 2 — `parser.c` (the kitchen)

```
INCLUDE "parser.h"


FUNCTION crc8_update (running_value, byte) -> new running value    <- static
    first pass, the bitwise version:
        combine the byte into the running value with XOR
        REPEAT 8 times:
            if the top bit is set
                shift left one and XOR in the polynomial constant (0x07)
            otherwise
                just shift left one
    (the 256-entry lookup table is the second pass, not now)

    DECIDE and write down: which bytes does your CRC cover? Just the payload?
    Length plus payload? Any answer works as long as both ends agree, but you
    must STATE it - "the CRC never matches" between two teams is nearly always
    this.


FUNCTION reset_to_hunting (p)                                      <- static
    set state to P_SYNC
    zero len, index and the running crc
    <- have ONE of these and call it from every exit path. If you write the
       reset logic separately for "good frame" and "bad frame" they will drift
       out of sync, and that drift is the bug.


FUNCTION parser_init (p)
    zero the three counters
    call reset_to_hunting


FUNCTION parser_feed (p, byte) -> complete valid frame available?

    SWITCH on the current state:

    CASE P_SYNC
        IF the byte is not START_BYTE
            count one more dropped byte
            RETURN no frame              <- stay here, keep hunting
        start the crc off, covering whatever you decided it covers
        go to P_LEN
        RETURN no frame

    CASE P_LEN
        IF the byte is larger than MAX_PAYLOAD
            count a bad frame
            reset to hunting
            RETURN no frame
            <- THIS IS THE ONE. Writing a 200-byte payload into a 64-byte
               array is the buffer overflow this kata exists to teach, and
               ASan will catch it if you get it wrong. Do not truncate and
               carry on - reject the whole frame.
        store the length, fold the byte into the crc, zero the index
        DECIDE: is a length of zero legal? If it is, you must go straight to
        P_CRC, or you will sit in P_PAYLOAD forever waiting for zero bytes.
        go to P_PAYLOAD
        RETURN no frame

    CASE P_PAYLOAD
        store the byte at position `index` in the payload array
        fold it into the crc
        advance index
        IF index has reached len
            go to P_CRC
        RETURN no frame
        <- note there is NO special handling of 0xAA here. Once you are
           collecting payload, 0xAA is just a data value. Resyncing on it
           would corrupt every frame that happens to contain that byte.

    CASE P_CRC
        compare the byte against your computed crc
        IF they match
            count a good frame
            set state back to P_SYNC (but do NOT wipe the payload - the
            caller is about to read it)
            RETURN frame available
        OTHERWISE
            count a bad frame
            reset to hunting
            RETURN no frame
```

**Where does the CRC get reset?** On accepting a start byte, not at the end of a
frame. Get that backwards and the first frame parses while the second never does
— the classic bug in this kata.

---

## File 3 — `test_parser.c` (the critic)

Build two helpers first, or every test becomes unreadable.

```
INCLUDE assert.h, stdio.h, string.h, "parser.h"


FUNCTION build_frame (payload bytes, length, output buffer) -> total size
    write START_BYTE, then the length, then the payload
    compute the crc the same way the parser does
    append it
    RETURN how many bytes the frame occupies
    <- so your tests never hand-encode a checksum literal


FUNCTION feed_all (p, bytes, count) -> how many frames came out
    call parser_feed once per byte, counting the trues


FUNCTION test_a_clean_frame_parses
    build a frame with a known payload
    feed it
    ASSERT exactly one frame came out
    ASSERT the payload matches byte for byte
    ASSERT p.len is right


FUNCTION test_leading_garbage_is_discarded
    feed some random bytes, then a good frame
    ASSERT the frame still parses
    ASSERT bytes_dropped equals the amount of garbage


FUNCTION test_bad_crc_is_rejected_and_recovers
    build a good frame, then corrupt its last byte
    feed it                       ASSERT no frame, frames_bad is 1
    feed a GOOD frame straight after
    ASSERT it parses              <- the recovery half, which is the point


FUNCTION test_truncated_frame_then_a_good_one
    feed the first half of a frame only, then a complete good frame
    ASSERT exactly one frame came out - the good one


FUNCTION test_oversized_length_is_rejected_without_overrunning
    hand-build: START_BYTE, then a length of 200, then some bytes
    feed it
    ASSERT no frame and frames_bad went up
    ASSERT ASan stays completely silent    <- the real assertion here


FUNCTION test_start_byte_inside_the_payload
    build a frame whose payload deliberately CONTAINS 0xAA
    feed it
    ASSERT it parses and the payload matches exactly


FUNCTION test_two_frames_back_to_back
    build two frames, concatenate with no gap, feed the whole thing
    ASSERT exactly two frames came out, both with correct payloads
    (this is the CRC-reset bug's test)


FUNCTION test_the_counters_add_up
    feed a mixture of good frames, corrupt frames and garbage
    ASSERT frames_ok + frames_bad equals the number of frames you fed
    a parser that silently loses a frame without counting it is worse than
    one that counts it as bad


FUNCTION main
    call every test function
    print "all tests passed"
```

---

## The order to write them in

1. **The CRC function and `build_frame` first**, plus a test that a frame you
   build passes its own checksum. Everything else depends on that being right.
2. Then `P_SYNC` and `P_LEN` and the clean-frame test.
3. Then payload collection, then CRC checking.
4. The hostile-input tests last — and expect at least one to fail the first time.
   That is the test doing its job.

Compile after every step:

```bash
gcc -std=c11 -Wall -Wextra -Werror -O1 \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    parser.c -o parser && ./parser
```

When it is clean, **log the session** ([LOGGING.md](../LOGGING.md)) and delete the
file.
