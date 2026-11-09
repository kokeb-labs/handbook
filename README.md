# Kokeb Labs handbook

How every Kokeb Labs repository is designed, written, tested, documented and released: C and C++20 code, CMake,
tests, documentation, Git and releases, CI and coding agents. Every rule has an ID, a level and the check that
verifies it, so what the handbook says is what CI enforces.

- Read it: <https://kokeb-labs.github.io/handbook/>
- Rules as data: [`rules/`](rules/), one file per area; the pages under `docs/rules/` are generated from them
- Checks: [`checks/registry.yml`](checks/registry.yml) lists every check a rule may name, implemented or planned;
  [`checks/source_checks.py`](checks/source_checks.py) runs the source checks (include guards, bus requirements,
  raw access) on a repository: `python3 checks/source_checks.py scan --repo <path>`
- Tool configuration: [`config/`](config/), the `.clang-format` and `.clang-tidy` every repository uses, and
  `.clang-tidy-safety`, the safety-level profile generated from the MISRA C++:2023 matrix
- HardFOC supplement: [`hf-supplement/`](hf-supplement/), the HF-* rules for HardFOC products only; they move
  to `hardfoc/hf-development-handbook` once its own CI validates them
- Open configuration work: [`checks/backlog.yml`](checks/backlog.yml)

## Change a rule

1. Edit `rules/<area>.yml` (the fields are explained on the *How rules work* page).
2. Run `python checks/handbook.py gen` to regenerate the pages, and `python checks/handbook.py check` to validate.
3. Open a pull request. A new `must` rule starts as `proposed` with an `enforce_from` date; removing or loosening a
   rule needs a decision record in `docs/adr/`.

Preview the site with `pip install "git+https://github.com/kokeb-labs/ci-tools@v1#subdirectory=packages/kokeb-mkdocs-theme"`
and `mkdocs serve`.

## Licence

MIT, see [LICENSE](LICENSE).
