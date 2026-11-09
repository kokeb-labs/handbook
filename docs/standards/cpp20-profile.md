# C++20 profile

Kokeb Labs code is ISO C++20 (ADR-0010), and MISRA C++:2023, our reference coding standard, is written for C++17.
This profile closes the gap. It sorts every C++17 and C++20 feature we have a view on into **Use**, **Use with
rules** and **Forbid**, and states the rules as numbered guidelines, KB-CPP20-001 to KB-CPP20-058 (the
[C++20 profile rules](../rules/cpp20.md)), each with its category, scope, the MISRA C++:2023 guidelines it extends
or relates to (by number only) and the tool or review step that enforces it.

The profile is also what deviation MD-CPP-001 covers
([`compliance/misra-cpp-2023-deviations.yml`](https://github.com/kokeb-labs/handbook/blob/main/compliance/misra-cpp-2023-deviations.yml)):
the features marked *Use* and *Use with rules*, each under its guidelines, and nothing else. A feature marked
*Forbid*, anything C++20 deprecates, and every feature of C++23 or later is a violation of Rule 4.1.1 with no
deviation, even in a build whose dialect accepts it (ESP-IDF compiles as `gnu++23` or `gnu++26` by default). A
feature moves into the covered set only by a change to this page, `rules/cpp20.yml` and MD-CPP-001 in one pull
request.

## How to read a guideline

- **Category** follows MISRA's model. *Mandatory*: breaking it is undefined behaviour or an unrecoverable defect,
  and it is never deviated. *Required*: followed unless a deviation record exists. *Advisory*: followed unless a
  reviewer accepts a stated reason. Mandatory and required guidelines are `must` rules, advisory ones `should`
  rules. A guideline is never classified below the MISRA guideline it extends. The set has **4 mandatory, 36
  required and 18 advisory** guidelines.
- **Scope**: D drivers and the driver template, L libraries, H HALs, BSP binds and firmware. Test code in every
  repository follows the language-level guidelines (KB-CPP20-001 to 004), not the library-subset ones.
- **MISRA C++:2023** lists the guidelines a rule extends or relates to. The standard's text is not reproduced
  here; the compliance matrix holds our own one-line summary of each.
- **Enforced by** names the compiler flag, clang-tidy check, handbook source check (`cpp20-profile/...`,
  `checks/source_checks.py`), the strict-dialect build, a query of the planned Kokeb CodeQL pack, or the review
  step. Each rule's page entry lists the exact checks.

## Use { #use }

Recommended without rules beyond the rest of the handbook.

| Feature | Why |
| --- | --- |
| `enum class` with a fixed-width underlying type | Scoped, no implicit conversion, fixed size (Rules 10.2.1, 10.2.2). Integer-to-enum conversion follows KB-CPP20-025. |
| `[[nodiscard]]` | Makes the use of every result compiler-checked (Rule 0.1.2); on every error type (KB-CPP20-037). |
| `constexpr` functions and `inline constexpr` variables | No run-time cost, undefined behaviour is a compile error in constant evaluation, provable with `static_assert` (KB-CPP20-012, -017). |
| `static_assert` | Compile-time evidence of datasheet facts (KB-CPP-009, KB-CPP20-012). |
| `std::array` | Bounded, does not decay (Rules 11.3.1, 7.11.2). |
| `if` and `switch` with an initialiser | Narrows the scope of `Result` temporaries (Rule 6.4.1). |
| Nested namespace definitions | Syntax only. |
| Standard concepts (`same_as`, `derived_from`, `unsigned_integral`, `invocable`) | Prefer the standard's concepts to home-made ones. |
| `std::span` with a fixed extent | The size is in the type and checked at compile time (KB-CPP20-042). |
| `<numbers>` | Constants only (KB-CPP20-054), where the layer's ADR-0017 subset lists it. |
| `[[maybe_unused]]` | Replaces `(void)x;` in hook dispatch (Rule 0.2.2, KB-CPP20-038). |
| `std::in_range`, `std::cmp_less` and siblings | Correct mixed-sign comparison and range-checked narrowing (Rules 7.0.5, 7.0.6; KB-CPP20-022, -023). |
| `<bit>` counting and rotation | Unsigned operands by construction, `constexpr` (Rule 7.0.4, KB-CPP20-028). |
| Defaulted and deleted special members, `explicit operator bool` | Rules 15.0.1, 15.1.3, 7.0.2. |
| Default member initialisers on aggregates | Every member has a defined value (Rules 11.6.1, 15.1.4). |
| Range-based `for` over arrays and spans | Over a named object (Rule 9.5.2). |
| Digit separators | Readable masks and constants. |

## Use with rules { #use-with-rules }

Allowed under the named guidelines.

| Feature | Rules | Guidelines |
| --- | --- | --- |
| Concepts and requires-clauses for port contracts | Exact signatures and `noexcept` | KB-CPP20-005, -006 |
| Requires-expressions for optional hooks | Named detection concepts only | KB-CPP20-007 |
| `if constexpr` | Compile-time conditions only, each branch instantiated by a test | KB-CPP20-015 |
| `std::span` with a dynamic extent | Checked before indexing; never outlives its target | KB-CPP20-043, -044 |
| Designated initialisers | Every member defaulted; used at call sites | KB-CPP20-031 |
| Defaulted `operator==` | Only on exactly comparable members (MD-CPP-002) | KB-CPP20-033 |
| Lambdas | Explicit captures, never stored | KB-CPP20-045 |
| CRTP and class templates on the port | Port-independent code outside the template | KB-CPP20-009 |
| Member function templates, abbreviated function templates | Constrained; no `auto` parameters in public API | KB-CPP20-005, -010 |
| `consteval` | Build-time construction, such as checked configurations | KB-CPP20-013 |
| `constinit` | HAL and firmware statics; drivers have none | KB-CPP20-014 |
| `std::bit_cast` | Equal-size value types only, never pointers or byte order | KB-CPP20-029 |
| `std::endian` | Only in `static_assert` or MCU port code | KB-CPP20-029 |
| `using enum` | Block scope only | KB-CPP20-027 |
| `std::optional` | Read only when engaged; never `.value()` | KB-CPP20-048 |
| Structured bindings | The error is tested before the value | KB-CPP20-035 |
| Class types as non-type template parameters | Structural, integral members only | KB-CPP20-036 |
| `std::ranges` algorithms in `<algorithm>` | Non-allocating, named ranges, side-effect-free predicates | KB-CPP20-050 |
| Non-allocating `<algorithm>` | As above; ADR-0017 bans the `stable_` algorithms | KB-CPP20-050 |
| `__has_include` | Kconfig leaf headers only; one configuration per program | KB-CPP20-018 |
| Pointer to data member | Private helpers only, never across the API | review |
| `std::source_location` | The libraries' logging facade only | KB-CPP20-052 |
| `std::atomic_ref` | HAL only, with a lock-free assertion | KB-CPP20-055 |
| Strong unit types (a library technique) | Public APIs with easily swapped parameters | KB-CPP20-030 |

## Forbid { #forbid }

Not used in the stated scope (drivers unless stated otherwise).

| Feature | Why | Guideline |
| --- | --- | --- |
| Coroutines | Heap-allocated frames unless optimised away, a generated state machine that is hard to bound, no checker coverage | KB-CPP20-056 |
| Modules | Not supported by ESP-IDF's build, partial in GCC, needs a scanning generator; tools lag | KB-CPP20-057 |
| Range views and `<ranges>` (target code) | Lazy views hold references, heavy instantiations, slow unoptimised builds | KB-CPP20-050 |
| `std::format`, `format_to`, `std::print` | Heap strings, exceptions, locale; drivers never format text | KB-CPP20-051 |
| Three-way comparison `<=>` (drivers) | Configurations and errors have no order; `<compare>` is outside the subset | KB-CPP20-034 |
| `char8_t` and `u8` literals (target code) | Drivers move bytes; C++20 changed the literal type | KB-CPP20-053 |
| Any C++23 or later feature | Outside MD-CPP-001, even where a dialect accepts it; our own `detail::ToUnderlying` replaces `std::to_underlying` | KB-CPP20-001, -002 |
| `[[likely]]` and `[[unlikely]]` without a measurement | Rarely measurable here, easy to misplace | KB-CPP20-040 |
| `[[no_unique_address]]` (drivers, layout types) | Changes layout per compiler | KB-CPP20-041 |
| `[[fallthrough]]` | Every switch clause ends in `break` or `return` | KB-CPP20-039 |
| Parenthesised aggregate initialisation | Positional, and allows narrowing | KB-CPP20-032 |
| Lambdas in unevaluated operands, namespace-scope lambdas in headers | A distinct closure type per translation unit is an ODR trap | KB-CPP20-046 |
| `std::variant`, `std::any`, `std::function`, `std::expected` (drivers) | Throwing access, heap, RTTI, C++23 | KB-CPP20-049 |
| `constexpr` allocation, `constexpr virtual` | Needs allocating headers; drivers have no virtual functions | KB-CPP20-019 |
| `std::is_constant_evaluated` | Always true inside `if constexpr`; the clean form is C++23 | KB-CPP20-016 |
| Constructs C++20 deprecates | Candidates for removal, and misleading | KB-CPP20-003 |
| Feature-test macros and `<version>` to choose behaviour | One language level; the other branch goes untested | KB-CPP20-004 |
| Generic lambdas (drivers) | Unconstrained templates; use a named, constrained function template | KB-CPP20-047 |

That is 17 features to use, 24 to use with rules and 18 to avoid.

## The guidelines { #guidelines }

The rule text, the reason and the exact checks of each guideline are on the
[C++20 profile rules](../rules/cpp20.md) page; this is the overview.

### Part A: Language level and build { #part-a }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-001](../rules/cpp20.md#kb-cpp20-001) Strict ISO C++20, with a conformance build on every target compiler | required | DLH | 4.1.1, 4.1.2 | compiler, handbook check, strict-dialect build |
| [KB-CPP20-002](../rules/cpp20.md#kb-cpp20-002) Only profile features; nothing from C++23 or later | required | DLH | 4.1.1, 4.1.2 | compiler, handbook check |
| [KB-CPP20-003](../rules/cpp20.md#kb-cpp20-003) Nothing C++20 deprecates | required | DLH | 4.1.2, 10.1.2 | compiler, clang-tidy |
| [KB-CPP20-004](../rules/cpp20.md#kb-cpp20-004) No feature-test macros to choose behaviour | advisory | DL | 4.1.1, 19.0.1 | handbook check |

### Part B: Templates and concepts { #part-b }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-005](../rules/cpp20.md#kb-cpp20-005) Every template parameter is constrained by a named concept | required | DL | 17.8.1, Dir 0.3.2 | CodeQL (planned), review |
| [KB-CPP20-006](../rules/cpp20.md#kb-cpp20-006) Port concepts check the exact hook signature and `noexcept` | required | D | 7.0.6, 0.1.2, 4.1.3 | compile-fail tests, CodeQL (planned) |
| [KB-CPP20-007](../rules/cpp20.md#kb-cpp20-007) Optional hooks use named detection concepts; a misdeclared hook is an error | required | D | 0.1.2, 9.6.5 | handbook check, compile-fail tests |
| [KB-CPP20-008](../rules/cpp20.md#kb-cpp20-008) One dependent-false helper | advisory | DL | 0.0.1 | review |
| [KB-CPP20-009](../rules/cpp20.md#kb-cpp20-009) Code that does not depend on the port lives outside the class template | advisory | DL | 6.2.3 | CodeQL (planned), review |
| [KB-CPP20-010](../rules/cpp20.md#kb-cpp20-010) Abbreviated function templates are constrained and stay out of the public API | advisory | DL | 17.8.1 | CodeQL (planned), review |
| [KB-CPP20-011](../rules/cpp20.md#kb-cpp20-011) Concepts carry meaning; overloads are not chosen by subsumption | advisory | DL | 17.8.1 | review |

### Part C: Compile-time evaluation { #part-c }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-012](../rules/cpp20.md#kb-cpp20-012) Pure computations are `constexpr` and proved with `static_assert` | required | DL | 0.0.1, 4.1.3 | CodeQL (planned), review |
| [KB-CPP20-013](../rules/cpp20.md#kb-cpp20-013) `consteval` only for build-time construction | advisory | DLH | 0.1.2, Dir 0.3.2 | review |
| [KB-CPP20-014](../rules/cpp20.md#kb-cpp20-014) `constinit` on every mutable static | required | LH | 6.7.2, 6.7.1 | clang-tidy, CodeQL (planned) |
| [KB-CPP20-015](../rules/cpp20.md#kb-cpp20-015) `if constexpr` only on compile-time facts, each branch instantiated by a test | required | DL | 0.0.1, 0.0.2 | coverage, review |
| [KB-CPP20-016](../rules/cpp20.md#kb-cpp20-016) No `std::is_constant_evaluated` | advisory | DL | 0.0.2 | handbook check |
| [KB-CPP20-017](../rules/cpp20.md#kb-cpp20-017) Header-scope variables are `constexpr` | required | DLH | 6.2.4, 6.2.1, 6.7.2 | clang-tidy, CodeQL (planned) |
| [KB-CPP20-018](../rules/cpp20.md#kb-cpp20-018) Configuration-dependent inline code: one configuration per program | required | DL | 6.2.1 | handbook check, review |
| [KB-CPP20-019](../rules/cpp20.md#kb-cpp20-019) No allocation and no virtual functions in constant evaluation | required | DL | 21.6.1, 21.6.2 | handbook check |

### Part D: Integers, bits and enumerations { #part-d }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-020](../rules/cpp20.md#kb-cpp20-020) Every shift count is provably below the operand width | mandatory | DLH | 7.0.4, 4.1.3 | clang-tidy, UBSan, CodeQL (planned) |
| [KB-CPP20-021](../rules/cpp20.md#kb-cpp20-021) Bit work in `uint32_t`; no promoted narrow operands; no platform-width types | required | DLH | 7.0.5, 7.0.4, 6.9.2 | clang-tidy, CodeQL (planned) |
| [KB-CPP20-022](../rules/cpp20.md#kb-cpp20-022) Narrowing is explicit, compound assignment included | required | DLH | 7.0.6 | compiler, clang-tidy, CodeQL (planned) |
| [KB-CPP20-023](../rules/cpp20.md#kb-cpp20-023) Mixed-sign comparison through `std::cmp_less` and its siblings | advisory | DLH | 7.0.5 | compiler |
| [KB-CPP20-024](../rules/cpp20.md#kb-cpp20-024) Signed reinterpretation of wire values through a named helper | required | DL | 12.3.1, 6.8.1, 8.2.5 | clang-tidy |
| [KB-CPP20-025](../rules/cpp20.md#kb-cpp20-025) Integer-to-enum conversion only for proven enumerators | mandatory | DLH | 4.1.3, 10.2.1 | CodeQL (planned), review |
| [KB-CPP20-026](../rules/cpp20.md#kb-cpp20-026) One enumeration utility layer | advisory | DL | 17.8.1 | review |
| [KB-CPP20-027](../rules/cpp20.md#kb-cpp20-027) `using enum` only at block scope | required | DLH | 6.4.1, 10.2.2 | CodeQL (planned), review |
| [KB-CPP20-028](../rules/cpp20.md#kb-cpp20-028) `<bit>` for counting and rotation instead of hand-written loops | advisory | DLH | 7.0.4, 9.5.1 | review |
| [KB-CPP20-029](../rules/cpp20.md#kb-cpp20-029) `std::bit_cast` between equal-size values, never for byte order | required | DLH | 8.2.5, 8.2.4, 8.2.6, 6.8.1 | clang-tidy, CodeQL (planned) |
| [KB-CPP20-030](../rules/cpp20.md#kb-cpp20-030) Strong types for units and easily swapped parameters | advisory | DL | 7.0.6 | review (clang-tidy once re-enabled) |

### Part E: Initialisation, aggregates and comparison { #part-e }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-031](../rules/cpp20.md#kb-cpp20-031) Designated initialisers for configuration; every member has a default | required | DLH | 11.6.1, 15.1.4, 7.0.6 | clang-tidy |
| [KB-CPP20-032](../rules/cpp20.md#kb-cpp20-032) No parenthesised aggregate initialisation | required | DLH | 7.0.6 | CodeQL (planned), review |
| [KB-CPP20-033](../rules/cpp20.md#kb-cpp20-033) Defaulted `operator==` only on exactly comparable members | required | DLH | 16.6.1, Dir 0.3.1 | CodeQL (planned), review |
| [KB-CPP20-034](../rules/cpp20.md#kb-cpp20-034) No three-way comparison in drivers | required | D | 16.6.1 | handbook check |
| [KB-CPP20-035](../rules/cpp20.md#kb-cpp20-035) Structured bindings test the error before the value | advisory | DLH | 0.1.2, 11.6.2 | CodeQL (planned), review |
| [KB-CPP20-036](../rules/cpp20.md#kb-cpp20-036) Class-type template arguments are structural and integral | advisory | DL | 17.8.1 | review |

### Part F: Attributes { #part-f }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-037](../rules/cpp20.md#kb-cpp20-037) `[[nodiscard]]` on every error-carrying type | required | DLH | 0.1.2 | handbook check, compiler, clang-tidy |
| [KB-CPP20-038](../rules/cpp20.md#kb-cpp20-038) `[[maybe_unused]]` instead of `(void)` for conditionally used names | advisory | DLH | 0.2.2 | compiler |
| [KB-CPP20-039](../rules/cpp20.md#kb-cpp20-039) No `[[fallthrough]]` | required | DLH | 9.4.2 | handbook check, compiler |
| [KB-CPP20-040](../rules/cpp20.md#kb-cpp20-040) `[[likely]]` and `[[unlikely]]` only with a measurement | advisory | DLH | none | handbook check |
| [KB-CPP20-041](../rules/cpp20.md#kb-cpp20-041) No `[[no_unique_address]]` in drivers | required | D | 12.2.1, 21.2.4 | handbook check |

### Part G: Buffers and spans { #part-g }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-042](../rules/cpp20.md#kb-cpp20-042) Caller buffers are spans, with a fixed extent when the size is known | required | DLH | 7.11.2, 8.7.1 | CodeQL (planned), review |
| [KB-CPP20-043](../rules/cpp20.md#kb-cpp20-043) A dynamic span is checked before it is indexed, wherever it is indexed | required | DLH | 8.7.1, 4.1.3 | library assertions, sanitizers, CodeQL (planned) |
| [KB-CPP20-044](../rules/cpp20.md#kb-cpp20-044) Views and references never outlive what they refer to | mandatory | DLH | 6.8.2, 6.8.3, 6.8.1, 6.8.4 | clang-tidy, CodeQL (planned) |

### Part H: Lambdas { #part-h }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-045](../rules/cpp20.md#kb-cpp20-045) Lambdas: explicit captures, local use, no state | required | DLH | 8.1.1, 8.1.2, 7.11.3 | clang-tidy, CodeQL (planned) |
| [KB-CPP20-046](../rules/cpp20.md#kb-cpp20-046) No lambdas in unevaluated operands or at namespace scope in headers | required | DLH | 6.2.1 | CodeQL (planned), review |
| [KB-CPP20-047](../rules/cpp20.md#kb-cpp20-047) No generic lambdas in drivers | advisory | D | 17.8.1 | CodeQL (planned), review |

### Part I: Library vocabulary { #part-i }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-048](../rules/cpp20.md#kb-cpp20-048) `std::optional` is read only when engaged, never through `.value()` | mandatory | DLH | 4.1.3, 0.1.2, Dir 0.3.2 | clang-tidy, review |
| [KB-CPP20-049](../rules/cpp20.md#kb-cpp20-049) No `variant`, `any`, `function` or `expected` in drivers | required | D | 21.6.1 | handbook check |
| [KB-CPP20-050](../rules/cpp20.md#kb-cpp20-050) Range algorithms with rules; no views in target code | required | DLH | 28.3.1, 9.5.2, 6.8.1 | handbook check |
| [KB-CPP20-051](../rules/cpp20.md#kb-cpp20-051) No `<format>`, `std::format` or `std::print` | required | DLH | 21.6.1, 21.10.1 | handbook check |
| [KB-CPP20-052](../rules/cpp20.md#kb-cpp20-052) No `std::source_location` in drivers | required | D | none | handbook check |
| [KB-CPP20-053](../rules/cpp20.md#kb-cpp20-053) No `char8_t` and no `u8` literals in target code | required | DLH | 7.0.3 | handbook check |
| [KB-CPP20-054](../rules/cpp20.md#kb-cpp20-054) `<numbers>` for mathematical constants | advisory | DLH | Dir 0.3.1 | clang-tidy |
| [KB-CPP20-055](../rules/cpp20.md#kb-cpp20-055) `std::atomic_ref` only for lock-free sharing with an interrupt | advisory | H | 10.1.2 | review |

### Part J: Large features we forbid { #part-j }

| Guideline | Category | Scope | MISRA C++:2023 | Enforced by |
| --- | --- | --- | --- | --- |
| [KB-CPP20-056](../rules/cpp20.md#kb-cpp20-056) No coroutines | required | DLH | 21.6.1, 8.2.10 | handbook check, clang-tidy |
| [KB-CPP20-057](../rules/cpp20.md#kb-cpp20-057) No modules | required | DLH | 4.1.1 | handbook check |
| [KB-CPP20-058](../rules/cpp20.md#kb-cpp20-058) Loops are bounded by a validated constant | required | DLH | 9.5.1, 0.0.2 | clang-tidy, CodeQL (planned), review |

## How MISRA C++:2023 applies to C++20 constructs { #mapping }

MD-CPP-001's mitigation applies every guideline of the edition to the C++20 constructs we use, by these analogies.
The commercial checker's C++20 findings are triaged against them.

| C++20 construct | Treated as | Guidelines |
| --- | --- | --- |
| A concept | A template: the rules on templates apply to its instantiations | 17.8.1 and the template rules |
| The parameters of a requires-expression | Not function parameters: the unused-parameter rule does not apply to them | 0.2.2 |
| A designated initialiser | An initialisation: the conversion rule applies to each designator | 7.0.6 |
| Indexing a `std::span` | An array access; a span is a reference-like object for the lifetime rules | 8.7.1; 6.8.1 to 6.8.4 |
| A defaulted `operator==` | Covered by MD-CPP-002 and KB-CPP20-033 | 16.6.1 |
| A lambda in a template argument | A function object | 8.1.1, 8.1.2 |
| `std::bit_cast` | The permitted alternative to the casts these rules forbid, never applied to pointers | 8.2.5, 8.2.6 |
| A `constinit` object | Still a mutable static, inside MD-CPP-005's scope | 6.7.2 |
| A discarded `if constexpr` branch that no instantiation keeps | Unreachable code | 0.0.1 |

## What the build and the tools add { #tools }

- **Compiler**, in every target a repository builds: `-std=c++20` with `CMAKE_CXX_EXTENSIONS OFF`,
  `-pedantic-errors`, `-Wdeprecated -Wdeprecated-enum-enum-conversion -Wdeprecated-enum-float-conversion`,
  `-Wimplicit-fallthrough`, on top of KB-CPP-104's warnings and `-Werror`. Host tests and fuzz targets add the
  standard library's assertions (`-D_GLIBCXX_ASSERTIONS`, libc++ hardening) and the sanitizers.
- **Strict-dialect build**: every public header compiles alone at `-std=c++20 -pedantic-errors` with host GCC and
  Clang (host tests), Arm GCC (cross-build), and the ESP-IDF toolchain through a header self-check compiled at
  `-std=c++20` inside the ESP-IDF build, which also asserts that the flag took effect.
- **clang-tidy** (`config/.clang-tidy`): `bugprone-dangling-handle` also watches `std::span`; the checks that
  suggest `std::print` and `std::format` are off.
- **Source checks** (`checks/source_checks.py scan`): `cpp20-profile/forbidden-features`,
  `cpp20-profile/cmake-extensions`, `cpp20-profile/nodiscard-error`, `cpp20-profile/inline-requires` and
  `cpp20-profile/kconfig-leaf`, each proved by the script's self-test with a seeded violation.
- **CodeQL** (planned): the guidelines marked *CodeQL* get a query in the Kokeb pack; until then they are review
  steps. In priority order: 021, 022, 025, 058, 042, 020, 033, 006, 012, 044 and 045, then the rest.

## Zero-cost patterns { #patterns }

The driver template carries the patterns this profile asks for, with tests: exact port concepts
(`detail::Exactly<T>`), named optional-hook concepts, typed register fields (`detail::Field`), strong unit types
for public conversions, fixed-extent spans on the bus helpers, `consteval` checked configurations, and round-trip
`static_assert`s for encoders, CRC vectors and presets. None of them changes the generated code of the run-time
path. Its `docs/template.md` describes each one.

## Toolchain support { #toolchains }

Every feature in the *Use* and *Use with rules* sets is available from GCC 11 and Clang 17; the pinned compilers
(host GCC 14 and Clang 18, Arm GCC 14, ESP-IDF's GCC) all exceed that. Features of note:

| Feature | GCC | Clang | Profile |
| --- | --- | --- | --- |
| `consteval` | 11 | 17 | KB-CPP20-013 |
| `using enum` | 11 | 13 | KB-CPP20-027 |
| `std::bit_cast` | 11 | 14 | KB-CPP20-029 |
| `std::source_location` | 11 | 16 | KB-CPP20-052 |
| `std::atomic_ref` | 10 | 19 | KB-CPP20-055 |
| Parenthesised aggregate initialisation | 10 | 16 | forbidden (KB-CPP20-032) |
| Lambdas in unevaluated contexts | 9 | 17 | forbidden (KB-CPP20-046) |
| `std::format` | 13 | 17 | forbidden (KB-CPP20-051) |
| Coroutines | 10 | 17 | forbidden (KB-CPP20-056) |
| Modules | partial | partial | forbidden (KB-CPP20-057) |
