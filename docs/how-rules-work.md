# How rules work

## A rule is data

Each rule lives in `rules/<area>.yml` and has:

| Field | Meaning |
| --- | --- |
| `id` | `KB-<AREA>-<NNN>`, for example `KB-CPP-003`. Never reused, never renumbered. HardFOC's supplement uses `HF-`. |
| `level` | `must`: CI or review fails without it. `should`: the pull request says why if it is not followed. `guide`: how we prefer to do it. |
| `applies` | The repository kinds it applies to (`driver`, `library`, `hal`, `firmware`, `tooling`, `docs`, `template`, or `all`) and the lowest [assurance level](assurance-levels.md) it applies from. |
| `verify` | How it is verified: a `check` from the [check registry](https://github.com/kokeb-labs/handbook/blob/main/checks/registry.yml), or `review` with the checklist line a reviewer confirms. |
| `status` | `proposed` (warns, with `enforce_from`), `active` (enforced), or `retired` (kept so the ID is never reused). |
| `refs` | The decision record behind it, and the clauses of MISRA, CERT, the C++ Core Guidelines or IEC 62304 it corresponds to. |

The pages under [Rules](rules/cpp.md) are generated from these files, and CI fails if they are stale, so the
words you read are the data CI enforces.

## What makes a rule valid

The handbook's own CI (`checks/handbook.py`) refuses:

- an active `must` rule with no check and no review line;
- a check that is not in the registry, or a registry entry marked implemented without saying where it runs;
- a duplicate or reused ID;
- a reference to a decision record, page or standard that does not exist.

Every check in the registry is either **implemented** (it runs in a named workflow and fails on a finding) or
**planned**. The [coverage page](rules/coverage.md) counts both, so the gap between what we say and what we check is
always visible.

## How a repository follows the handbook

A repository declares, in `.kokeb/handbook.yml`:

```yaml
handbook: "1.0"        # the handbook release it follows
kind: driver
level: high            # standard | high | safety
waivers:               # see Deviations and waivers
  - rule: KB-DOC-004
    reason: Doxygen comments for the v2 register API land with #41
    approved_by: "@N3b3x"
    until: 2027-01-31
```

Its CI calls the conformance workflow, which runs every check that applies to its kind and level and reports
each failure by rule ID, with the rule's text and a link here. People and agents see the same thing.

## How rules change

- A new `must` rule arrives as `proposed` with an `enforce_from` date: it warns until that date, then fails.
- Tightening or removing a rule needs a decision record.
- The handbook is released like code (`v1.0.0`, `v1.1.0`, …). Repositories pin a minor version and move up on
  purpose, the way they pin `ci-tools@v1`.
