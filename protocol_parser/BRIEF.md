# Kata 06 — Protocol Parser

**In one sentence.** A byte-at-a-time parser that finds framed messages inside a
stream that may be truncated, corrupted, or interrupted at any point.

New to this? Read [GETTING_STARTED.md](../GETTING_STARTED.md) first. **Do this one
last** — it combines the ring buffer and the FSM, and it's the closest thing here to
production code.

---

## The problem, in plain language

Two devices are connected by a serial wire. Bytes arrive one at a time, with
arbitrary gaps, and the wire has no concept of "a message" — it's an endless stream
of bytes. You have to find the messages inside it.

The convention is a **frame**: an agreed shape that lets the receiver recognise where
a message starts and ends.

```
  0xAA     LEN      PAYLOAD ...            CRC8
┌──────┬────────┬─────────────────────┬──────────┐
│ 0xAA │   3    │  0x01  0x02  0x03   │   0x5C   │
└──────┴────────┴─────────────────────┴──────────┘
  start   how      the actual data      checksum
  byte    many                          over the frame
```

- **Start byte `0xAA`** — a marker meaning "a frame probably begins here."
- **LEN** — how many payload bytes follow, so you know when the payload ends.
- **PAYLOAD** — the data.
- **CRC8** — a one-byte checksum computed over the frame. If your own computation
  doesn't match the byte received, something got corrupted; throw the frame away.

You cannot wait for a whole frame to arrive and then examine it, because you don't
control when bytes arrive and you must not block. Instead you get handed **one byte
at a time** and must remember where you were. That's a state machine:

```
    P_SYNC  ──see 0xAA──►  P_LEN  ──got length──►  P_PAYLOAD  ──got LEN bytes──►  P_CRC
      ▲                                                                             │
      └─────────────────────── frame done (good or bad) ─────────────────────────────┘
```

In `P_SYNC` you throw away anything that isn't `0xAA`. In `P_PAYLOAD` you collect
bytes until you have LEN of them. And so on.

### The actual skill: recovery

The input is **hostile**. Not because of attackers — because wires are noisy, cables
get unplugged mid-message, and the other device reboots halfway through a
transmission. Your parser must:

- Never block, never assume a whole message is available.
- Never be permanently derailed by garbage.
- After **any** failure, return to hunting for the next start byte and carry on.

A parser that works on clean input is a first draft. A parser that recovers from
anything is the deliverable. If a cable is yanked mid-frame and your parser sits in
`P_PAYLOAD` forever waiting for bytes that will never come, the link is dead until
someone power-cycles the device — and that's the bug that gets reported from the
field as "it randomly stops working."

---

## Why firmware needs this

Every serial link to a sensor, radio, GPS module, motor driver, or host computer.
NMEA sentences from a GPS, Modbus over RS-485, a vendor's binary protocol from an
IMU, your own command protocol between a PC and your arm.

Bytes arrive one interrupt at a time and messages straddle those arrivals, which is
precisely why this is a state machine and not a `scanf`. In a real system the ISR
pushes bytes into a **ring buffer** (Kata 01) and the main loop pops them and feeds
them to this **state machine** (Kata 03), one at a time. That's why this kata comes
last: it's the two earlier ones doing a real job.

---

## What you need from C

```c
#include <stdint.h>   /* uint8_t, uint32_t */
#include <stdbool.h>  /* bool */
#include <string.h>   /* memcpy, if you want it */
```

**Arrays inside a struct.** `uint8_t payload[MAX_PAYLOAD];` reserves that many bytes
inside every `parser_t`. Fixed size, no allocation — same rule as everywhere else.
Define `MAX_PAYLOAD` with `#define` in the header (32 or 64 is fine).

**CRC8.** A checksum: run every byte through a small repeatable calculation and get
one byte out. Send it along; the receiver recomputes and compares. Any single-bit
corruption almost certainly changes the result, so mismatches mean "discard."

For pass one, write the bitwise version — for each byte, XOR it into the running
value, then for each of its 8 bits, shift left and conditionally XOR a polynomial
constant (0x07 and 0x31 are both common). Roughly 8 lines and two nested loops. You do
not need to understand the polynomial mathematics to implement or use it correctly;
you need to know it's deterministic and that both ends must use the same one.

Decide and write down: **what range of bytes does your CRC cover?** Just the payload?
Length plus payload? Including the start byte? Any choice works as long as sender and
receiver agree — but you must state it, because "the CRC never matches" between two
teams is nearly always this.

---

## The API you are writing

```c
/* Frame: [0xAA][LEN][PAYLOAD...][CRC8] */
typedef enum { P_SYNC, P_LEN, P_PAYLOAD, P_CRC } pstate_t;

typedef struct {
    pstate_t state;
    uint8_t  payload[MAX_PAYLOAD];
    uint8_t  len, index, crc;
    uint32_t frames_ok, frames_bad, bytes_dropped;
} parser_t;

void parser_init(parser_t *p);

/* Feed one byte. Returns true when a complete, valid
   frame is available in p->payload with length p->len. */
bool parser_feed(parser_t *p, uint8_t byte);
```

