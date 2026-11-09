# Changelog

All notable changes to the handbook are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): a new or tightened rule is a minor release, a removed or
loosened rule is a major release.

## [Unreleased]

### Added

- The C++20 profile: 58 guidelines KB-CPP20-001 to 058 (`rules/cpp20.yml`; 4 mandatory, 36 required, 18
  advisory) that extend MISRA C++:2023 to the C++20 we write, and the page Standards > C++20 profile, which sorts
  59 features into use (17), use with rules (24) and forbid (18), with each guideline's MISRA numbers and
  enforcement. Required and mandatory guidelines are `proposed` and enforced from 2027-03-01.
- `checks/source_checks.py`: the C++20 profile checks `cpp20-profile/forbidden-features` (coroutines, modules,
  range views, `<format>`, C++23 features, feature-test macros, `[[fallthrough]]`, `char8_t`, and in drivers
  `<=>`, `<source_location>`, `variant`, `any`, `function`), `cmake-extensions` (every CMakeLists.txt that builds a
  target sets `CMAKE_CXX_EXTENSIONS OFF`, which the ci-tools check only enforced by rejecting `ON`),
  `nodiscard-error`, `inline-requires` and `kconfig-leaf`, each with seeded breaks in the self-test.
- Checks `strict-dialect`, `library-hardening` and the planned `codeql` family in the registry;
  `header-self-contained` is implemented by the driver template's header checks.

### Changed

- The MISRA matrix names CodeQL (`by: codeql`, a new verification method) for the 168 guidelines whose
  queries the ci-tools tool validation proves: 73 decided by it (decidable, translation-unit scope, every query
  passing with no recorded anomaly), 95 partial, each citing its requirement and anomaly ids. Nothing was removed:
  the review and commercial-checker steps stay. Rule 8.2.3's clang-tidy check is partial (it misses a cast below
  the first pointer level), so the rule gains a review step.
- KB-CPP-053: a mapping switch lists every enumerator and ends with `default: break;` before its fallback (MISRA
  C++ Rule 9.4.2 requires the default for a scoped enumeration); `-Wswitch-enum` keeps a new enumerator a warning.
  The matrix's review text of Rule 9.4.2 and Standards > Errors say the same; the old "no default" reading was
  wrong.
- New deviation record MD-CPP-009 (Rule 19.0.3): the one `#include "../src/<name>.ipp"` that ends an umbrella
  header.
- MD-CPP-001 now names exactly what it covers: the features the C++20 profile allows, under its guidelines. A
  forbidden or deprecated feature, or anything from C++23 or later, is a violation of Rule 4.1.1 even where a
  toolchain's dialect accepts it. Its mitigation adds the strict-dialect build and the profile's source checks.
- The MISRA matrix's verification of Rules 0.1.2, 4.1.1, 4.1.2, 6.2.1, 7.0.4, 8.7.1, 9.4.2, 9.5.1 and 21.6.1 names
  the profile's checks and flags. KB-CPP-001 also names `cpp20-profile/cmake-extensions` and `strict-dialect`.
- `config/.clang-tidy`: `bugprone-dangling-handle` watches `std::span`; `modernize-use-std-format` and
  `modernize-use-std-print` are off, so the tool never suggests what the profile forbids. The safety profile is
  regenerated.
- Rule ids may carry digits in the area (`KB-CPP20-001`).

- 22 rules from testing the migrated drivers on hardware, all `proposed` and enforced from 2027-03-01: replies
  proven before they are decoded (KB-ARCH-042), pipelined exchanges inside one call (KB-ARCH-043), idempotent,
  bounded and counted retries (KB-ARCH-044), line patterns that are never data (KB-CPP-116), an active identity
  check (KB-CPP-117), resync after a failed transfer (KB-CPP-118), one latch for clear-on-read flags (KB-CPP-119),
  setters that update the copy after success (KB-CPP-120) and change only what they name (KB-CPP-121), whole
  writes of control registers (KB-CPP-122), bus requirements as `constexpr` (KB-CPP-123), a bounded wait for ready
  (KB-CPP-124), the variant confirmed first (KB-CPP-125), operating ranges without silent clamps (KB-CPP-126),
  non-measurements as errors (KB-CPP-127), conversions from the actual setting (KB-CPP-128), single-shot raw
  access and the last raw reply (KB-CPP-129), I2C NACK-by-design, no empty probe and repeated START (KB-CPP-130),
  load diagnostics only on loaded channels (KB-CPP-131), hardware findings as model faults with an independent
  model (KB-TST-030), control outputs inactive before enable (KB-HW-018) and port conformance for the shared-bus
  faults (KB-HW-019). The driver contract gains Bus requirements, Replies, retries and resynchronisation, State,
  shadows and latches, Start-up, and Values and diagnostics.
- `checks/source_checks.py`: the source checks `include-guards`, `bus-requirements` and `raw-access`, with a
  `selftest` that handbook CI runs and a `guard` command that prints the guard a header needs. Standard library
  only, so a repository's CI can run it as it is.
- The safety-level clang-tidy profile, `config/.clang-tidy-safety`, generated by `checks/misra_matrix.py gen` from
  `config/.clang-tidy` and the MISRA matrix and checked for staleness in CI; `misra_matrix.py tidy` lists which
  checks are on at every level and which at the safety level only.

- The MISRA C++:2023 (TC1:2026) compliance matrix, `compliance/misra-cpp-2023.yml`: all 179 guidelines with
  MISRA's category, decidability and scope, our own summary, whether it applies, the category we enforce (seven
  raised above MISRA's) and how each is verified. Eight project-wide deviations in
  `compliance/misra-cpp-2023-deviations.yml`, starting with C++20 itself (MD-CPP-001). `checks/misra_matrix.py`
  validates both on every pull request and keeps the counts on the Coding standards page current.

