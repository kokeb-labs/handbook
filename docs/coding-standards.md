# Coding standards

Kokeb Labs code follows named, published coding standards, so that a reviewer, an auditor or a customer can check
our claims against a reference they already know.

| Standard | Used for | How we follow it |
| --- | --- | --- |
| **MISRA C++:2023** (with TC1:2026) | C++ code | Reference standard. A compliance matrix classifies every guideline (below). |
| **MISRA C:2025** | C code | Reference standard; its compliance matrix follows the same format (not written yet). |
| **SEI CERT C++ and CERT C** | Security baseline | Every rule an open tool can decide is checked by clang-tidy (`cert-*`) or cppcheck. |
| **C++ Core Guidelines** | Design and idiom | Followed through the clang-tidy `cppcoreguidelines-*` checks and the [Standards](standards/index.md) pages. |
| **NASA/JPL Power of Ten** | Embedded discipline | Covered by rules on memory, loops and checking every result. |

## What "follows MISRA" means here

We use the approach MISRA itself defines in *MISRA Compliance:2020*:

1. **Guideline enforcement plan.** For every guideline of MISRA C++:2023, the compliance matrix
   ([`compliance/misra-cpp-2023.yml`][matrix]) records how it is verified (MISRA C:2025 gets
   `compliance/misra-c-2025.yml` in the same format):
    - **tool:** a named clang-tidy or cppcheck check, or a compiler flag, that decides it;
    - **review:** it is undecidable or no open tool decides it, so it is on the pull-request checklist;
    - **commercial checker:** decided by the MISRA checker that the safety level adds;
    - **not applicable:** the construct cannot occur in our code (for example, guidelines about exceptions, which
      we do not use), with the reason.
2. **Guideline re-categorisation plan.** Where our profile is stricter than MISRA (an advisory guideline we treat
   as required), the matrix says so. We never make a guideline weaker than MISRA classifies it.
3. **Deviations.** Every departure from a required guideline has a [deviation record](deviations.md): project-wide
   ones in [`compliance/misra-cpp-2023-deviations.yml`][deviations], single places in the repository's own
   `docs/deviations.yml`. Mandatory guidelines are never deviated.
4. **Compliance summary.** Each release of a high or safety component states, per guideline, whether it is
   compliant, deviated or not applicable. It is generated from the matrix and the deviation records.

## The edition

The matrix is written against **MISRA C++:2023 with Technical Corrigendum 1 (TC1:2026)**. The corrigendum adds no
guidelines and is equivalent to MISRA C++:2023, but clarifies many of them, so tool reports can differ from the
2023 text. The licensed copy the matrix was written from is held privately by the maintainer; the matrix records its
SHA-256 (`licensed_copy_sha256`), so any entry can be traced to the exact edition it was checked against. When MISRA
publishes a new corrigendum or edition, the matrix is reviewed against it in one pull request that changes the hash.

MISRA C++:2023 targets C++17; our code is C++20 (ADR-0010). Deviation MD-CPP-001 records that, lists the C++20
features in use, and says how each guideline applies to C++20 constructs.

## Reading the matrix

Each guideline has one entry:

| Field | Meaning |
| --- | --- |
| `id` | The guideline number, `Rule a.b.c` or `Dir a.b.c`. |
| `kind` | `rule` (checkable from the code alone) or `directive` (needs design or requirements information). |
| `category` | MISRA's category: `mandatory`, `required` or `advisory`. |
| `decidable` | Whether an analyser can always answer "compliant?" (`yes`/`no`); `n/a` for directives. |
| `scope` | `tu` when one translation unit at a time is enough, `system` when the whole program is needed. |
| `summary` | Our own one-line paraphrase (at most 12 words); the standard's text is not reproduced. |
| `applies` | `yes`, or `no` with a `reason` (for example, the exception guidelines: we build with `-fno-exceptions`). |
| `our_category` | The category we enforce: MISRA's or stricter, never weaker. A stricter one is our re-categorisation plan. |
| `verification` | How it is checked: each item names `by` (method) and `how` (the exact flag, check or review step). |
| `deviations` | The project-wide deviation records that cover part of the guideline, if any. |
| `note` | Anything a reader needs to apply the guideline to our code. |

