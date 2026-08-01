# template — not a kata

A deliberately trivial module (`clamp`) that exists for two reasons:

1. **It proves your toolchain works.** Before you have written a line of your own,
   `make test` builds and runs something under `-Werror` and both sanitizers. If
   this passes, nothing that goes wrong later is your compiler's fault.
2. **It shows the three-file shape in real, compiling C** — what belongs in the
   header, what belongs in the implementation, what a test file looks like. Every
   kata directory has a `SKELETON.md` describing its own version of this shape in
   pseudocode; this is the same thing you can actually run.

```bash
make test MODULE=template
```

The comments explain the *structure*, not the clamping — `clamp` is three lines
precisely so that nothing distracts from the layout.

It is not one of the six katas, it is not part of the rotation, and it is not
loggable in `log.tsv`. Leave it here as a reference, or delete it once the shape
is second nature.
