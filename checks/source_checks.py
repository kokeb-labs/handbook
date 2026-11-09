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
        page = {"KB-CPP": "cpp"}.get(self.rule[:6], "cpp")
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

    def scan(self) -> list[Finding]:
        self.check_include_guards()
        self.check_bus_requirements()
        self.check_raw_access()
        return self.findings


# -- self-test ---------------------------------------------------------------------------------------------------
GOOD = {
    ".kokeb/handbook.yml": 'handbook: "1.0"\nkind: driver\nlevel: high\n',
    "driver.yml": "name: zp100\nversion: 0.1.0\nbus: [spi]\n",
    "inc/zp100.hpp": "/** @file zp100.hpp */\n#ifndef ZP100_HPP\n#define ZP100_HPP\n#include \"zp100_types.hpp\"\n"
                     "class Zp100 {\n public:\n  int ReadRegister(int a);\n  int GetLastReply() const;\n};\n"
                     "#if defined(X)\nint x;\n#endif\n#endif // ZP100_HPP\n",
    "inc/zp100_types.hpp": "#ifndef ZP100_TYPES_HPP\n#define ZP100_TYPES_HPP\n// #pragma once in a comment is fine\n"
                           "const char* s = \"#pragma once\";\n#endif\n",
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
    for label, (check, changes) in cases.items():
        found = [f for f in run(changes) if f.check == check]
        if not found:
            failures.append(f"{label}: not reported by {check}")
    library = run({".kokeb/handbook.yml": 'handbook: "1.0"\nkind: library\nlevel: high\n', "driver.yml": None,
                   ".kokeb/template.yml": "name: zp100\n", "inc/zp100.hpp": "#ifndef ZP100_HPP\n#define ZP100_HPP\n"
                   "int a;\n#endif\n"})
    if library:
        failures.append("a library is held to the driver checks: " + "; ".join(str(f) for f in library))
    for f in failures:
        print(f"::error::selftest: {f}")
    if failures:
        return 1
    print(f"selftest: {len(GUARDS)} guard names right, a clean repository passes, {len(cases)} seeded breaks reported")
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