### Changed

- KB-CPP-019 now requires `#ifndef` include guards instead of `#pragma once` (owner decision, MISRA C++:2023 Rule
  19.2.1), named `<NAME>_<FILE_STEM>_<EXT>` (`ADS7952_TYPES_HPP`), with no reserved names and no `#pragma` of any
  kind; checked by `include-guards`. The MISRA matrix entries for Rules 19.2.1 and 19.6.1 are now decided by that
  check, and their open findings are closed.
- KB-CPP-047 fixes the names and meanings of the common chip-specific codes `NoDevice`, `Pin` and `NotReady`;
  KB-CPP-058 adds "clear or report faults latched before the start"; KB-CPP-038 adds "status bits by meaning".
- `config/.clang-tidy` turns on the cheap checks the MISRA matrix relies on: `hicpp-signed-bitwise` (with
  `IgnorePositiveIntegerLiterals`), `readability-uppercase-literal-suffix` (L, LL, UL, ULL), `misc-no-recursion`,
  `misc-static-assert`, `misc-definitions-in-headers` (`.ipp` is a header), `misc-unconventional-assign-operator`,
  `hicpp-no-assembler`, `hicpp-multiway-paths-covered`, `fuchsia-virtual-inheritance`, `cert-*`, and no longer
  turns off `cppcoreguidelines-pro-type-union-access`, `cppcoreguidelines-pro-type-vararg` (the `Log` hook takes a
  plain string; the driver contract said it was printf-shaped) or `portability-avoid-pragma-once`.

- New rule KB-ARCH-041 (proposed, enforced from 2026-12-01): extra read-back and verification in a driver are
  chosen per call with a `Verify` argument that defaults to `Verify::None`; the driver contract gains
  "Verification is opt-in".

- Migration checklist: four findings from the AT25040B migration (an active identity check, a confirmed idle
  status, WP parked after every call, the scaffold's full stop).
- The handbook is public: CI publishes the site from `main` to <https://kokeb-labs.github.io/handbook/>.

### Added

- Migration checklist: "Drivers that are already proven on hardware". Hardware evidence belongs to the old code at
  a commit, on a board, by a procedure; a rewrite records it in `docs/limitations.md`, turns each hardware quirk
  into a model fault and a test, checks the firmware's real calls, and claims "verified on hardware" only after the
  same bench procedure. Also a fuzz-target step, and the pilots' new findings (a lost-frame OTP burn found by
  fuzzing, the output-latch read-back, the plain-text `Log()` hook, Pages on private repositories).

- The handbook as data: rules in `rules/*.yml` with IDs, levels, scope and verification; the check registry; the
  repository kinds and assurance levels; `checks/handbook.py` to validate the rules and generate their pages and
  the coverage report.
- Pages on how rules work, assurance levels (standard, high, safety), deviations and waivers, coding standards
  (MISRA C++:2023, MISRA C:2025, CERT, C++ Core Guidelines), evidence for regulated products, and IEC 62304.
- The engineering standard, decision records 0001 to 0015 and checklists, moved from `kokeb-labs/.github`.
- 402 rules in 11 areas (architecture, C++, C, hardware and porting, build, testing, documentation, repository, Git,
  CI, agents), converted from the Kokeb engineering standard and the HardFOC development handbook, with conflicts
  resolved in favour of the Kokeb standard; 3 duplicates retired. 270 are `must` rules: 76 checked by a tool today,
  159 naming a planned check, 35 verified in review.
- 53 HardFOC-only rules in `hf-supplement/`, validated against the same registry.
- 134 checks in the registry: 15 implemented, the rest planned and listed on the coverage page.
- The generator escapes Markdown in rule text, so names like `<chip>` and `KB_` render as written.
- Decision records 0016 to 0020: virtual functions only at three run-time boundaries; the target library subset
  replaces "freestanding"; `sdkconfig.defaults` only, the effective `sdkconfig` attached to releases; datasheets
  referenced by revision and SHA-256, never committed; complexity limits and coverage floors per assurance level.
- Rules for complexity (KB-CPP-115), MC/DC at safety level (KB-TST-027), justified coverage gaps (KB-TST-028) and
  mutation testing (KB-TST-029); the coverage floor now says how coverage is measured.

- The complexity, coverage and sanitizer checks are implemented by ci-tools' `ru-host-quality` (v1.2.0); rules
  KB-CPP-115 (complexity), KB-TST-003 (sanitizers), KB-TST-004 (coverage floors) and KB-TST-027 (MC/DC at safety
  level) are active.

- Phase A checks are implemented: the handbook declaration and waivers, the driver root layout, `driver.yml`,
  banned code patterns (heap, exceptions and RTTI, virtual functions in drivers, `file(GLOB)`, C++20), the target
  library subset of headers and committed `sdkconfig` or PDFs (ci-tools `ru-handbook-check`); Doxygen failing on
  warnings (`ru-mkdocs-publish` with the repository's Doxyfile); and Cortex-M builds (`ru-cross-build`). Ten rules
  become active: KB-REPO-002, 003, 005, 016 and 018, KB-BLD-002, KB-CPP-012, KB-DOC-004 and 035, KB-TST-005.
  Must rules checked by a tool: 98 of 274.
- A parametric check can list `implemented_params`: only those parameters count as checked.

### Fixed

- The five conflicts found while loading the rules are settled, and the affected rules and pages agree. The
  switch-default "conflict" was not one: clang-tidy's check covers only non-enum switches.
