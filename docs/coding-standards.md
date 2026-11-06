# Coding standards

Kokeb Labs code follows named, published coding standards, so that a reviewer, an auditor or a customer can check
our claims against a reference they already know.

| Standard | Used for | How we follow it |
| --- | --- | --- |
| **MISRA C++:2023** | C++ code | Reference standard. A compliance matrix classifies every guideline (below). |
| **MISRA C:2025** | C code | Reference standard, with the same compliance matrix. |
| **SEI CERT C++ and CERT C** | Security baseline | Every rule an open tool can decide is checked by clang-tidy (`cert-*`) or cppcheck. |
| **C++ Core Guidelines** | Design and idiom | Followed through the clang-tidy `cppcoreguidelines-*` checks and the [Standards](standards/index.md) pages. |
| **NASA/JPL Power of Ten** | Embedded discipline | Covered by rules on memory, loops and checking every result. |

## What "follows MISRA" means here

We use the approach MISRA itself defines in *MISRA Compliance:2020*:

1. **Guideline enforcement plan.** For every guideline of MISRA C++:2023 and MISRA C:2025, the compliance matrix
   (`compliance/misra-cpp-2023.yml` and `compliance/misra-c-2025.yml`) records how it is verified:
    - **tool:** a named clang-tidy or cppcheck check, or a compiler flag, that decides it;
    - **review:** it is undecidable or no open tool decides it, so it is on the pull-request checklist;
    - **commercial checker:** decided by the MISRA checker that the safety level adds;
    - **not applicable:** the construct cannot occur in our code (for example, guidelines about exceptions, which
      we do not use), with the reason.
2. **Guideline re-categorisation plan.** Where our profile is stricter than MISRA (an advisory guideline we treat
   as required), the matrix says so. We never make a guideline weaker than MISRA classifies it.
3. **Deviations.** Every departure from a required guideline has a [deviation record](deviations.md). Mandatory
   guidelines are never deviated.
4. **Compliance summary.** Each release of a high or safety component states, per guideline, whether it is
   compliant, deviated or not applicable. It is generated from the matrix and the deviation records.

## What open tools can and cannot prove

clang-tidy, cppcheck and the compilers decide a large part of MISRA and CERT, but not all of it: some guidelines
are undecidable in general, and some decidable ones are only implemented by commercial checkers (Cppcheck Premium,
Helix QAC, Parasoft C/C++test, Polyspace and others). The matrix never claims a guideline is checked by a tool
that does not check it. At the **safety** level a commercial checker runs on every release, under the licence of
the organisation qualifying the component, and its report becomes part of the evidence package.

## Copyright

The MISRA and CERT documents are copyrighted. The handbook cites guideline numbers with our own one-line
summaries; it does not reproduce their text. Contributors working at the safety level need their own copies of
the standards.
