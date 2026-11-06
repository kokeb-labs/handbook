# ADR-0018: Commit sdkconfig.defaults, never the generated sdkconfig

- Status: Accepted
- Date: 2026-11-06

## Context

The driver and product pages say a full `sdkconfig` is not committed, but the threading page still describes
projects that commit one, and the release page attaches `sdkconfig` to product releases. A committed `sdkconfig`
silently overrides the defaults files, so the 1 kHz tick (ADR-0006) and any other required setting can be lost in
a repository that commits one.

## Decision

- An ESP-IDF project commits `sdkconfig.defaults` (and `sdkconfig.defaults.<target>` where a target needs its own
  settings). Every setting the project depends on is in those files.
- The generated `sdkconfig` is in `.gitignore` and never committed. `tracked-files/sdkconfig` fails CI if one is
  tracked.
- A firmware release attaches the **effective** `sdkconfig` the build produced, so the exact configuration of the
  released binary is recorded without being a source of truth in the repository.

## Consequences

- The threading page's note about committed `sdkconfig` files becomes a migration step: delete it, and move any
  setting it held into `sdkconfig.defaults`.
- A reproducible build depends only on the defaults files and the pinned ESP-IDF version.