The verification methods are:

- `compiler`: a GCC or Clang flag (with `-Werror`) whose diagnostic decides the guideline;
- `clang-tidy`: a clang-tidy 20 check, with its options where they matter;
- `cppcheck`: a cppcheck message id (there is no free MISRA C++ addon; cppcheck's MISRA addon covers MISRA C only);
- `handbook-check`: one of the handbook's own implemented checks;
- `review`: the step a reviewer checks on the pull request, used where no free tool decides the guideline;
- `commercial-checker`: the MISRA checker the safety level adds, for every guideline no free tool decides;
- `not-applicable`: the construct cannot occur in our code, and why.

A tool item marked `partial: true` finds some violations but cannot prove there are none (an undecidable guideline,
or a check narrower than the guideline); such a guideline always also has a review step and the commercial checker.
A tool is only listed for a guideline it actually checks. Several clang-tidy checks the matrix names are outside the
org's default `config/.clang-tidy`; a repository at the safety level enables them, and `checks/misra_matrix.py`
lists them on every run.

[`checks/misra_matrix.py`](https://github.com/kokeb-labs/handbook/blob/main/checks/misra_matrix.py) validates the
matrix and the deviations on every pull request: every guideline present exactly once (179), valid categories,
`our_category` never weaker, a verification for every applicable guideline, a reason for every guideline that does
not apply, and no deviation of a mandatory guideline. It also keeps the counts below current.

### Counts

<!-- misra-counts:begin (generated by checks/misra_matrix.py gen) -->

MISRA C++:2023 with TC1:2026 has **179 guidelines**: 4 directives and 175 rules.

| MISRA category | Directives | Rules | Total | Our category |
| --- | --- | --- | --- | --- |
| mandatory | 0 | 5 | 5 | 5 |
| required | 2 | 122 | 124 | 131 |
| advisory | 2 | 48 | 50 | 43 |
| **all** | 4 | 175 | 179 | 179 |

| How it is verified | Guidelines |
| --- | --- |
| Decided by an open tool (compiler, clang-tidy, cppcheck, handbook check) | 46 |
| &nbsp;&nbsp;of which by compiler | 11 |
| &nbsp;&nbsp;of which by clang-tidy | 35 |
| Review and commercial checker, helped by a partial tool | 80 |
| Review and commercial checker only | 46 |
| Not applicable to our code | 7 |

A guideline can be decided by more than one tool. Raised above MISRA's category: 7 (Dir 5.7.2, Rule 6.0.3, Rule 9.6.1,
Rule 10.2.2, Rule 12.2.1, Rule 13.1.1, Rule 21.6.1). Project-wide deviations: 8 (MD-CPP-001 Rule 4.1.1, MD-CPP-002 Rule
16.6.1, MD-CPP-003 Rule 8.2.5, MD-CPP-004 Rule 8.2.6, MD-CPP-005 Rule 6.7.2, MD-CPP-006 Rule 19.0.2, MD-CPP-007 Rule
21.2.4, MD-CPP-008 Rule 21.6.1).

<!-- misra-counts:end -->

## What open tools can and cannot prove

clang-tidy, cppcheck and the compilers decide a large part of MISRA and CERT, but not all of it: some guidelines
are undecidable in general, and some decidable ones are only implemented by commercial checkers (Cppcheck Premium,
Helix QAC, Parasoft C/C++test, Polyspace and others). The matrix never claims a guideline is checked by a tool
that does not check it. At the **safety** level a commercial checker runs on every release, under the licence of
the organisation qualifying the component, and its report becomes part of the evidence package.

## Copyright

The MISRA and CERT documents are copyrighted. The handbook cites guideline numbers, categories and analysis
attributes with our own one-line summaries; it does not reproduce headlines, rationale, examples or tables, and the
standard itself is never committed to any repository. Contributors working at the safety level need their own
licensed copies of the standards.

[matrix]: https://github.com/kokeb-labs/handbook/blob/main/compliance/misra-cpp-2023.yml
[deviations]: https://github.com/kokeb-labs/handbook/blob/main/compliance/misra-cpp-2023-deviations.yml
