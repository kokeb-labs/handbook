# ADR-0017: Target code uses a named subset of the standard library

- Status: Accepted
- Date: 2026-11-06

## Context

The layers page and ADR-0010 call the headers a driver may include "the freestanding subset". They are not: in
C++20, `<array>`, `<span>`, `<optional>`, `<cstring>`, `<cmath>` and `<algorithm>` are hosted headers, available
on every embedded toolchain we use but not freestanding by the standard's definition. A rule named after a
standard term it contradicts invites argument about which list applies, and no tool can check "freestanding-friendly".

## Decision

- The term is **the target library subset**: the standard headers code that runs on a microcontroller may use. It
  is an allow-list, not a description.
- **Drivers** may include exactly the headers in the Driver row of the include table on the Layers page
  (`<cstdint>`, `<cstddef>`, `<array>`, `<algorithm>`, `<type_traits>`, `<concepts>`, `<limits>`, `<cmath>`,
  `<cstring>`, `<span>`, `<utility>`, `<optional>`, `<bit>`), plus `<cstdarg>` for the optional `Log` hook.
- **Other target code** (kb-core, HALs, firmware) may also include `<atomic>`, `<chrono>` (types and arithmetic;
  clocks come from `kb::rtos`), `<string_view>`, `<variant>`, `<tuple>`, `<iterator>`, `<numeric>`, `<new>`
  (placement new only) and `<cstdio>` for `snprintf` into a caller's buffer.
- **No target code** includes a header that allocates, throws or needs an operating system: `<string>`,
  `<vector>`, `<map>`, `<set>`, the `<unordered_*>` and `<list>`/`<deque>` containers, `<memory>`, `<functional>`,
  `<iostream>` and the other stream headers, `<thread>`, `<mutex>`, `<condition_variable>`, `<future>`, `<regex>`,
  `<filesystem>`, `<locale>`, `<exception>`, `<stdexcept>`, `<typeinfo>`, `<any>`.
- Algorithms that may allocate (`std::stable_sort`, `std::stable_partition`, `std::inplace_merge`) are not used.
- Host-only tests and tools are exempt.

The `include-allowlist/driver` and `include-allowlist/target` checks test each translation unit against these
lists.

## Consequences

- The layers page and ADR-0010 say "target library subset" instead of "freestanding".
- Adding a header to the subset is a change to this record and to the include table.
