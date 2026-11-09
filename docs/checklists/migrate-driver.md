# Checklist: migrate an existing driver

Use this to move a driver from an older repository (for example a HardFOC `hf-<chip>-driver`) to a new
`driver-<chip>` built from the template. It adds the migration steps to the [new driver](new-driver.md) checklist,
which still applies in full. It was written during the first migrations (AS5047U over SPI, PCAL9555A over I2C,
then the AT25040B EEPROM) and is updated with each one.

**The principle:** the old repository is a source of *chip knowledge*: the register map, the protocol, the timing
and the procedures the datasheet asks for. Its API, error model and structure are not carried over; the new driver
is written on the template's architecture, and the old repository stays untouched until every driver has moved.

## Drivers that are already proven on hardware

Some old drivers run in shipped or bench-tested firmware that used them: its hardware records cover the MAX22200,
the TLE92466ED, the TMC9660, the ADS7952 and the PCAL9555A, partly the AT25040, and leave others (the AS5047U among
them) with none. That evidence belongs to **the old code at a given commit, on a given board, by a given
procedure**. A rewritten driver is new code: it inherits the knowledge, never the verification. So for a proven
driver the migration adds four things:

1. **Record the evidence as it is.** `docs/limitations.md` of the new repository lists, per chip, what was verified
   on hardware, with which old repository and commit, which board, which procedure and which evidence folder, and
   says plainly that it applies to the old driver until the new one is verified the same way.
2. **Keep every quirk the hardware taught.** Comments such as "workaround", "errata", "second write", the
   firmware's retries and its call sites are chip knowledge (step 2). Each one becomes a fault in the chip model and
   a test, or a documented reason it no longer applies. Example: acknowledged writes to the PCAL9555A were lost on
   hardware with the old driver, so the model can drop writes and the driver reads each write back (`WriteMismatch`).
3. **Fit the firmware's real use.** Before the API is final, list how the firmware's handler calls the old driver
   (which calls, how often, from which thread, what it does on error) and check the new API covers each one, or
   name the replacement. A call the firmware depends on and the new driver lacks blocks the merge
   (the PCAL9555A migration found four: output-latch read-back, a verified write, variant choice, retry guidance).
4. **Verify on the same bench before claiming it.** The status stays "not yet verified on hardware" until the new
   driver runs behind the same handler on the same board, through the same procedure, and its evidence folder is
   linked from `docs/limitations.md` with the driver's commit. Only then does the README's status say
   "verified on hardware: <board>, <date>".

Order the migrations so that a proven driver is moved when its firmware user can take the new version to the bench
soon after; a driver with no hardware user can move at any time.