- `parser_feed` takes exactly one byte and returns `true` only on the byte that
  completes a valid frame. The caller's loop is
  `while (rb_pop(&rb, &b)) { if (parser_feed(&p, b)) handle(p.payload, p.len); }`.
- `len` is the declared length; `index` is how many payload bytes you've collected so
  far; `crc` is the running checksum.
- The payload lives inside the parser struct, so the caller must consume it before
  feeding the next byte. Note that in your header — it's a real constraint and the
  kind of thing a reviewer asks about.

**The counters are not decoration.** `frames_ok`, `frames_bad`, and `bytes_dropped`
are exactly what real firmware keeps, because they are the first thing anyone looks
at when a link misbehaves. "1000 ok, 0 bad, 40000 dropped" says the baud rate is
wrong. "900 ok, 100 bad" says electrical noise. "All zero" says the wire is dead.
Including them shows you have thought about your code being debugged in the field
six months from now, which is a genuinely uncommon signal in a junior portfolio.

---

## How to think about it

1. For each of the four states, answer: *a byte just arrived — what do I do with it,
   and what state am I in next?*
2. In `P_SYNC`, a byte that isn't `0xAA` arrives. Which counter moves?
3. In `P_LEN`, the length byte says 200 but `MAX_PAYLOAD` is 64. **What must happen?**
   (Not "truncate and carry on." Reject the frame, count it, go back to `P_SYNC`.
   Writing 200 bytes into a 64-byte array is the buffer overflow this kata exists to
   teach — and ASan will catch it if you get it wrong.)
4. What does LEN = 0 mean? Is a zero-length frame legal? Decide, and make sure you
   don't sit in `P_PAYLOAD` waiting for zero bytes forever.
5. Where does the CRC accumulator get reset? (On accepting a start byte — not at the
   end. Get this wrong and the first frame parses and the second never does. This is
   *the* classic bug in this kata.)
6. After a bad CRC, what is the state and what has been reset? Write down every field
   that must return to its initial value. Then check: is that the same list as after a
   *good* frame? If you have two separate "reset" code paths that must stay in sync,
   consider one helper both call.

---

## Tests it must pass

Build a helper that feeds an array of bytes and returns how many frames came out.
Then build a helper that *constructs* a valid frame (computing the CRC) so your tests
don't hand-encode checksums.

| Test | What it's protecting against |
| --- | --- |
| A clean frame parses and the payload matches | Baseline |
| Leading garbage before the start byte is discarded, and the frame behind it still parses | The most common real-world case — you joined mid-stream |
| A bad CRC rejects the frame, increments the counter, and leaves the parser ready | Corruption handling *and* recovery |
| A truncated frame followed by a good frame — the good one still parses | The unplugged-cable case. Frequently fails |
| A length byte larger than the payload buffer is rejected without overrunning | Buffer overflow. **ASan will confirm** |
| The start byte appearing **inside** a payload does not derail the parse | `0xAA` is just a data value once you're in `P_PAYLOAD`. Naive implementations resync on it and lose the frame |
| Two frames back to back with no gap both parse | The CRC-reset bug and any end-of-frame cleanup you missed |

Also assert the counters add up: `frames_ok + frames_bad` should equal the number of
frames you actually fed. A parser that silently loses a frame without counting it
anywhere is worse than one that counts it as bad.

---

## Once it's boring

**Second pass — table-driven CRC and byte stuffing.** Precompute a 256-entry lookup
table so the CRC is one array index per byte instead of eight iterations; generate the
table with a small program and paste it in as a `static const`. Then add an escape
scheme (byte stuffing) so `0xAA` can appear in the payload without ambiguity — pick a
escape byte, and define what happens when the escape byte itself appears in data.
That last question is where people discover the scheme they invented doesn't quite
work.

**Third pass — a timeout.** Abandon a partial frame if the remaining bytes never
arrive. That needs a tick input or a timestamp, which changes the API — think about
how to add it without making the common path more expensive. This is what actually
happens when a cable is pulled mid-message, and it's the difference between a link
that recovers by itself and one that needs a reboot.

---

> **Log slugs:** `basic` → `stuffed` → `timeout`. Record each session in
> [log.tsv](../log.tsv) under the variant you actually wrote — time is only
> comparable within a variant. See [LOGGING.md](../LOGGING.md).

## The publishable angle

**Fuzzing, and it's a genuinely uncommon thing to find in a junior portfolio.**

Generate thousands of randomly corrupted frames — truncated at random points,
individual bits flipped, random garbage prefixed and interleaved — feed them all in,
and show that the parser never overruns, never wedges, always recovers, and that the
counters add up exactly. Run the whole thing under ASan and UBSan.

That demonstrates defensive thinking and a testing instinct rather than an
implementation, which is the entire difference between "I implemented a parser" and a
portfolio piece.
