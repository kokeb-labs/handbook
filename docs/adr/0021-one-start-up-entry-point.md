# ADR-0021: EnsureInitialized() is the one start-up entry point

- Status: Accepted
- Date: 2026-11-07
- Amends: [ADR-0002](0002-lifecycle.md) (the driver and handler parts)

## Context

ADR-0002 gave drivers two public ways to start: `Initialize(config)` and `EnsureInitialized()`. Moving the first
drivers showed what that costs:

- `Initialize()` can be called again on a running chip. It then resets and reconfigures it, for no reason and in
  the middle of operation, and nothing in the API discourages it.
- Two entry points with different behaviour on the second call are two contracts to test, document and review in
  every driver and every handler.
- Handlers will be singletons that own hardware and are used from several tasks. They need exactly one idempotent
  start, with no way to start twice.

The handler standard also allowed a handler method to start the chip itself on first use. That hides start-up
traffic (for the AS5047U, 42 SPI frames including writes) inside whatever call comes first, possibly a read in a
control loop, and turns a start-up failure into the error of a read.

## Decision

### Drivers

- The constructor takes the port, any bus argument, and the configuration last with a default:
  `explicit Chip(Port& port, ..., const Config& config = {}) noexcept`. It stores them, does no I/O and cannot fail.
- `EnsureInitialized()` is the only public way to start. Its first call validates the stored configuration
  (`InvalidArgument`, no I/O), brings the port up, resets and identifies the chip and applies the configuration, and
  only then marks the driver initialised. Once it has succeeded, later calls return `Ok` at once with no I/O. After
  a failure the driver stays uninitialised and the next call starts again from the beginning.
- The start-up sequence itself is a private member (`initialize()`). There is no public `Initialize()`.
- `Deinitialize()` puts the chip in its safe state and marks the driver uninitialised. Recovery after a fault is
  `Deinitialize()` then `EnsureInitialized()`.
- `ApplyConfig(config)` validates first. On a running driver it writes the configuration; before the start it only
  stores it for the first `EnsureInitialized()`, with no I/O.
- **No read or write starts the chip.** Before `EnsureInitialized()` has succeeded, every call that needs the chip
  returns `NotInitialized` and sends nothing. A read is always the bus traffic it needs and nothing more.

### Handlers

- `EnsureInitialized()` is the handler's one start-up entry point too: it builds the driver in place and calls the
  driver's `EnsureInitialized()`, and on failure destroys it again so the next call retries.
- Handler reads and writes do not call `EnsureInitialized()`. They return `NotInitialized` until the handler has
  been started. The HAL starts its handlers once, in its fixed start-up order (ADR-0002), and a task that uses a
  handler before then gets `NotInitialized`, not a hidden start.

## Consequences

- One lifecycle contract per layer: construct, `EnsureInitialized()`, use, optionally `Deinitialize()`.
- Calling `EnsureInitialized()` before every use is cheap and safe, so code that is unsure whether the chip has
  started can call it; but the start-up cost is always paid at a call that says it starts something.
- Timing of a read is deterministic: it never includes a reset or a configuration write.
- Breaking for code written against ADR-0002: `driver.Initialize(config)` becomes `Chip driver(port, config);` then
  `driver.EnsureInitialized()`, and a restart with a new configuration becomes `Deinitialize()`, `ApplyConfig()`,
  `EnsureInitialized()`. The template and the first two migrated drivers (AS5047U, PCAL9555A) change with this ADR;
  the HardFOC drivers are migrated onto it.

## Alternatives considered

- **Every read starts the chip on first use.** Rejected: start-up traffic and start-up errors inside a read, and a
  failing chip retried at every read.
- **Keep a public `Initialize()` for re-configuration.** Rejected: `ApplyConfig()` already changes a running
  configuration, and a full restart is `Deinitialize()` then `EnsureInitialized()`, so a second entry point adds
  nothing but a way to restart by accident.
