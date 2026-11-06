# Deviations and waivers

A rule can be set aside, but never silently. There are two kinds of exception, and both are checked by CI.

## A deviation: one place in the code

When a check flags code that is correct and deliberate, the finding is suppressed where it occurs, with the check
named and the reason stated:

```cpp
// The not-in-range form is deliberate: a NaN fails every comparison, so it is rejected here.
// NOLINTNEXTLINE(readability-simplify-boolean-expr)
if (!(value >= kMin && value <= kMax)) {
```

- At the **standard** level, the comment is the record.
- At the **high** and **safety** levels, every suppression also has an entry in `docs/deviations.yml` of the
  repository, which the conformance check compares with the suppressions in the code: an entry without a
  suppression, or a suppression without an entry, fails CI.

```yaml
- id: DEV-007
  rule: KB-CPP-008
  check: clang-tidy/readability-simplify-boolean-expr
  where: inc/xmpl100_types.hpp
  reason: The negated range test rejects NaN, which the rewritten form would accept.
  risk: None; the alternative is the defect.
  approved_by: "@N3b3x"
  date: 2026-11-06
```

This follows the deviation-record model of MISRA Compliance:2020: the guideline, the location, the justification,
the consequence, and who accepted it.

## A waiver: a whole rule, for a while

When a repository cannot meet a rule yet, it records a waiver in `.kokeb/handbook.yml`:

```yaml
waivers:
  - rule: KB-DOC-004
    reason: Doxygen comments for the v2 register API land with #41.
    approved_by: "@N3b3x"
    until: 2027-01-31
```

The conformance check reports the waiver on every run, and fails once `until` has passed. A waiver is a dated
promise, not a permanent exemption; a rule that a repository will never meet needs a decision record that changes
the rule or its scope instead.

## What cannot be waived

At the **safety** level, MISRA's mandatory guidelines and the evidence package cannot be waived (MISRA does not
permit deviations from mandatory guidelines either). They can only be met, or the component's level lowered.
