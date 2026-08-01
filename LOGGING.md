# The practice log — and what the website reads

## Why this file exists

On most mornings you write in a scratch directory and delete the result. Nothing
gets committed. `log.tsv` is the only artifact of a session that didn't promote
code — without it, four weeks of genuine practice leave no trace in this repo.

It also isn't an invented metric. The guide already defines done as *"you can write
it from a blank file in fifteen minutes, it compiles clean under strict flags, and
the sanitizers stay silent."* That is a number with a threshold. The log records the
number that was already the standard.

And a time curve is useful to a stranger in a way a checklist isn't. "Ring buffer:
31 minutes, then 22, then 14" tells someone else learning this what the curve
actually looks like. A row of green ticks tells them nothing.

---

## Three tiers, three jobs

Each holds a different kind of thing, and they should not blur together.

| Lives in | Holds | Shows on the site as |
| --- | --- | --- |
| `log.tsv` | the numbers | time curve per module, done-bar at 15 min, six ticks |
| `<module>/NOTES.md` | the design decision and the bug | each module's note on the project page |
| the site's own blog | measurements, traces, captures | the 2–4 real writeups |

The rule that keeps them separate: **a blog post is triggered by a measurement, not
by a completion.** Finishing a kata is a row in `log.tsv`. Capturing a real switch
bouncing on a scope, or the ARM assembly with and without `volatile`, is a post.
"I implemented X" is worth nothing; "here is X, here is the capture proving the
problem was real, here is the number before and after" is a portfolio piece.

---

## The format

Tab-separated, one row per session, append-only:

```
date	module	variant	minutes	clean	note
2026-08-04	ring_buffer	naive	31	n	forgot the count guard on pop
2026-08-11	ring_buffer	naive	22	y
2026-08-18	ring_buffer	naive	14	y	first time under the bar
2026-08-25	ring_buffer	lockfree	27	n	volatile on both indices, still raced
```

| Column | Rules |
| --- | --- |
| `date` | `YYYY-MM-DD`. Rows stay in date order. |
| `module` | Must name a real directory in this repo. |
| `variant` | Must be one of that module's slugs — see the table below. |
| `minutes` | Whole number. Blank file to working, not counting reading the brief. |
| `clean` | `y` or `n`. See below — it has a precise meaning. |
| `note` | Optional free text. One clause. What went wrong, usually. |

**TSV rather than JSON, deliberately.** Appending a line by hand at 6:40am shouldn't
involve balancing brackets, and a merge conflict in a text row is far easier to
resolve than one inside a JSON array.

### What `clean` means

`y` means: it compiled under `-Werror` and **both sanitizers stayed silent on the
first run.**

First run. Not "after I fixed the thing ASan caught." If ASan fired and you fixed it,
that session is `n` with a note saying what it caught — which is the useful row,
because the point of the curve is watching `n` turn into `y`.

### Why the variant column is not optional

Pass two of the ring buffer is the lock-free version, which is legitimately harder
and slower than the naive one. Without the variant, 14 minutes becoming 27 looks like
regression when it's actually a harder exercise. **Time is only comparable within a
variant.**

The slugs come from the "Once it's boring" section of each module's `BRIEF.md` —
first pass, second pass, third pass, in progression order:

| Module | First | Second | Third |
| --- | --- | --- | --- |
| `ring_buffer` | `naive` | `lockfree` | `bitmask` |
| `debouncer` | `counter` | `integrator` | `shiftreg` |
| `fsm` | `switch` | `table` | `actions` |
| `bitops` | `plain` | `peripheral` | `branchless` |
| `fixed_point_pid` | `basic` | `dmeas` | `filtered` |
| `protocol_parser` | `basic` | `stuffed` | `timeout` |

Adding a fourth pass to a kata means adding the slug to `VARIANTS` in
[tools/check_log.py](tools/check_log.py), or the log will reject the row. That
friction is on purpose — it stops `lock-free` and `lockfree` silently splitting one
curve into two.

### The tick

A module earns its tick when it first comes in **at or under 15 minutes with
`clean = y`**. There are only six ticks available, and a tick is **lost again when
you move to the next variant** — starting the lock-free ring buffer puts that module
back in progress until the lock-free version is under the bar too.

That's the honest version. A tick per session would be the green-squares thing the
guide warns about; a tick per module reaching a real threshold is a fact, and it's
derived from the log rather than being bookkeeping you maintain separately.

---

## Using it

```bash
make log         # print the time curve per module and who's at the bar
make check-log   # validate the format (CI runs this on every push)
```

`make log` on a populated file:

```
ring_buffer
  naive       31n -> 22y -> 14y  [bar met 2026-08-18]
  lockfree    27n  (never clean yet)
  bitmask     (not started)
  in progress — current variant: lockfree
```

The CI check keeps the file from quietly rotting: it rejects spaces-instead-of-tabs,
unknown modules or variants, malformed dates, out-of-order rows, bad `clean` values,
missing trailing newline, and CRLF line endings. Every message names the line number
and what to do about it.

---

## The contract with the website

Per ADR-007, this repo owns the facts; the site generates from them and stores
nothing of its own. A generator script reads:

**1. `log.tsv`** — parsed as described above. Stable guarantees: the header row is
exactly those six names, rows are in date order, `clean` is `y`/`n`, and `minutes` is
an integer. The `note` field may be empty or absent (a 5-field row is valid).

**2. `<module>/NOTES.md`** — three or four lines per module. These three bold labels
are load-bearing, because the generator keys on them:

```markdown
**What it does.** ...

**Design decision.** ...

**What bit me.** ...
```

Keep the labels exactly as written when you fill a `NOTES.md` in. If you want to
change them, change them in all six and in the generator together.

Everything else in this repo — the briefs, `GETTING_STARTED.md`, `VERIFYING.md` — is
for working in the repo, not for the site to render.

---

## The habit

Add the row before you delete the scratch file, while you still remember the number.
It's one line, it takes ten seconds, and it is the only thing that will still exist
in December from a morning in August.