```markdown
### 0. Before starting
- [ ] Hardware evidence found and recorded (section above): old commit, board, procedure, evidence folder; and the
      firmware's handler and call sites read
- [ ] Licence and authorship of the old code checked (`LICENSE`, `git log --format='%an <%ae>' | sort | uniq -c`).
      Relicensing (for example GPL-3.0 to MIT) needs every copyright holder's agreement; commits made with an
      employer address may belong to the employer. Record the decision in the tracking issue before the repository
      is made public
- [ ] The chip's real part number decided; it becomes the repository name, the namespace and every file name
      (an old repository name may be misspelt: `hf-pcal95555-driver` drives the PCAL9555A)
- [ ] Datasheet URL and revision noted; the PDF is never copied (ADR-0019)

### 1. Scaffold (no chip code yet)
- [ ] `gh repo create kokeb-labs/driver-<chip> --private --template kokeb-labs/driver-template`; public only after
      the licence decision and the first green CI
- [ ] `git switch -c feat/initial-driver`, then
      `python3 tools/setup.py --non-interactive --bus <bus> --description "..." --datasheet <url>`
- [ ] The scaffold's own host tests pass; commit that state alone (`git commit -s -m "Scaffold <CHIP> from driver-template"`)

### 2. Extract the chip knowledge from the old driver
- [ ] Register addresses, field positions and reset values (cross-checked against the datasheet, figure by figure)
- [ ] Frame or transaction format, CRC or PEC, read latency (for example "the reply answers the previous frame")
- [ ] Timing: power-up, reset, conversion, programming times
- [ ] Multi-step procedures (OTP or NVM burn, calibration) with their datasheet step numbers
- [ ] Error and status bits, and which of them mean "the value is not a measurement"
- [ ] The bus's burst semantics (auto-increment, or a pointer that toggles within a register pair) and the longest
      burst the driver needs (`kMaxBurst`)
- [ ] For a family with variants (PCA9555 and PCAL9555A): what the datasheets guarantee about a register a variant
      lacks. Configure the variant (`Config` field) unless detection is guaranteed, and never write a register before
      the variant is confirmed
- [ ] Old behaviour that is deliberately dropped is listed in the PR (for example `printf` dumps, retry
      parameters, sticky global flags, `std::function` callbacks)

### 3. Write the driver, in this order
- [ ] `inc/<chip>_registers.hpp`: addresses, masks and shifts as `constexpr`; no bit-field unions (their layout
      depends on the compiler)
- [ ] `inc/<chip>_types.hpp`: base `Error` set unchanged; chip-specific values from 16, each returned somewhere;
      unreturned base values listed on the API guide; `Config{}` equals the chip's reset state; `Validate()`
- [ ] `inc/<chip>_<bus>_interface.hpp`: the bus's standard hooks; remove hooks the chip has no use for. No reset
      pin: delete `CtrlPin`, `GpioSignal`, `GpioSet`, the `DeclaresGpioSet`/`HasGpioSet` concepts, `HardwareReset()`,
      `pulseResetPin()` and the `gpio_set_returns_void` compile-fail test
- [ ] `DelayUs` stays required only if some call waits (a reset, a conversion, a programming time); then the
      `port_without_delay` compile-fail test calls that operation. A chip with no timed procedure drops the hook,
      the `detail::DelayUs` helper and the test
- [ ] I2C: replace the scaffold's default address (`0x48`) with the chip's, and check the address range in
      `EnsureInitialized()` (`InvalidArgument`, no I/O)
- [ ] Lifecycle per [ADR-0021](../adr/0021-one-start-up-entry-point.md): `Config` is the constructor's last
      parameter, the start-up is a private `initialize()`, `EnsureInitialized()` is the only public start
- [ ] A chip with neither an ID register nor a reset (a GPIO expander): the identity check is "write every register,
      read every one back", and the missing reset and ID are listed as deviations on the Contract page
- [ ] `Validate()` returns `InvalidArgument`, or `Unsupported` for a setting the configured variant lacks
- [ ] `inc/<chip>.hpp` and `src/<chip>.ipp`: every fallible call returns `Result<T>`; every port failure
      propagates; destructive operations need an explicit confirmation argument
- [ ] A `Config` flag that leaves the chip's settings alone (an OTP- or NVM-programmed part) also reads them back
      into `GetConfig()`, so a later setter cannot write defaults over the programmed values
- [ ] Every register field the chip has is a `Config` field or deliberately kept as read (Dia bits, reserved);
      none is silently cleared by a write
- [ ] Multi-step procedures with a compare step use the protected frame format for every frame, reads included
- [ ] `tests/mock_<chip>.hpp`: a model at the protocol level (frames, latency, CRC, clear-on-read registers,
      timed procedures) with fault injection, not a register array. It has its own register map with datasheet
      page references and does not include `<chip>_registers.hpp`; `tests/test_model.cpp` static_asserts the two
      maps against each other (KB-TST-030)
- [ ] Every header has the KB-CPP-019 include guard (`python checks/source_checks.py guard --repo . <path>` from the
      handbook prints it); no `#pragma once` is left
- [ ] `inc/<chip>_<bus>_interface.hpp` declares the bus requirements as `constexpr` (KB-CPP-123), the Porting page
      lists them, and each example port static_asserts its settings against them
- [ ] A single-shot raw access and a `GetLast*()` accessor (KB-CPP-129); clear-on-read flags ORed into one latch
      with `GetLatched*()` / `ClearLatched*()` (KB-CPP-119)
