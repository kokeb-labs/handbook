#!/usr/bin/env python3
"""Source checks of the handbook: rules a script decides from a driver's or library's files.

  scan      check a repository (--repo DIR) and fail on a finding
  guard     print the include guard a header must use (--repo DIR PATH...)
  selftest  build small repositories with known breaks and confirm each break is reported (handbook CI runs this)

The checks, each named in checks/registry.yml:

  include-guards      KB-CPP-019, MISRA C++:2023 Rules 19.2.1 and 19.6.1. Every header (.h, .hh, .hpp, .hxx, .ipp,
                      .inl, and the same with .in for a configured header) under inc/, include/, src/, tests/ and
                      examples/ is wrapped in #ifndef GUARD / #define GUARD ... #endif, with the guard closing at the
                      end of the file and the name not reserved (no leading underscore, no double underscore). Under
                      inc/, include/ and src/ the name is the one `guard` prints. No file in those folders uses
                      #pragma (once or any other) or _Pragma. Guard names are unique in the repository.
  bus-requirements    KB-CPP-123. A driver (or the template) declares its bus requirements as constexpr in
                      inc/<name>_<bus>_interface.hpp for every bus in driver.yml (SPI, I2C, UART).
  raw-access          KB-CPP-129. A driver's inc/<name>.hpp declares a single-shot raw access (ReadRegister, ReadRaw...
                      or Trace...) and a no-I/O accessor for the last raw reply or status (GetLast...).
  cpp20-profile/...   The C++20 profile (rules/cpp20.yml), in drivers, libraries, HALs, firmware and templates:
    forbidden-features  in inc/, include/ and src/: no coroutines (KB-CPP20-056), modules (057), <ranges> or range
                        views (050), <format>, <print> or std::format/print (051), C++23-or-later features (002),
                        feature-test macros or <version> (004), std::is_constant_evaluated (016), [[fallthrough]]
                        (039), [[likely]]/[[unlikely]] without a `measured` comment on the line (040), char8_t or
                        u8 literals (053); in drivers and templates also no <=> or <compare> (034),
                        [[no_unique_address]] (041), std::variant, any, function or expected (049) and no
                        <source_location> (052).
    cmake-extensions    KB-CPP20-001. Every CMakeLists.txt that builds a target (add_executable, or add_library
                        that is not INTERFACE, ALIAS or IMPORTED) sets CMAKE_CXX_EXTENSIONS OFF, itself or in the
                        CMakeLists.txt of a parent directory; nothing sets extensions ON.
    nodiscard-error     KB-CPP20-037. In inc/ and include/, every `enum class` named Error (or ...Error) and every
                        Result class or struct is declared [[nodiscard]].
    inline-requires     KB-CPP20-007. No requires-expression in an `if constexpr` condition in inc/, include/ or
                        src/: optional hooks are detected by named concepts.
    kconfig-leaf        KB-CPP20-018. No header in inc/, include/ or src/ includes the Kconfig header
                        (<name>_kconfig.hpp, Kconfig.h), which only applications and tests include.

The guard name is <NAME>_<FILE_STEM>_<EXT> in upper case: NAME is the repository's name (driver.yml `name`, else
.kokeb/template.yml `name`, else --name), FILE_STEM the file name without its extension, in snake case (MovingAverage
-> MOVING_AVERAGE), and EXT the extension (a configured `.h.in` guards as the `.h` it becomes). NAME is not repeated
when the stem already starts with it: inc/ads7952_types.hpp -> ADS7952_TYPES_HPP, inc/ads7952.hpp -> ADS7952_HPP,
tests/mock_ads7952.hpp -> ADS7952_MOCK_ADS7952_HPP, inc/ring/Result.h in ring_buffer -> RING_BUFFER_RESULT_H.

Usage: source_checks.py scan [--repo .] [--name NAME]
       source_checks.py guard [--repo .] [--name NAME] PATH...
       source_checks.py selftest
Exit status: 1 when there is a finding, 2 when the repository's name cannot be found, 0 otherwise.
Standard library only (Python 3.9+), so a repository's CI can run it without installing anything.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import subprocess
import sys
import tempfile

HEADER_SUFFIXES = (".h", ".hh", ".hpp", ".hxx", ".ipp", ".inl")
SOURCE_SUFFIXES = HEADER_SUFFIXES + (".c", ".cc", ".cpp", ".cxx")
CODE_DIRS = ("inc", "include", "src", "tests", "examples")
NAMED_DIRS = ("inc", "include", "src")  # where the guard name is fixed by the convention
SKIP_PARTS = {".git", "third_party", "_deps", "managed_components", "external", "node_modules", "scripts"}
BUS_FILE = {"spi": "spi", "i2c": "i2c", "uart": "uart"}
# KB-CPP-123: the constants each bus interface declares. The handbook's driver page explains each one.
BUS_CONSTANTS = {
    "spi": ("kSpiMode", "kMsbFirst", "kMaxClockHz", "kMinCsHighNs", "kCsSetupNs", "kCsHoldNs", "kContinuousWord"),
    "i2c": ("kI2cAddress", "kMaxClockHz", "kRepeatedStart"),
    "uart": ("kMaxBaudRate", "kTurnaroundUs"),
}
TARGET_KINDS = ("driver", "library", "hal", "firmware", "template")
TARGET_DIRS = ("inc", "include", "src")
# KB-CPP20 forbidden features: (rule, regex on comment- and string-free code, message, drivers only).
CPP20_FORBIDDEN = [
    ("KB-CPP20-056", r"\bco_(?:await|yield|return)\b|#\s*include\s*<coroutine>", "a coroutine", False),
    ("KB-CPP20-057", r"^\s*(?:export\s+)?module\b\s*[\w:.;]|^\s*(?:export\s+)?import\s+[\w<\":]",
     "a module declaration or import", False),
    ("KB-CPP20-050", r"#\s*include\s*<ranges>|\bviews::", "<ranges> or a range view", False),
    ("KB-CPP20-051", r"#\s*include\s*<(?:format|print)>|\bstd::(?:format|format_to|format_to_n|vformat|print|println)\b",
     "<format>, <print> or std::format/print", False),
    ("KB-CPP20-002",
     r"#\s*include\s*<(?:expected|stacktrace|generator|mdspan|flat_map|flat_set|spanstream|stdfloat|print|"
     r"text_encoding|debugging|linalg|inplace_vector|hazard_pointer|rcu)>|"
     r"\bstd::(?:expected|unexpected|to_underlying|byteswap|unreachable|mdspan|flat_map|flat_set|generator|"
     r"stacktrace|move_only_function|out_ptr|inout_ptr|start_lifetime_as|forward_like|inplace_vector)\b|"
     r"\bif\s+!?\s*consteval\b|\[\[\s*assume\b|\(\s*this\s+(?:auto|const\s+auto|[A-Z]\w*)\b|"
     r"\b\d[\d']*(?:[uU][zZ]|[zZ][uU]?)\b|^\s*#\s*(?:elifdef|elifndef|warning|embed)\b",
     "a C++23 or later feature (MD-CPP-001 covers C++20 only)", False),
    ("KB-CPP20-004", r"\b__cpp_\w+|#\s*include\s*<version>", "a feature-test macro or <version>", False),
    ("KB-CPP20-016", r"\bis_constant_evaluated\b", "std::is_constant_evaluated", False),
    ("KB-CPP20-039", r"\[\[\s*fallthrough\s*\]\]", "[[fallthrough]]: end every switch clause", False),
    ("KB-CPP20-053", r"\bchar8_t\b|\bu8(?=[\"'])", "char8_t or a u8 literal", False),
    ("KB-CPP20-034", r"<=>|#\s*include\s*<compare>", "three-way comparison in a driver", True),
    ("KB-CPP20-041", r"\[\[\s*no_unique_address\s*\]\]", "[[no_unique_address]] in a driver", True),
    ("KB-CPP20-049", r"#\s*include\s*<(?:variant|any|functional|expected)>|\bstd::(?:variant|any|function)\b",
     "std::variant, std::any, std::function or std::expected in a driver", True),
    ("KB-CPP20-052", r"#\s*include\s*<source_location>|\bstd::source_location\b",
     "std::source_location in a driver", True),
]
LIKELY_RE = re.compile(r"\[\[\s*(?:likely|unlikely)\s*\]\]")
NODISCARD_TYPE_RE = re.compile(
    r"\b(?P<kind>enum\s+class|enum\s+struct|struct|class)\s+(?P<attrs>(?:\[\[[^\]]*\]\]\s*)*)"
    r"(?P<name>\w+)\s*(?:<[^<>{};]*>\s*)?(?::[^;{]*)?\{")
INLINE_REQUIRES_RE = re.compile(r"\bif\s+constexpr\s*\(\s*!?\s*\(?\s*requires\b")
KCONFIG_HEADER_RE = re.compile(r"(?:^|[/_])[kK]config\.(?:hpp|h)$")
INCLUDE_RE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]")
CMAKE_TARGET_RE = re.compile(r"\b(add_executable|add_library)\s*\(([^)]*)\)", re.I | re.S)
CMAKE_EXT_OFF_RE = re.compile(
    r"\bset\s*\(\s*CMAKE_CXX_EXTENSIONS\s+(?:OFF|FALSE|NO|0)\s*\)|\bCXX_EXTENSIONS\s+(?:OFF|FALSE|NO|0)\b", re.I)
CMAKE_EXT_ON_RE = re.compile(r"\bCMAKE_CXX_EXTENSIONS\s+(?:ON|TRUE|YES|1)\b|\bCXX_EXTENSIONS\s+(?:ON|TRUE|YES|1)\b",
                             re.I)
RAW_ACCESS_RE = re.compile(r"\b(?:ReadRegister\w*|ReadRaw\w*|Trace[A-Z]\w*)\s*\(")
LAST_REPLY_RE = re.compile(r"\bGetLast[A-Z]\w*\s*\(")
HANDBOOK = "https://kokeb-labs.github.io/handbook/rules"


@dataclasses.dataclass
class Finding:
    rule: str
    check: str
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        page = "cpp20" if self.rule.startswith("KB-CPP20-") else "cpp"
        where = f"file={self.path},line={self.line}" if self.line else f"file={self.path}"
        return f"::error {where}::{self.rule} ({self.check}): {self.message} ({HANDBOOK}/{page}/#{self.rule.lower()})"


def strip_comments(text: str) -> str:
    """Blank out comments and the contents of string and character literals, keeping every newline."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(c + " " * max(0, min(j, n) - i - 1) + (c if j < n and text[j] == c else ""))
            i = j + 1 if j < n and text[j] == c else j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def snake(stem: str) -> str:
    stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", stem)
    return re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").upper()


