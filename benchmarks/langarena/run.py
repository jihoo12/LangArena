#!/usr/bin/env python3
"""Validate and time twelve original LangArena workloads on the current host.

The runner lives in the LangArena checkout and reads a separate Jihoo checkout
(`--jihoo`, default `../jihoo`) for the compiler, its library and the memory
guard `scripts/proof-limits.sh`. See README.md for the partial coverage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES = (
    "Binarytrees::Obj", "Binarytrees::Arena", "Matmul::Single", "Etc::Sieve",
    "Sort::Quick", "Sort::Merge", "Sort::Self", "Hash::SHA256", "Hash::CRC32",
    "CLBG::Fannkuchredux", "CLBG::Mandelbrot", "CLBG::Spectralnorm",
)
C_SOURCES = (
    "helper.c", "benchmark.c", "binarytrees.c", "matmul1t.c", "sieve.c",
    "sort.c", "buffer_hash.c", "fannkuchredux.c", "mandelbrot.c", "spectralnorm.c",
)


def capture(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cpu_name():
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jihoo", type=Path, default=ROOT.parent / "jihoo")
    parser.add_argument("--langarena", type=Path, default=ROOT)
    parser.add_argument("--compiler", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "out/langarena")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--languages", nargs="+", default=["Jihoo", "C/Clang", "Rust", "Javascript/Node", "Python/PyPy"])
    args = parser.parse_args()
    if args.repeats < 1 or args.timeout < 1:
        parser.error("repeats and timeout must be positive")
    arena, jihoo = args.langarena.resolve(), args.jihoo.resolve()
    compiler = (args.compiler or jihoo / "out/jihoo-langa").resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    logs = output / "logs"
    logs.mkdir(exist_ok=True)
    original_configs = {kind: json.loads((arena / f"{kind}.js").read_text()) for kind in ("test", "run")}
    configs = {kind: {case["name"]: case for case in source if case["name"] in CASES}
               for kind, source in original_configs.items()}
    for kind, selected in configs.items():
        assert set(selected) == set(CASES), (kind, set(CASES) - set(selected))
        (output / f"{kind}.json").write_text(json.dumps(list(selected.values()), indent=2) + "\n")

    binaries = {"Jihoo": output / "jihoo", "C/Clang": output / "c-clang",
                "Rust": output / "rust/release/benchmarks"}
    flags = {"Jihoo": ["-O2", "--release"], "C/Clang": ["-O2", "-DNDEBUG", "-fstack-protector-strong", "-fno-omit-frame-pointer"],
             "Rust": ["cargo", "build", "--release", "--locked", "--jobs", "1"]}
    compiler_env = {**os.environ, "JIHOO_PATH": str(jihoo / "lib"), "JIHOO_CODEGEN_UNITS": "1"}
    build_commands = {
        "Jihoo": [str(compiler), "build", *flags["Jihoo"], str(HERE / "main.jh"), "-o", str(binaries["Jihoo"])],
        "C/Clang": ["clang", *flags["C/Clang"], "-Wall", "-Wextra", "-Wpedantic", "-Werror=return-type", "-Werror=address",
                    "-I", str(arena / "c/src"), str(HERE / "c-main.c"),
                    *(str(arena / "c/src" / source) for source in C_SOURCES), "-lyyjson", "-lm", "-pthread",
                    "-Wl,-z,relro,-z,now", "-Wl,--gc-sections", "-o", str(binaries["C/Clang"])],
        "Rust": [*flags["Rust"], "--manifest-path", str(arena / "rust/Cargo.toml"),
                 "--target-dir", str(output / "rust")],
    }
    report = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": platform.platform(), "cpu": cpu_name(),
        "affinity_cpu": min(os.sched_getaffinity(0)), "initial_load": os.getloadavg(),
        "jihoo_revision": capture(["git", "rev-parse", "HEAD"], cwd=jihoo),
        "langarena_revision": capture(["git", "rev-parse", "HEAD"], cwd=arena),
        "coverage": {"implemented": len(CASES), "upstream_total": len(original_configs["run"]),
                     "unported": [case["name"] for case in original_configs["run"] if case["name"] not in CASES]},
        "method": "Per-workload inner time; upstream warmup and checksum state; median of rotated fresh processes; one CPU; no Docker.",
        "flags": flags, "build_commands": build_commands, "compile_seconds": {},
        "versions": {}, "source_sha256": {}, "small_checks": {}, "samples": {}, "failures": [],
        "repeats": args.repeats, "languages": args.languages,
    }
    provenance = [HERE / "main.jh", HERE / "c-main.c", HERE / "run.py", jihoo / "flake.lock",
                  arena / "test.js", arena / "run.js", arena / "python/main.py", arena / "javascript/index.js"]
    provenance.extend(arena / "c/src" / source for source in C_SOURCES)
    provenance.extend(sorted((arena / "rust/src").rglob("*.rs")))
    for path in provenance:
        report["source_sha256"][str(path)] = digest(path)
    version_commands = {"Jihoo": [str(compiler), "--version"], "C/Clang": ["clang", "--version"],
                        "Rust": ["rustc", "--version"], "Javascript/Node": ["node", "--version"],
                        "Python/PyPy": ["pypy3", "--version"]}
    for language in args.languages:
        if language not in version_commands:
            parser.error(f"unknown language: {language}")
        report["versions"][language] = capture(version_commands[language])
        if language in build_commands and not args.skip_build:
            print(f"Building {language} (serialized memory guard)", flush=True)
            start = time.perf_counter()
            with (logs / f"build-{language.replace('/', '-')}.log").open("w") as log:
                subprocess.run([str(jihoo / "scripts/proof-limits.sh"), *build_commands[language]],
                               cwd=jihoo, env=compiler_env, stdout=log, stderr=subprocess.STDOUT, check=True)
            report["compile_seconds"][language] = time.perf_counter() - start

    def save():
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    def run(language, kind, case, repeat):
        config = configs[kind][case]
        if language == "Jihoo":
            warmup = config.get("warmup_iterations", max(int(config["iterations"] * 0.2), 1))
            size = next(config[field] for field in ("depth", "limit", "n", "w", "size") if field in config)
            command = [str(binaries[language]), case, str(config["iterations"]), str(warmup),
                       str(size), str(config.get("h", 0)), str(config["checksum"])]
        else:
            executable = {"Javascript/Node": ["node", str(arena / "javascript/index.js")],
                          "Python/PyPy": ["pypy3", str(arena / "python/main.py")]}
            command = executable.get(language, [str(binaries.get(language, ""))]) + [str(output / f"{kind}.json"), case]
        stem = f"{kind}-{case.replace('::', '-')}-{language.replace('/', '-')}-{repeat}"
        rss_path = logs / f"{stem}.rss"
        timed = [shutil.which("time"), "-f", "%M", "-o", str(rss_path), *command]
        cpu = report["affinity_cpu"]
        try:
            completed = subprocess.run(timed, cwd=ROOT, env=compiler_env, text=True, capture_output=True,
                                       timeout=args.timeout, preexec_fn=lambda: os.sched_setaffinity(0, {cpu}))
            (logs / f"{stem}.log").write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise ValueError(f"exit status {completed.returncode}: {completed.stderr[-500:]}")
            if language == "Jihoo":
                lines = completed.stdout.strip().splitlines()
                actual, nanos = map(int, lines)
                assert actual == config["checksum"], (actual, config["checksum"])
                seconds = nanos / 1e9
            else:
                result = re.search(re.escape(case) + r":\s+OK\s+in\s+([\d.]+)s", completed.stdout)
                if not result or "ERR[" in completed.stdout:
                    raise ValueError(f"no successful checksum result: {completed.stdout[-800:]}")
                seconds = float(result.group(1))
            rss = int(rss_path.read_text().strip()) / 1024
            return {"seconds": seconds, "peak_rss_mib": rss, "expected_checksum": config["checksum"]}
        except (subprocess.TimeoutExpired, ValueError, AssertionError) as error:
            failure = {"language": language, "kind": kind, "case": case, "repeat": repeat, "error": str(error)}
            report["failures"].append(failure)
            print(f"FAIL {language} {case}: {error}", flush=True)
            save()
            return None

    for case in CASES:
        report["small_checks"][case] = {}
        for language in args.languages:
            checked = run(language, "test", case, 0)
            report["small_checks"][case][language] = checked
        print(f"Small checksum: {case}", flush=True)
        save()
    if report["failures"]:
        print(f"Small checks failed; see {output / 'report.json'}", flush=True)
        return 1
    if args.check_only:
        print(f"PASS: {len(CASES)} workloads x {len(args.languages)} languages", flush=True)
        return 0

    for index, case in enumerate(CASES):
        report["samples"][case] = {language: [] for language in args.languages}
        for repeat in range(args.repeats):
            shift = (index + repeat) % len(args.languages)
            order = args.languages[shift:] + args.languages[:shift]
            for language in order:
                sample = run(language, "run", case, repeat)
                if sample:
                    report["samples"][case][language].append(sample)
                    print(f"{case} {language} [{repeat + 1}/{args.repeats}] {sample['seconds']:.6f}s", flush=True)
                save()
    if report["failures"]:
        print("Incomplete measurements; no aggregate ranking was computed.", flush=True)
        return 1

    medians = {case: {language: statistics.median(sample["seconds"] for sample in samples)
                      for language, samples in langs.items()} for case, langs in report["samples"].items()}
    report["medians"] = medians
    totals = {language: sum(medians[case][language] for case in CASES) for language in args.languages}
    report["ranking_by_total_seconds"] = sorted(totals.items(), key=lambda row: row[1])
    report["per_case_jihoo_rank"] = {case: 1 + sum(value < times["Jihoo"] for language, value in times.items() if language != "Jihoo")
                                     for case, times in medians.items()}
    report["geometric_mean_over_c"] = {language: statistics.geometric_mean(medians[case][language] / medians[case]["C/Clang"] for case in CASES)
                                       for language in args.languages} if "C/Clang" in args.languages else {}
    save()
    lines = ["# Local LangArena subset results", "", f"{report['date']} — {report['cpu']}", "",
             f"{len(CASES)}/{len(original_configs['run'])} workloads; {len(args.languages)} local configurations; {args.repeats} measurements per workload/configuration.",
             "This is a local subset ranking, not the official 27-language, 50-workload ranking.", "",
             "| Rank | Configuration | Sum of median runtimes (s) | Geometric mean time / C |", "| ---: | --- | ---: | ---: |"]
    for index, (language, total) in enumerate(report["ranking_by_total_seconds"], 1):
        ratio = report["geometric_mean_over_c"].get(language, float("nan"))
        lines.append(f"| {index} | {language} | {total:.4f} | {ratio:.3f} |")
    lines += ["", "| Workload | Jihoo (s) | C/Clang (s) | Jihoo / C | Jihoo rank |", "| --- | ---: | ---: | ---: | ---: |"]
    for case, times in medians.items():
        c = times.get("C/Clang", float("nan"))
        lines.append(f"| {case} | {times['Jihoo']:.6f} | {c:.6f} | {times['Jihoo'] / c:.3f} | {report['per_case_jihoo_rank'][case]}/{len(args.languages)} |")
    lines += ["", "All original small and production checksums passed for every included configuration.",
              "Preparation and warmup are excluded from the inner runtime. Peak RSS includes them.",
              "Bounds checks remain enabled. No PGO, native CPU flags, unsafe indexing or fast-math flags were added.",
              "Compilation times cover different source coverage (Rust builds its complete suite); they are not ranked.",
              "See report.json and logs/ for versions, source hashes, commands and raw samples.", ""]
    (output / "results.md").write_text("\n".join(lines))
    print("\n".join(lines[:15]), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
