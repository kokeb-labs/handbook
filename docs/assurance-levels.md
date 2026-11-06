# Assurance levels

Not every repository needs the same rigour. A script that renders a diagram and a motor-current driver inside a
medical pump are both Kokeb code, but only one of them can hurt someone. Each repository declares one of three
levels, and each level includes everything below it. All levels keep the same rules; higher levels switch on
more of them and ask for more evidence.

| Level | For | Adds |
| --- | --- | --- |
| **standard** | Every repository: tools, examples, documentation | Format, lint, static analysis, host tests, strict docs build, DCO, the CI gate |
| **high** | Code others build products on: drivers, kb-core, board HALs | Sanitizers; a coverage floor (85% lines, 75% branches); builds for every supported target; warning-free Doxygen on the public API; a deviation record for every suppressed finding; register layouts asserted |
| **safety** | Components meant to be qualified inside a safety-classified product, such as the software of an IEC 62304 class C medical device | Requirements traced to code and tests; every reachable branch covered, each gap justified; the [coding-standard compliance matrix](coding-standards.md) with a commercial MISRA checker run; an anomaly list; a signed [evidence package](evidence.md) per release |

## Choosing a level

- A repository starts at **standard** and moves up when something depends on it.
- Drivers and kb-core are **high** from their first release.
- **safety** is chosen per component when a product team intends to qualify it, and needs the maintainer's
  approval in a decision record, because it commits the project to keeping the evidence current for every
  release.

## What a level is not

A level is not a certification. A Kokeb component at **safety** level is not "IEC 62304 compliant": compliance is
a property of a manufacturer's process and product, not of a library. What the level guarantees is that the
evidence a manufacturer's process asks for exists, is complete, and was produced by the checks named here. See
[IEC 62304](iec-62304.md) for how that maps onto the standard.
