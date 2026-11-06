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
- A first set of 33 rules across C++, build, testing, documentation, repository, Git, CI and agents.