- [ ] The hardware-proven rules on the driver contract: replies proven before they are decoded, line patterns
      refused, resync after a failed transfer, idempotent bounded retries, setters that change only what they name,
      start-up that waits for ready and clears inherited faults
      ([driver.md](../standards/driver.md#replies-retries-and-resynchronisation))

### 4. Tests
- [ ] Behaviour of every public call, including each error it documents
- [ ] The lifecycle: a second `EnsureInitialized()` does no I/O, a failed start is retried, reads before the start
      return `NotInitialized` and send nothing, `Deinitialize()` then `EnsureInitialized()` restarts, `ApplyConfig()`
      before the start stores without I/O
- [ ] `test_bus_faults.cpp`: every transfer of every operation failed in turn, each reported as `Bus`
- [ ] `test_errors.cpp`: each chip-specific error produced by a real call
- [ ] `test_kconfig.cpp` and `_config/Kconfig`: only options that map to `Config` fields
- [ ] Compile-fail tests for every compile-time contract that remains (missing hook, wrong signature)
- [ ] `tests/docs/*.cpp`: every snippet the pages show, rewritten for the new API
- [ ] `tests/fuzz/fuzz_<chip>.cpp`: the bus under the fuzzer's control (failed, corrupted, replaced and, where the
      bus allows it, lost transfers), the driver's promises checked after every call, the corpus replayed as a CTest;
      every crash it finds is fixed with a unit test and kept as a `regress-*` input
- [ ] Every quirk found on hardware is a fault in the model and a test (section above)

### 5. Local gates (the same tools and versions as CI)
- [ ] A few GB free on the disk: the coverage, clang-tidy and docs builds each create their own build directory
- [ ] `ctest` passes with GCC and Clang
- [ ] clang-format 20.1.8 clean over `.hpp`, `.cpp` and `.ipp`. It reflows tables inside comment blocks into one
      paragraph: wrap a Doxygen comment that holds a table in `// clang-format off` / `// clang-format on`
- [ ] clang-tidy 20.1.0 clean with the compile database. CI runs it on Linux (libstdc++), which reports checks a
      macOS run (libc++) misses, such as `modernize-use-std-numbers` and `modernize-use-integer-sign-comparison`:
      treat CI's lint as the authority (`-DCMAKE_EXPORT_COMPILE_COMMANDS=ON -D<CHIP>_BUILD_TESTS=ON`);
      intentional findings in tests (out-of-range enum casts that test `Validate()`) carry a `NOLINT` with the check name
- [ ] lizard 1.24.1 with the files listed explicitly (`inc/*.hpp src/*.ipp`): within the level's limits
- [ ] gcovr 8.7 on GCC `-O0 --coverage -fcondition-coverage` over every CTest binary, with `--merge-lines` as CI
      uses (ci-tools 1.5.2): at or above the level's floors. Without it each template instance counts separately
- [ ] `ru-handbook-check` locally: `python3 tools/handbook_check/handbook_check.py --repo .` from ci-tools, 0 errors
- [ ] The handbook's source checks: `python3 checks/source_checks.py scan --repo <driver>` from the handbook, 0
      findings (include guards, bus requirements, raw access)

### 6. Documentation
- [ ] Every page rewritten for the chip; nothing about the template's example chip remains, in `.claude/skills/`
      too (including `new-driver-from-template`)
- [ ] Facts from the datasheet text, not from memory: a fetched PDF comes back as raw data, so extract it locally
      (`pdftotext -layout`) and cite sections and figures
- [ ] Chip-specific pages added where the chip needs them (an OTP or calibration procedure)
- [ ] `kokeb-docs figures && kokeb-docs gen && kokeb-docs check`, `mkdocs build --strict`, markdownlint
- [ ] Hardware-dependent statements marked **not verified on hardware**, with bench steps

### 7. Pull request and release
- [ ] PR from `feat/initial-driver` lists: what was carried over, what was dropped and why, the gate figures
      (coverage, complexity) and the hardware steps still to run
- [ ] `CI gate / gate` green
- [ ] Owner applies [repository setup](https://github.com/kokeb-labs/driver-template/blob/main/docs/repo-setup.md)
      and decides visibility; `v0.1.0` released through the gated flow
- [ ] The old repository is not archived or deleted until every driver has moved and kb-core is in place; its
      README may point to the new repository
```

## What the pilots found

| Finding | Where it was fixed |
| --- | --- |
| lizard skips `.ipp` files in a directory, so the complexity gate never measured a header-only implementation | ci-tools 1.5.1 lists the files itself |
| The lint default extensions left `.ipp` out of clang-format | ci-tools 1.5.1 default, template lint caller |
| Coverage counted each template instance separately: a happy-path example made failure paths look untested (73.8 % instead of 94.5 % of branches) | ci-tools 1.5.2 (`--merge-lines`) |
| clang-tidy on Linux reports checks a macOS run misses | Step 5: CI's lint is the authority |
| Two public start-up calls (`Initialize`, `EnsureInitialized`) | ADR-0021: one entry point |
| A GPIO expander has no ID register and no reset | Step 3: write-and-read-back identity, deviations recorded |
| An old repository name was misspelt (`pcal95555`) | Step 0: decide the real part number first |
| Old drivers are GPL-3.0, some commits under an employer address | Step 0: licence decision before going public |
| clang-format merged the rows of the hook tables in the Doxygen comments (the template has the same) | Step 5 note; template fix |
| A burned part's settings were overwritten by the first setter after `write_settings = false` | Step 3: read the settings back |
| The OTP compare reads ran without CRC in 16-bit mode | Step 3: protected frames for the whole procedure |
| The fuzzer found that a lost data frame of a two-frame write turned the next command into data: losing "PROG = PROGOTP" let the next read burn the AS5047U's OTP | Driver: a NOP read after any failed transfer; step 4: fuzz every driver |
| `SetZeroHere()` left the zero at 0 when its angle read failed (fuzzer) | Driver: restore the old zero; a failed call has no side effect |
| The firmware checks the PCAL9555A's output latch after every write because the bench lost acknowledged writes | Driver: read-back calls and `verify_writes`; section above |
| The port's `Log()` hook was a C variadic function, and the examples passed driver text as a format string | Plain-text hook; clang-tidy `cert-*` |
| A dead bus passed the old EEPROM probe: a MISO floating low reads 0x00, the same as an idle AT25040B, twice | Driver: an active identity check (toggle the write enable latch, which a stuck line cannot follow); step 3: prefer a check the chip must answer over one a line can fake |
| One status byte lost to noise read "idle" during a write cycle, so a read went ahead and returned the busy chip's 0xFF as data (fuzzer) | Driver: an idle status counts only when a second read confirms it |
| The old handler released WP for every probe and read and parked it only after a successful write | Driver: WP raised only for a write, parked after on success and failure; the fuzzer checks "WP parked after every call" |
| The scaffold wrote "EEPROMs It follows" when the description had no full stop | driver-template: the description gets a full stop in `AGENTS.md` |
| README docs and API links pointed at GitHub Pages, which a private repository on the free plan does not serve | README links to `docs/`; the site link waits for the repository to be public |