def header_kind(rel: str) -> str | None:
    """The extension a header guards as (`HPP`), or None for a file that is not a header."""
    name = rel.rsplit("/", 1)[-1]
    if name.endswith(".in"):
        name = name[:-3]
    for suffix in HEADER_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return suffix[1:].upper()
    return None


def expected_guard(repo_name: str, rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    if name.endswith(".in"):
        name = name[:-3]
    stem, ext = name.rsplit(".", 1)
    prefix, base = snake(repo_name), snake(stem)
    if base != prefix and not base.startswith(prefix + "_"):
        base = f"{prefix}_{base}"
    return f"{base}_{ext.upper()}"


def guard_problems(text: str) -> tuple[str | None, list[tuple[int, str]]]:
    """The guard a header uses and what is wrong with it: (name or None, [(line, message)])."""
    lines = [(i + 1, ln.strip()) for i, ln in enumerate(strip_comments(text).splitlines()) if ln.strip()]
    if len(lines) < 3:
        return None, [(1, "no #ifndef/#define/#endif include guard")]
    (l1, first), (_, second), (ln_last, last) = lines[0], lines[1], lines[-1]
    m = re.fullmatch(r"#\s*ifndef\s+(\w+)", first)
    if not m:
        return None, [(l1, "the first line of code is not `#ifndef <GUARD>`: no include guard")]
    guard = m.group(1)
    bad: list[tuple[int, str]] = []
    if not re.fullmatch(rf"#\s*define\s+{re.escape(guard)}", second):
        bad.append((lines[1][0], f"`#ifndef {guard}` is not followed by `#define {guard}`"))
    if not re.fullmatch(r"#\s*endif\b.*", last):
        bad.append((ln_last, "the file does not end with the guard's `#endif`"))
    depth = 0
    for num, ln in lines:
        if re.match(r"#\s*if(n?def)?\b", ln):
            depth += 1
        elif re.match(r"#\s*endif\b", ln):
            depth -= 1
            if depth == 0 and num != ln_last:
                bad.append((num, "the include guard closes before the end of the file"))
                break
    if guard.startswith("_") or "__" in guard:
        bad.append((l1, f"`{guard}` is a reserved identifier (leading or double underscore)"))
    return guard, bad


class Repo:
    def __init__(self, root: pathlib.Path, name: str | None):
        self.root = root
        self.findings: list[Finding] = []
        self.kind = self._field(".kokeb/handbook.yml", "kind") or ""
        self.name = name or self._field("driver.yml", "name") or self._field(".kokeb/template.yml", "name")

    def _field(self, rel: str, key: str) -> str | None:
        path = self.root / rel
        if not path.is_file():
            return None
        m = re.search(rf"^{key}:\s*['\"]?([A-Za-z0-9_.-]+)", path.read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else None

    def files(self) -> list[str]:
        try:
            out = subprocess.run(["git", "ls-files", "-z", "--", *CODE_DIRS], cwd=self.root, capture_output=True,
                                 check=True).stdout.decode()
            rels = [r for r in out.split("\0") if r]
        except (OSError, subprocess.CalledProcessError):
            rels = [p.relative_to(self.root).as_posix() for d in CODE_DIRS if (self.root / d).is_dir()
                    for p in (self.root / d).rglob("*") if p.is_file()]
        keep = []
        for rel in sorted(rels):
            parts = rel.split("/")
            if parts[0] not in CODE_DIRS or SKIP_PARTS & set(parts) or any(p.startswith("build") for p in parts):
                continue
            keep.append(rel)
        return keep

    def add(self, rule: str, check: str, rel: str, line: int, message: str) -> None:
        self.findings.append(Finding(rule, check, rel, line, message))

    def check_include_guards(self) -> None:
        seen: dict[str, str] = {}
        for rel in self.files():
            is_header = header_kind(rel) is not None
            if not (is_header or rel.endswith(SOURCE_SUFFIXES)):
                continue
            text = (self.root / rel).read_text(encoding="utf-8", errors="replace")
            code = strip_comments(text)
            for num, ln in enumerate(code.splitlines(), 1):
                if re.match(r"\s*#\s*pragma\b", ln) or re.search(r"\b_Pragma\s*\(", ln):
                    what = "#pragma once" if re.search(r"pragma\s+once", ln) else "a #pragma"
                    self.add("KB-CPP-019", "include-guards", rel, num,
                             f"{what}: headers use #ifndef include guards and the build sets compiler options "
                             "(MISRA C++:2023 Rules 19.2.1, 19.6.1)")
            if not is_header:
                continue
            guard, bad = guard_problems(text)
            for num, msg in bad:
                self.add("KB-CPP-019", "include-guards", rel, num, msg)
            if guard is None:
                continue
            if rel.split("/", 1)[0] in NAMED_DIRS:
                want = expected_guard(self.name or "", rel)
                if guard != want:
                    self.add("KB-CPP-019", "include-guards", rel, 1, f"the guard is `{guard}`; it must be `{want}`")
            if guard in seen:
                self.add("KB-CPP-019", "include-guards", rel, 1, f"guard `{guard}` is also used by {seen[guard]}")
            seen.setdefault(guard, rel)

    def buses(self) -> list[str]:
        path = self.root / "driver.yml"
        if not path.is_file():
            return []
        m = re.search(r"^bus:\s*\[([^\]]*)\]", path.read_text(encoding="utf-8"), re.M)
        return [b.strip() for b in m.group(1).split(",") if b.strip()] if m else []

    def is_driver(self) -> bool:
        return self.kind in ("driver", "template") and (self.root / "driver.yml").is_file()

    def check_bus_requirements(self) -> None:
        if not self.is_driver():
            return
        for bus in self.buses():
            if bus not in BUS_CONSTANTS:
                continue
            rel = f"inc/{self.name}_{BUS_FILE[bus]}_interface.hpp"
            path = self.root / rel
            if not path.is_file():
                self.add("KB-CPP-123", "bus-requirements", rel, 0, f"driver.yml lists {bus} but there is no {rel}")
                continue
            code = strip_comments(path.read_text(encoding="utf-8"))
            missing = [c for c in BUS_CONSTANTS[bus] if not re.search(rf"\bconstexpr\b[^;{{}}()]*\b{c}\b", code)]
            if missing:
                self.add("KB-CPP-123", "bus-requirements", rel, 0,
                         f"the {bus} requirements are not all declared as constexpr: missing {', '.join(missing)}")

    def check_raw_access(self) -> None:
        if not self.is_driver():
            return
        rel = f"inc/{self.name}.hpp"
        path = self.root / rel
        if not path.is_file():
            self.add("KB-CPP-129", "raw-access", rel, 0, "the driver header is missing")
            return
        code = strip_comments(path.read_text(encoding="utf-8"))
        if not RAW_ACCESS_RE.search(code):
            self.add("KB-CPP-129", "raw-access", rel, 0,
                     "no single-shot raw access (ReadRegister..., ReadRaw... or Trace...)")
        if not LAST_REPLY_RE.search(code):
            self.add("KB-CPP-129", "raw-access", rel, 0, "no no-I/O accessor for the last raw reply (GetLast...)")

    # -- the C++20 profile (rules/cpp20.yml) ------------------------------------------------------------------------
    def is_target(self) -> bool:
        return self.kind in TARGET_KINDS

    def target_sources(self) -> list[str]:
        return [rel for rel in self.files() if rel.split("/", 1)[0] in TARGET_DIRS
                and (header_kind(rel) is not None or rel.endswith(SOURCE_SUFFIXES))]

    def check_cpp20_sources(self) -> None:
        if not self.is_target():
            return
        driver = self.kind in ("driver", "template")
        forbidden = [(rule, re.compile(rx, re.M), msg) for rule, rx, msg, only_driver in CPP20_FORBIDDEN
                     if driver or not only_driver]
        for rel in self.target_sources():
            raw = (self.root / rel).read_text(encoding="utf-8", errors="replace")
            code = strip_comments(raw)
            raw_lines = raw.splitlines()
            code_lines = code.splitlines()
            for num, ln in enumerate(code_lines, 1):
                for rule, rx, msg in forbidden:
                    if rx.search(ln):
                        self.add(rule, "cpp20-profile/forbidden-features", rel, num, f"{msg} (the C++20 profile)")
                if LIKELY_RE.search(ln) and "measured" not in raw_lines[num - 1]:
                    self.add("KB-CPP20-040", "cpp20-profile/forbidden-features", rel, num,
                             "[[likely]]/[[unlikely]] without a `measured` comment naming the measurement")
                if INLINE_REQUIRES_RE.search(ln):
                    self.add("KB-CPP20-007", "cpp20-profile/inline-requires", rel, num,
                             "a requires-expression in an if constexpr condition: detect the hook with a named "
                             "Has<Hook> concept in detail")
                inc = INCLUDE_RE.match(raw_lines[num - 1]) if ln.lstrip().startswith("#") else None
                if inc and KCONFIG_HEADER_RE.search(inc.group(1)) and not KCONFIG_HEADER_RE.search(rel):
                    self.add("KB-CPP20-018", "cpp20-profile/kconfig-leaf", rel, num,
                             f"includes {inc.group(1)}: the Kconfig header is a leaf that only applications and "
                             "tests include (one configuration per program)")
            if rel.split("/", 1)[0] in ("inc", "include"):
                for m in NODISCARD_TYPE_RE.finditer(code):
                    name, kind = m.group("name"), m.group("kind")
                    is_error = kind.startswith("enum") and (name == "Error" or name.endswith("Error"))
                    is_result = not kind.startswith("enum") and name == "Result"
                    if (is_error or is_result) and "nodiscard" not in m.group("attrs"):
                        line = code.count("\n", 0, m.start()) + 1
                        self.add("KB-CPP20-037", "cpp20-profile/nodiscard-error", rel, line,
                                 f"`{name}` is not declared [[nodiscard]]: put the attribute on the type "
                                 f"(`{kind} [[nodiscard]] {name}`)")

    def cmake_files(self) -> list[str]:
        try:
            out = subprocess.run(["git", "ls-files", "-z", "--", "CMakeLists.txt", "*/CMakeLists.txt"],
                                 cwd=self.root, capture_output=True, check=True).stdout.decode()
            rels = [r for r in out.split("\0") if r]
        except (OSError, subprocess.CalledProcessError):
            rels = [p.relative_to(self.root).as_posix() for p in self.root.rglob("CMakeLists.txt")]
        keep = []
        for rel in sorted(set(rels)):
            parts = rel.split("/")
            if SKIP_PARTS & set(parts) or any(p.startswith("build") for p in parts[:-1]):
                continue
            keep.append(rel)
        return keep

    def check_cmake_extensions(self) -> None:
        if not self.is_target():
            return
        files = self.cmake_files()
        texts = {rel: re.sub(r"#[^\n]*", "", (self.root / rel).read_text(encoding="utf-8", errors="replace"))
                 for rel in files}
        sets_off = {rel for rel, text in texts.items() if CMAKE_EXT_OFF_RE.search(text)}
        for rel, text in texts.items():
            for m in CMAKE_EXT_ON_RE.finditer(text):
                self.add("KB-CPP20-001", "cpp20-profile/cmake-extensions", rel, text.count("\n", 0, m.start()) + 1,
                         "compiler extensions are on: the code is ISO C++20 (CMAKE_CXX_EXTENSIONS OFF)")
            builds = [m for m in CMAKE_TARGET_RE.finditer(text)
                      if not re.search(r"\b(INTERFACE|ALIAS|IMPORTED)\b", m.group(2))]
            if not builds:
                continue
            folder = rel.rsplit("/", 1)[0] if "/" in rel else ""
            parents = {"CMakeLists.txt"} | {"/".join(folder.split("/")[:i]) + "/CMakeLists.txt"
                                            for i in range(1, folder.count("/") + 2) if folder}
            # A file with its own project() is also configured on its own (examples/host, an install consumer).
            standalone = rel != "CMakeLists.txt" and re.search(r"\bproject\s*\(", text, re.I)
            if (standalone and rel not in sets_off) or not (parents & sets_off):
                line = text.count("\n", 0, builds[0].start()) + 1
                self.add("KB-CPP20-001", "cpp20-profile/cmake-extensions", rel, line,
                         "builds a target without CMAKE_CXX_EXTENSIONS OFF here or in a parent directory: CMake's "
                         "default is the GNU dialect (-std=gnu++20)")

    def scan(self) -> list[Finding]:
        self.check_include_guards()
        self.check_bus_requirements()
        self.check_raw_access()
        self.check_cpp20_sources()
        self.check_cmake_extensions()
        return self.findings


# -- self-test ---------------------------------------------------------------------------------------------------
GOOD = {
    ".kokeb/handbook.yml": 'handbook: "1.0"\nkind: driver\nlevel: high\n',
    "driver.yml": "name: zp100\nversion: 0.1.0\nbus: [spi]\n",
    "inc/zp100.hpp": "/** @file zp100.hpp */\n#ifndef ZP100_HPP\n#define ZP100_HPP\n#include \"zp100_types.hpp\"\n"
                     "class Zp100 {\n public:\n  int ReadRegister(int a);\n  int GetLastReply() const;\n};\n"
                     "#if defined(X)\nint x;\n#endif\n#endif // ZP100_HPP\n",
    "inc/zp100_types.hpp": "#ifndef ZP100_TYPES_HPP\n#define ZP100_TYPES_HPP\n// #pragma once in a comment is fine\n"
                           "const char* s = \"#pragma once\";\n"
                           "// co_await, std::format and [[fallthrough]] in a comment are fine\n"
                           "enum class [[nodiscard]] Error : uint8_t { Ok = 0 };\n"
                           "template <typename T>\nstruct [[nodiscard]] Result { T value{}; };\n"
                           "template <>\nstruct [[nodiscard]] Result<void> { Error error{}; };\n"
                           "enum class LogLevel : uint8_t { Error = 0 };\n"
                           "inline constexpr uint32_t kBig = 10U;\n#endif\n",
    "inc/zp100_kconfig.hpp": "#ifndef ZP100_KCONFIG_HPP\n#define ZP100_KCONFIG_HPP\n#include \"zp100_types.hpp\"\n"
                             "#endif\n",
    "CMakeLists.txt": "cmake_minimum_required(VERSION 3.16)\nproject(zp100 LANGUAGES CXX)\n"
                      "set(CMAKE_CXX_EXTENSIONS OFF)\nadd_library(zp100 INTERFACE)\n"
                      "add_library(zp100::zp100 ALIAS zp100)\nadd_subdirectory(tests)\n",
    "tests/CMakeLists.txt": "# CMAKE_CXX_EXTENSIONS ON in a comment is fine\nadd_executable(zp100_tests test_zp100.cpp)\n",
    "examples/host/CMakeLists.txt": "project(zp100_host_example LANGUAGES CXX)\nset(CMAKE_CXX_EXTENSIONS OFF)\n"
                                    "add_executable(zp100_host_example main.cpp)\n",
    "inc/zp100_version.h.in": "#ifndef ZP100_VERSION_H\n#define ZP100_VERSION_H\n#define ZP100_V @V@\n#endif\n",
    "inc/zp100_spi_interface.hpp": (
        "#ifndef ZP100_SPI_INTERFACE_HPP\n#define ZP100_SPI_INTERFACE_HPP\nnamespace zp100 {\n"
        "inline constexpr uint8_t kSpiMode = 0;\ninline constexpr bool kMsbFirst = true;\n"
        "inline constexpr uint32_t kMaxClockHz = 1;\ninline constexpr uint32_t kMinCsHighNs = 1;\n"
        "inline constexpr uint32_t kCsSetupNs = 1;\ninline constexpr uint32_t kCsHoldNs = 1;\n"
        "inline constexpr bool kContinuousWord = true;\n}\n#endif\n"),
    "src/zp100.ipp": "#ifndef ZP100_IPP\n#define ZP100_IPP\nint f();\n#endif\n",
    "src/zp100.cpp": "int f() { return 0; }\n",
    "tests/mock_zp100.hpp": "#ifndef ZP100_MOCK_ZP100_HPP\n#define ZP100_MOCK_ZP100_HPP\n#endif\n",
    "tests/test_zp100.cpp": "int main() {}\n",
    "examples/host/host_zp100_port.hpp": "#ifndef ZP100_HOST_ZP100_PORT_HPP\n#define ZP100_HOST_ZP100_PORT_HPP\n"
                                         "#endif\n",
}
GUARDS = {
    ("zp100", "inc/zp100.hpp"): "ZP100_HPP",
    ("ads7952", "inc/ads7952_types.hpp"): "ADS7952_TYPES_HPP",
    ("max22200", "inc/max22200_spi_interface.hpp"): "MAX22200_SPI_INTERFACE_HPP",
    ("ads7952", "tests/mock_ads7952.hpp"): "ADS7952_MOCK_ADS7952_HPP",
    ("ring_buffer", "inc/ring/MovingAverage.h"): "RING_BUFFER_MOVING_AVERAGE_H",
    ("ring_buffer", "inc/ring/Version.h.in"): "RING_BUFFER_VERSION_H",
    ("xmpl100", "src/xmpl100.ipp"): "XMPL100_IPP",
}


def selftest() -> int:
    failures = []
    for (name, rel), want in GUARDS.items():
        if expected_guard(name, rel) != want:
            failures.append(f"guard for {name} {rel} is {expected_guard(name, rel)}, expected {want}")

    def run(changes: dict[str, str | None]) -> list[Finding]:
        with tempfile.TemporaryDirectory(prefix="source-checks-") as tmp:
            root = pathlib.Path(tmp)
            files = dict(GOOD)
            files.update(changes)
            for rel, text in files.items():
                if text is None:
                    continue
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
            return Repo(root, None).scan()

    clean = run({})
    if clean:
        failures.append("the clean repository has findings: " + "; ".join(str(f) for f in clean))
    hpp = GOOD["inc/zp100_types.hpp"]
    cases = {
        "#pragma once": ("include-guards", {"inc/zp100_types.hpp": "#pragma once\n" + hpp}),
        "#pragma once in a test header": ("include-guards", {
            "tests/mock_zp100.hpp": "#pragma once\n" + GOOD["tests/mock_zp100.hpp"]}),
        "another #pragma in a source": ("include-guards", {"src/zp100.cpp": "#pragma GCC optimize(\"O3\")\n"}),
        "_Pragma": ("include-guards", {"src/zp100.cpp": "_Pragma(\"once\")\nint f();\n"}),
        "no guard": ("include-guards", {"inc/zp100_types.hpp": "namespace zp100 {}\nint y;\nint z;\n"}),
        "a guard in a test header missing": ("include-guards", {"tests/mock_zp100.hpp": "int a;\nint b;\nint c;\n"}),
        "a mismatched guard name": ("include-guards", {"inc/zp100_types.hpp": hpp.replace("ZP100_TYPES", "TYPES")}),
        "a guard on the configured header": ("include-guards", {
            "inc/zp100_version.h.in": GOOD["inc/zp100_version.h.in"].replace("_H\n", "_H_IN\n")}),
        "#define differs from #ifndef": ("include-guards", {
            "inc/zp100_types.hpp": hpp.replace("#define ZP100_TYPES_HPP", "#define ZP100_TYPE_HPP")}),
        "a reserved guard": ("include-guards", {
            "tests/mock_zp100.hpp": "#ifndef _MOCK_H\n#define _MOCK_H\n#endif\n"}),
        "a double underscore": ("include-guards", {
            "tests/mock_zp100.hpp": "#ifndef ZP100__MOCK_H\n#define ZP100__MOCK_H\n#endif\n"}),
        "code after the guard": ("include-guards", {"inc/zp100_types.hpp": hpp + "int after;\n"}),
        "the guard closes early": ("include-guards", {
            "inc/zp100_types.hpp": "#ifndef ZP100_TYPES_HPP\n#define ZP100_TYPES_HPP\n#endif\n#ifdef X\n#endif\n"}),
        "a duplicate guard": ("include-guards", {"tests/other.hpp": GOOD["tests/mock_zp100.hpp"]}),
        "a missing bus constant": ("bus-requirements", {
            "inc/zp100_spi_interface.hpp": GOOD["inc/zp100_spi_interface.hpp"].replace("kCsHoldNs", "kHoldNs")}),
        "a bus constant only in a comment": ("bus-requirements", {
            "inc/zp100_spi_interface.hpp": GOOD["inc/zp100_spi_interface.hpp"].replace(
                "inline constexpr bool kMsbFirst = true;", "// constexpr bool kMsbFirst")}),
        "no interface for a listed bus": ("bus-requirements", {
            "driver.yml": "name: zp100\nversion: 0.1.0\nbus: [spi, i2c]\n"}),
        "no raw access": ("raw-access", {"inc/zp100.hpp": GOOD["inc/zp100.hpp"].replace("ReadRegister", "Read")}),
        "no last-reply accessor": ("raw-access", {"inc/zp100.hpp": GOOD["inc/zp100.hpp"].replace("GetLastReply",
                                                                                                "Reply")}),
    }
    src = GOOD["src/zp100.ipp"]

    def ipp(code: str) -> dict[str, str]:
        return {"src/zp100.ipp": src.replace("int f();\n", "int f();\n" + code + "\n")}

    cpp20 = "cpp20-profile/forbidden-features"
    cases.update({
        "co_await": (cpp20, ipp("task t() { co_await x; }")),
        "<coroutine>": (cpp20, ipp("#include <coroutine>")),
        "a module import": (cpp20, ipp("import std;")),
        "a module declaration": (cpp20, ipp("export module zp100;")),
        "<ranges>": (cpp20, ipp("#include <ranges>")),
        "a range view": (cpp20, ipp("auto v = std::views::iota(0, 4);")),
        "<format>": (cpp20, ipp("#include <format>")),
        "std::format": (cpp20, ipp("auto s = std::format(\"{}\", 1);")),
        "std::to_underlying": (cpp20, ipp("auto u = std::to_underlying(e);")),
        "std::expected in a library-level header": (cpp20, ipp("#include <expected>")),
        "if consteval": (cpp20, ipp("constexpr int g() { if consteval { return 1; } return 0; }")),
        "[[assume]]": (cpp20, ipp("void h(int x) { [[assume(x > 0)]]; }")),
        "deducing this": (cpp20, ipp("struct S { void m(this S& self); };")),
        "a size_t literal": (cpp20, ipp("auto n = 4uz;")),
        "#elifdef": (cpp20, ipp("#if A\n#elifdef B\n#endif")),
        "a feature-test macro": (cpp20, ipp("#if defined(__cpp_lib_span)\n#endif")),
        "<version>": (cpp20, ipp("#include <version>")),
        "is_constant_evaluated": (cpp20, ipp("bool b = std::is_constant_evaluated();")),
        "[[fallthrough]]": (cpp20, ipp("void k(int x) { switch (x) { case 1: [[fallthrough]]; default: break; } }")),
        "[[likely]] without a measurement": (cpp20, ipp("void l(int x) { if (x) [[likely]] { } }")),
        "char8_t": (cpp20, ipp("char8_t c{};")),
        "a u8 literal": (cpp20, ipp("const auto* s = u8\"x\";")),
        "<=> in a driver": (cpp20, ipp("auto operator<=>(const S&) const = default;")),
        "[[no_unique_address]] in a driver": (cpp20, ipp("struct T { [[no_unique_address]] E e; };")),
        "std::function in a driver": (cpp20, ipp("std::function<void()> cb;")),
        "<source_location> in a driver": (cpp20, ipp("#include <source_location>")),
        "an Error enum without [[nodiscard]]": ("cpp20-profile/nodiscard-error", {
            "inc/zp100_types.hpp": GOOD["inc/zp100_types.hpp"].replace("enum class [[nodiscard]] Error",
                                                                       "enum class Error")}),
        "a ChipError enum without [[nodiscard]]": ("cpp20-profile/nodiscard-error", {
            "inc/zp100_types.hpp": GOOD["inc/zp100_types.hpp"].replace("#endif\n",
                                                                       "enum class SpiError : uint8_t { A };\n#endif\n")}),
        "a Result without [[nodiscard]]": ("cpp20-profile/nodiscard-error", {
            "inc/zp100_types.hpp": GOOD["inc/zp100_types.hpp"].replace("struct [[nodiscard]] Result<void>",
                                                                       "struct Result<void>")}),
        "an inline requires-expression": ("cpp20-profile/inline-requires", ipp(
            "template <typename P> void d(P& p) { if constexpr (requires { p.DelayUs(1U); }) { p.DelayUs(1U); } }")),
        "a header that includes the Kconfig header": ("cpp20-profile/kconfig-leaf", {
            "inc/zp100.hpp": GOOD["inc/zp100.hpp"].replace("#include \"zp100_types.hpp\"\n",
                                                           "#include \"zp100_types.hpp\"\n#include \"zp100_kconfig.hpp\"\n")}),
        "a test target without CMAKE_CXX_EXTENSIONS OFF": ("cpp20-profile/cmake-extensions", {
            "CMakeLists.txt": GOOD["CMakeLists.txt"].replace("set(CMAKE_CXX_EXTENSIONS OFF)\n", "")}),
        "a standalone example that relies on the root": ("cpp20-profile/cmake-extensions", {
            "examples/host/CMakeLists.txt": "project(zp100_host_example LANGUAGES CXX)\n"
                                            "add_executable(zp100_host_example main.cpp)\n"}),
        "extensions switched on": ("cpp20-profile/cmake-extensions", {
            "tests/CMakeLists.txt": GOOD["tests/CMakeLists.txt"] + "set(CMAKE_CXX_EXTENSIONS ON)\n"}),
        "a target property switching extensions on": ("cpp20-profile/cmake-extensions", {
            "tests/CMakeLists.txt": GOOD["tests/CMakeLists.txt"] + "set_target_properties(zp100_tests PROPERTIES "
                                                                  "CXX_EXTENSIONS ON)\n"}),
    })
    for label, (check, changes) in cases.items():
        found = [f for f in run(changes) if f.check == check]
        if not found:
            failures.append(f"{label}: not reported by {check}")
    allowed = {
        "[[likely]] with a measurement": ipp("void l(int x) { if (x) [[likely]] { }  // measured: 12 % on M4F }"),
        "std::format in a string": ipp("const char* doc = \"std::format and co_await\";"),
        "u8 as a name": ipp("uint8_t u8 = 0; uint8_t v = u8;"),
        "the Kconfig header including the types": {},
        "a named detection concept": ipp("template <typename P> concept HasD = requires(P& p) { p.DelayUs(1U); };\n"
                                         "template <typename P> void d(P& p) { if constexpr (HasD<P>) { } }"),
    }
    for label, changes in allowed.items():
        found = [f for f in run(changes) if f.check.startswith("cpp20-profile/")]
        if found:
            failures.append(f"{label}: reported, but it is allowed: " + "; ".join(str(f) for f in found))
    lib = {".kokeb/handbook.yml": 'handbook: "1.0"\nkind: library\nlevel: high\n', "driver.yml": None,
           ".kokeb/template.yml": "name: zp100\n"}
    found = [f for f in run(dict(lib, **ipp("#include <compare>\nauto operator<=>(const S&) const = default;")))
             if f.check.startswith("cpp20-profile/")]
    if found:
        failures.append("a library is held to the driver-only C++20 checks: " + "; ".join(str(f) for f in found))
    library = run({".kokeb/handbook.yml": 'handbook: "1.0"\nkind: library\nlevel: high\n', "driver.yml": None,
                   ".kokeb/template.yml": "name: zp100\n", "inc/zp100.hpp": "#ifndef ZP100_HPP\n#define ZP100_HPP\n"
                   "int a;\n#endif\n"})
    if library:
        failures.append("a library is held to the driver checks: " + "; ".join(str(f) for f in library))
    for f in failures:
        print(f"::error::selftest: {f}")
    if failures:
        return 1
    print(f"selftest: {len(GUARDS)} guard names right, a clean repository passes, {len(cases)} seeded breaks reported, "
          f"{len(allowed) + 1} allowed forms pass")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scan", "guard", "selftest"])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--name", default=None, help="the repository's name, when driver.yml and .kokeb/template.yml "
                                                 "do not give it")
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    repo = Repo(pathlib.Path(a.repo).resolve(), a.name)
    if not repo.name:
        print("::error::source checks: no repository name (driver.yml `name`, .kokeb/template.yml `name` or --name)")
        return 2
    if a.cmd == "guard":
        for rel in a.paths:
            print(f"{rel}: {expected_guard(repo.name, rel)}")
        return 0
    findings = repo.scan()
    for f in findings:
        print(f)
    print(f"source checks: {len(findings)} finding(s) in {repo.root.name} ({repo.kind or 'unknown kind'}, "
          f"name {repo.name})")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
