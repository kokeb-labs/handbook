# Changelog

All notable changes to the handbook are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): a new or tightened rule is a minor release, a removed or
loosened rule is a major release.

## [Unreleased]

### Added

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

### Fixed

- The five conflicts found while loading the rules are settled, and the affected rules and pages agree. The
  switch-default "conflict" was not one: clang-tidy's check covers only non-enum switches.
