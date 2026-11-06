# ADR-0016: Virtual functions only at the three run-time boundaries

- Status: Accepted
- Date: 2026-11-06

## Context

The standard said two different things. The library page said `Base*` interfaces are "the one place above the
bind with virtual functions", while the HAL page defines `ManagerBase` with pure virtual functions and a virtual
`CollectDiagnostics(DiagnosticsSink&)`, and kb-core's `BaseThread` is a base class products derive from. A rule
that the code already breaks cannot be enforced, and a checker needs one list it can test against.

## Decision

Virtual functions are allowed in exactly three places, each a boundary where the concrete type is chosen when the
board or product is built, not when the library is written:

1. the `Base*` peripheral interfaces in kb-core's `interfaces/base/` (the MCU boundary);
2. kb-hal-common's `ManagerBase`, `FacadeBase` and the sink interfaces they take, such as `DiagnosticsSink` (the
   board boundary);
3. kb-core's `BaseThread` and `BaseThreadsManager` (the task boundary).

Everywhere else, including every driver, port, handler and utility, there are no virtual functions; ports use CRTP
(ADR-0003). A class at a boundary is abstract, is never deleted through a base pointer (there is no heap after
start-up, ADR-0004), and declares either a public virtual or a protected non-virtual destructor (C++ Core
Guidelines C.35). The repositories that own a boundary list its folders in `.kokeb/handbook.yml`, and the
`forbidden-patterns/virtual-outside-interfaces` check rejects `virtual` anywhere else.

## Consequences

- The library page's sentence is corrected to name all three boundaries; rule KB-ARCH-011 says the same.
- Adding a fourth boundary needs a new decision record, not a quiet exception.
