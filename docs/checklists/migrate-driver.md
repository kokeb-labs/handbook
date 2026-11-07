# Checklist: migrate an existing driver

Use this to move a driver from an older repository (for example a HardFOC `hf-<chip>-driver`) to a new
`driver-<chip>` built from the template. It adds the migration steps to the [new driver](new-driver.md) checklist,
which still applies in full. It was written during the first migrations (AS5047U over SPI, PCAL9555A over I2C) and is
updated with each one.

**The principle:** the old repository is a source of *chip knowledge*: the register map, the protocol, the timing
and the procedures the datasheet asks for. Its API, error model and structure are not carried over; the new driver
is written on the template's architecture, and the old repository stays untouched until every driver has moved.

```markdown
### 0. Before starting
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
      timed procedures) with fault injection, not a register array

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
