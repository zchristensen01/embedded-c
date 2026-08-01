#!/usr/bin/env python3
"""Validate and summarise log.tsv — the kata practice log.

    python3 tools/check_log.py             validate (CI runs this on every push)
    python3 tools/check_log.py --summary   print the time curve per module

Or via make: `make check-log` and `make log`. Format spec: LOGGING.md.
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "log.tsv"

HEADER = ["date", "module", "variant", "minutes", "clean", "note"]

# Variant vocabulary, in progression order. These slugs come from the "Once it's
# boring" section of each module's BRIEF.md — first pass, second pass, third
# pass. Adding a fourth pass to a kata means adding its slug here, otherwise the
# log will reject it.
VARIANTS = {
    "ring_buffer":     ["naive", "lockfree", "bitmask"],
    "debouncer":       ["counter", "integrator", "shiftreg"],
    "fsm":             ["switch", "table", "actions"],
    "bitops":          ["plain", "peripheral", "branchless"],
    "fixed_point_pid": ["basic", "dmeas", "filtered"],
    "protocol_parser": ["basic", "stuffed", "timeout"],
}

# The guide's definition of done: "you can write it from a blank file in fifteen
# minutes ... and the sanitizers stay silent". Both halves are required.
BAR_MINUTES = 15


def fail(errors):
    for e in errors:
        print(e, file=sys.stderr)
    print(f"\n{len(errors)} problem(s) in log.tsv — see LOGGING.md", file=sys.stderr)
    sys.exit(1)


def parse():
    """Return (rows, errors). A row is a dict; errors are human-readable strings."""
    errors = []

    if not LOG.exists():
        return [], [f"{LOG} does not exist"]

    raw = LOG.read_bytes()
    if b"\r" in raw:
        errors.append("log.tsv: contains carriage returns — save it with Unix line endings")
    if raw and not raw.endswith(b"\n"):
        errors.append("log.tsv: no trailing newline (an append would join two rows)")

    lines = raw.decode("utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    if not lines:
        return [], ["log.tsv: empty — it needs at least the header row"]

    if lines[0].split("\t") != HEADER:
        errors.append(f"log.tsv:1: header must be exactly: {chr(9).join(HEADER)}")

    # Catch a directory that was renamed without updating VARIANTS above.
    for module in VARIANTS:
        if not (ROOT / module).is_dir():
            errors.append(f"check_log.py: VARIANTS names '{module}', which is not a directory")

    rows = []
    prev_date = None

    for n, line in enumerate(lines[1:], start=2):
        where = f"log.tsv:{n}"

        if not line.strip():
            errors.append(f"{where}: blank line — the log is append-only, no gaps")
            continue

        fields = line.split("\t")
        if len(fields) not in (5, 6):
            errors.append(
                f"{where}: has {len(fields)} tab-separated fields, expected 5 or 6 "
                f"(note is optional). Check you used tabs, not spaces."
            )
            continue
        if len(fields) == 5:
            fields.append("")

        d, module, variant, minutes, clean, note = fields

        for name, value in (("date", d), ("module", module), ("variant", variant),
                            ("minutes", minutes), ("clean", clean)):
            if value != value.strip():
                errors.append(f"{where}: {name} '{value}' has leading or trailing whitespace")

        row_date = None
        try:
            row_date = date.fromisoformat(d.strip())
        except ValueError:
            errors.append(f"{where}: date '{d}' is not a valid YYYY-MM-DD")

        if row_date:
            if prev_date and row_date < prev_date:
                errors.append(
                    f"{where}: date {d} is earlier than {prev_date} on the line above — "
                    f"keep rows in date order"
                )
            prev_date = row_date

        module = module.strip()
        variant = variant.strip()

        if module not in VARIANTS:
            errors.append(
                f"{where}: unknown module '{module}' — expected one of "
                f"{', '.join(sorted(VARIANTS))}"
            )
        elif not (ROOT / module).is_dir():
            errors.append(f"{where}: module '{module}' is not a directory in this repo")
        elif variant not in VARIANTS[module]:
            errors.append(
                f"{where}: unknown variant '{variant}' for {module} — expected one of "
                f"{', '.join(VARIANTS[module])} (see {module}/BRIEF.md)"
            )

        mins = None
        try:
            mins = int(minutes.strip())
            if mins <= 0:
                errors.append(f"{where}: minutes '{minutes}' must be a positive whole number")
        except ValueError:
            errors.append(f"{where}: minutes '{minutes}' must be a whole number")

        if clean.strip() not in ("y", "n"):
            errors.append(
                f"{where}: clean '{clean}' must be y or n "
                f"(y = compiled under -Werror and both sanitizers stayed silent on the first run)"
            )

        if row_date and mins:
            rows.append({
                "date": row_date, "module": module, "variant": variant,
                "minutes": mins, "clean": clean.strip() == "y", "note": note,
            })

    return rows, errors


def summarise(rows):
    if not rows:
        print("log.tsv has no sessions yet.\n")
        print("Add a row after tomorrow's drill:")
        print(f"  {date.today().isoformat()}\tring_buffer\tnaive\t31\tn\tforgot the count guard on pop")
        return

    at_bar = 0

    for module, variants in VARIANTS.items():
        print(module)
        for variant in variants:
            sessions = [r for r in rows if r["module"] == module and r["variant"] == variant]
            if not sessions:
                print(f"  {variant:<11} (not started)")
                continue

            curve = " -> ".join(f"{s['minutes']}{'y' if s['clean'] else 'n'}" for s in sessions)
            met = next((s for s in sessions if s["minutes"] <= BAR_MINUTES and s["clean"]), None)
            if met:
                tail = f"  [bar met {met['date']}]"
            else:
                best = min(s["minutes"] for s in sessions if s["clean"]) if any(s["clean"] for s in sessions) else None
                tail = f"  (best clean: {best})" if best else "  (never clean yet)"
            print(f"  {variant:<11} {curve}{tail}")

        # The tick is per module, and it is lost again when you move to a harder
        # variant — status follows the most recent variant worked on.
        latest = [r for r in rows if r["module"] == module]
        if latest:
            current = max(latest, key=lambda r: r["date"])["variant"]
            done = any(r["minutes"] <= BAR_MINUTES and r["clean"]
                       for r in latest if r["variant"] == current)
            at_bar += done
            print(f"  {'DONE' if done else 'in progress'} — current variant: {current}")
        print()

    print(f"modules at the bar: {at_bar}/{len(VARIANTS)}   "
          f"({len(rows)} sessions logged, {rows[0]['date']} to {rows[-1]['date']})")


def main():
    rows, errors = parse()
    if errors:
        fail(errors)

    if "--summary" in sys.argv:
        summarise(rows)
    else:
        print(f"log.tsv ok — {len(rows)} session(s)")


if __name__ == "__main__":
    main()
