# The Kokeb Labs handbook

How every Kokeb Labs repository is designed, written, tested, documented and released, for people and for coding
agents alike.

Every rule here has an ID, a level and a stated way of being verified. Most are checked by CI on every pull
request; the rest are checked in review against the pull-request checklist, or are guidance, and say so. A rule
nobody can verify is not written as a rule.

## Where to start

| You want to | Read |
| --- | --- |
| Understand how rules, IDs, levels and checks work | [How rules work](how-rules-work.md) |
| Know what your repository has to meet | [Assurance levels](assurance-levels.md), then the [rules](rules/cpp.md) for your kind |
| Set a rule aside for a good reason | [Deviations and waivers](deviations.md) |
| See how much is verified by CI today | [Coverage](rules/coverage.md) |
| Use a Kokeb component in a regulated product | [Evidence for regulated products](evidence.md) and [IEC 62304](iec-62304.md) |
| Know which coding standards we follow | [Coding standards](coding-standards.md) |
| Read why a decision was made | [Decision records](adr/index.md) |
| Read the design of each layer | [Standards](standards/index.md) |

## What it covers

C and C++20 code, CMake, tests, Markdown and Doxygen documentation, repository layout, Git and releases, CI and
supply chain, and coding agents, for drivers, libraries, board HALs, firmware, tooling and documentation
repositories.

## Who it is for

Contributors and maintainers of Kokeb Labs repositories, coding agents working in them (each repository's
`AGENTS.md` carries the rules for its kind), and teams that build products on Kokeb components and need to know
what was verified and how.

Product families under the Kokeb Labs umbrella extend this handbook with their own supplement, in the same format
and checked by the same tools; HardFOC's is `hardfoc/hf-development-handbook`. A supplement adds rules; it never
relaxes one of these.
