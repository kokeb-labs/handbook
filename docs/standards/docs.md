# Documentation

What every repository documents and where. The detailed writing rules, page templates and checks are in the
documentation style guide of `ci-tools`; this page sets what is required.

## The site

- Every public code repository publishes a MkDocs site at `https://kokeb-labs.github.io/<repo>/`, built with the
  shared theme package `kokeb-mkdocs-theme` and the `kokeb-docs` command-line tool (both in `ci-tools`), versioned
  per tag, with the Doxygen API reference under `api/`.
- Pages live in `docs/`, navigation in `docs/.nav.yml` (five tabs: Home, Get started, Concepts, Guides,
  Reference). The site configuration is `_config/mkdocs.yml` with `docs_dir: ../docs`
  ([ADR-0011](../adr/0011-repository-root-layout.md)); build with `mkdocs build -f _config/mkdocs.yml --strict`, and pass
  `mkdocs_config: _config/mkdocs.yml` and `doxygen_config: _config/Doxyfile` to the docs workflow.
- `kokeb-docs check` runs the same checks locally as the docs workflow.
- The build is strict: broken links, pages missing from the nav, figures or generated regions that no longer match
  the code, and snippets that do not compile all fail CI.

## Page sets

| Kind | Required pages |
| --- | --- |
| Driver | Home, Quickstart (starting with the host example), Installation (CMake first, then ESP-IDF), Platforms, Hardware, Architecture, **Contract**, API guide, API reference, Examples, Porting (with Editor setup), Configuration (if it has a `Config` or Kconfig), Testing and CI, Troubleshooting, Changelog, Figures |
| Standalone library | Home, Quickstart (starting with the host example), Concepts, **Contract**, API guide (one page per utility for a collection), API reference, Integration, Platforms, Testing and CI, Changelog |
| kb-core | Home, Quickstart, Architecture (the four parts and their direction), **Contract**, one section per part (utils, rtos, interfaces, handlers), Handler model, one page per handler, Build options and MCU gate, Release trains and compatibility, Threading, Host build, API reference, Testing, Changelog |
| `kb-hal-common` and board HALs | Home with the board card, Quickstart, Hardware (block diagram, pin table, connectors, power), Architecture (managers, start-up order), **Contract**, one guide page per board function, API reference, Examples, Bring-up and troubleshooting, Changelog |
| Product | Home, Getting started, Architecture (tasks, data flow), Operation (modes, commands, configuration, the fault catalogue), Hardware (links the HAL site), Development, Troubleshooting, Changelog, ADRs |
| CI and tools | Home, Quickstart, one page per workflow or script, Versioning, Migration guides, Changelog |

What each page contains is in the style guide's standard page sets.

## The Contract page

Every driver, library, kb-core, HAL and product has `docs/contract.md`, under **Concepts** right after
Architecture. It is the short, normative summary of what the repository promises, in this order:

```markdown
# Contract

What <repo> promises, what it needs, and the rules a caller follows.

## Promises

- One bullet per guarantee a caller can rely on.

## Depends on

| Dependency | Version | Why |
| --- | --- | --- |

## Threading

Which objects are thread-safe, which locks they take, what may run in an ISR.

## Errors

The error type, every value a caller can see, and what it means. For a handler or HAL, the `kb::Status` mapping.

## Memory

Allocation (none after start-up), static buffers and their sizes, stack needs of callbacks.

## Platform

What is platform-free and what is not. MCU-bound drivers say so here and name the families and the peripheral.

## Deviations from the standard

Each rule of the Kokeb Labs standard this repository does not meet yet, with its issue.
```

The Contract page links the standard for the rules it inherits rather than restating them, and states only what
is specific to the repository.

## Doxygen

The API reference is generated from the public headers with the shared settings in `ci-tools`. Each repository
keeps its Doxyfile in `_config/Doxyfile` and runs Doxygen from the root (`doxygen _config/Doxyfile`), so the paths
inside are relative to the root:

| Setting | Value | Why |
| --- | --- | --- |
| `INPUT` | `inc/` (drivers), the public header folders (libraries, kb-core, HALs) | Only the public API |
| `EXTRACT_ALL` | `NO` | Undocumented symbols show up as warnings instead of empty entries |
| `EXTRACT_PRIVATE` | `NO` | Private members are not API |
| `WARN_IF_UNDOCUMENTED` | `YES` | |
| `WARN_NO_PARAMDOC` | `YES` | Every parameter is documented, with its unit |
| `WARN_AS_ERROR` | `FAIL_ON_WARNINGS` | CI fails on any warning in the public headers |
| `USE_MDFILE_AS_MAINPAGE` | `docs/_doxygen/mainpage.md` | |
| `GENERATE_HTML` | `YES`, merged into the site under `api/` | |

Each public symbol has a brief description; each function documents its parameters with units, its return value
and the error values it can return, and whether it does I/O or blocks.

## README

The README is the front door: someone who reads only it knows what the part is, whether the driver fits their
project, where the datasheet is, and how to get to a first reading. The reference stays on the site. Sections, in
this order, only those that apply:

1. `# Name` and a one-sentence hero line: what it is and does.
2. Badges that are true: the main test workflow, license, C++ standard, latest release (once one exists).
3. **The documentation link** in bold.
4. One short paragraph in plain words: what the part does and what the driver gives you.
5. One layer or block figure.
6. **At a glance**: a two-column table: the part (vendor, package, supply), what it measures or does, the bus, what
   else it drives, the driver's properties, where it runs, and its **status** (version, and "not yet verified on
   hardware" until it is).
7. **Datasheet** (drivers): the generated card (`<!-- generated: datasheet-card -->`): document, revision, where to
   get it, and the link to the Datasheet map.
8. **Try it on your PC**: the host example in one command.
9. **Use it on your MCU**: 1. a minimal wiring table, 2. one line on the port with a link to Porting, 3. the generated
   quickstart region (`<!-- generated: quickstart-code -->`), which checks every return value, and one line on how
   the driver starts (`EnsureInitialized()`).
10. **What it does**: five to seven bullets.
11. **Install**: the submodule line and the CMake lines.
12. **Documentation**: a table of the pages with a "Read it when you want to" column. Links go to the pages in the
    repository (`docs/<page>.md`) while the site is not published, to `/latest/` once it is.
13. **Tests and quality**: one command line, and one sentence on what CI checks.
14. **License**: one line (MIT, or CERN-OHL-P-2.0 for a hardware design).

### The datasheet trail

A driver lists the vendor documents it was written against in `docs/datasheets.yml`
([ADR-0019](../adr/0019-datasheets.md)), and, for each thing it takes from them, a **topic**: the datasheet's own
section name and printed page, the driver API that implements it, and the docs pages that explain it. The
`datasheet` generator (shipped in the template, `tools/docs/generators/datasheet.py`) builds three regions from it,
so a revision or a page number is written once:

- `datasheet-card` on the README, the home page and Hardware: document, revision, date, where to get it;
- `datasheet-map` on `docs/datasheet.md`: every topic with section, page, driver API and docs page;
- `datasheet-refs` at the top of each page a topic names: a collapsed box listing the sections that page relies on.

Page numbers link into the PDF (`#page=N`) when the vendor publishes a stable PDF URL (`pdf`, with `page_offset` when
the printed and PDF page numbers differ). The repository never contains the PDF.

A driver's README names the chip and the part, not the org: the driver is usable on its own
([ADR-0012](../adr/0012-unbranded-drivers.md)).

No table of contents, no emoji walls, no check-mark feature lists, no badges that link nowhere, no duplicated API
tables.

## Code on the site

- Every C++ block on the site compiles: it lives in `tests/docs/` and is pulled into the page as a generated
  region, so a change that breaks an example fails CI.
- Examples check every `Result` and `Status`. An example that ignores a return value teaches the wrong thing.
- Figures are generated (`kokeb-docs figures`) with light and dark variants and alt text.

## Changelog and decisions

- `docs/changelog.md` includes `CHANGELOG.md` ([release.md](release.md#changelog)).
- Decisions that affect more than one repository are ADRs here, in [`adr/`](../adr/index.md). Decisions local to
  one repository are ADRs in its own `docs/adr/`, in the same format.
