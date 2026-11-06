# ADR-0020: Complexity limits and coverage floors per assurance level

- Status: Accepted
- Date: 2026-11-06

## Context

The handbook asked for "a coverage floor" without saying how coverage is measured, and had no rule on code
complexity at all. Both are among the first things a safety assessor asks about, and both are meaningless without
a fixed tool, a fixed definition and a number that is defended in writing.

## Decision

### Complexity

Measured by **lizard** on library code (`inc/`, `src/`, kb-core and HAL sources; not tests or examples), using
the *modified* cyclomatic complexity, which counts a whole `switch` as one decision: a flat enum-to-string table
is not branching logic a reader has to hold in their head.

| Limit per function | standard | high | safety |
| --- | --- | --- | --- |
| Cyclomatic complexity (modified) | 15 | 15 | 10 |
| Length (lines of code, without blanks and comments) | 80 | 60 | 60 |
| Parameters | 7 | 6 | 6 |

Ten is McCabe's original limit, and NIST SP 500-235 recommends it, allowing up to 15 for experienced teams with a
review of each case. Sixty lines is the NASA/JPL Power of Ten limit (one printed page). A function over a limit
that is genuinely clearer as one piece, for example a state machine's transition table, has a deviation record
(see Deviations); it is never split just to satisfy the number.

### Coverage

Measured by **gcovr** over the host tests built with the pinned GCC at `-O0 --coverage`, counting only library
code (as above), with unreachable branches and branches the compiler adds for exceptions excluded (we do not use
exceptions). Compile-only targets that never run are not part of the measurement.

| Floor (library code) | standard | high | safety |
| --- | --- | --- | --- |
| Lines | reported | 85% | 100% of reachable lines |
| Branches | reported | 75% | 100% of reachable branches |
| MC/DC (GCC condition coverage) | not measured | reported | 100% |

At the **safety** level, every line, branch or condition the tests do not reach is listed in
`docs/coverage-justification.yml` with the reason (for example, a defensive check that the hardware cannot
trigger, verified by review) and who accepted it. The coverage check fails when an unreached item has no
justification, or a justification names an item the tests now reach. MC/DC uses GCC's `-fcondition-coverage`,
which measures whether each condition in a decision independently affects its outcome.

### Test quality

Coverage shows what ran, not what was checked. At the **safety** level, mutation testing (for example Mull)
runs on each release and its surviving mutants are reviewed; this is guidance until the tooling is proven on our
code base.

## Consequences

- Rules KB-CPP-115 (complexity), KB-TST-004 (coverage floors) and KB-TST-027 to 029 encode these numbers.
- ci-tools gains a reusable workflow that runs lizard, gcovr and the sanitizers and fails on these limits.
- Raising a floor is a minor handbook release with an `enforce_from` date; lowering one needs a new record.
