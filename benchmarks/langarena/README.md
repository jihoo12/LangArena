# Local LangArena comparison

This is a Jihoo port of **12 of LangArena's 50 workloads**, with a runner that
compares Jihoo, C/Clang, Rust, JavaScript/Node and Python/PyPy on the same host.
It reports a **local subset ranking**, not Jihoo's position in the official
27-language, 50-workload table. The other 38 workloads have not been ported here.

The [recorded run](results.md) on an i7-12700 (one CPU, three repetitions)
places Jihoo third of five by total runtime: Rust 13.691 s, C/Clang 14.394 s,
Jihoo 15.201 s, JavaScript/Node 32.784 s and Python/PyPy 53.258 s. Jihoo's
sum is 5.6% above C; its equal-workload geometric mean time/C ratio is 1.016.
The [raw results](sample-results.json) retain all 180 production samples and
the 60 successful small-input checks. Jihoo wins the object-tree and Fannkuch
workloads; merge sort and matrix multiplication are slower than C in this run.

The fixed selection covers two binary-tree representations, single-threaded
matrix multiplication, the sieve of Eratosthenes, quick/merge/library sorting,
both buffer hashes, Fannkuch, Mandelbrot and spectral norm. It omits ecosystem
workloads (JSON, CSV, regex and Base64), threaded matrix variants and the other
algorithms. Do not extrapolate this selection to full-suite performance.

## Reproduce

This directory lives in a checkout of [LangArena](https://github.com/kostya/LangArena).
The runner reads that checkout's files directly and does not edit its
implementations or configurations. It also needs a Jihoo checkout for the
compiler, its library and the memory guard `scripts/proof-limits.sh`; select it
with `--jihoo PATH`, which defaults to `../jihoo`.

The recorded run used LLVM/Clang, Rust/Cargo, Node, PyPy, yyjson and uthash in
addition to Jihoo's default toolchain; provide them on `PATH`. From the
LangArena repository root:

```sh
mkdir -p out/logs ../jihoo/out/logs
../jihoo/scripts/proof-limits.sh nix develop ../jihoo -c \
  jihoo build -O2 ../jihoo/compiler/main.jh -o ../jihoo/out/jihoo-langa \
  > out/logs/langa-compiler-build.log 2>&1
nix shell nixpkgs#clang nixpkgs#rustc nixpkgs#cargo nixpkgs#nodejs nixpkgs#pypy3 \
  nixpkgs#uthash nixpkgs#yyjson -c \
  python3 benchmarks/langarena/run.py --jihoo ../jihoo --repeats 3
```

The runner wraps **every compiler invocation** in the Jihoo checkout's
`scripts/proof-limits.sh`, including C and Rust compilation. Jihoo uses one code
generation unit. Builds are serialized, with the Jihoo repository's memory
ceilings; its `flake.lock` pins the compiler toolchain.
Cargo uses the upstream lockfile. Dependency fetching precedes measurement.

`--check-only` runs all small correctness inputs without production timings.
`--skip-build` reuses binaries already in the output directory. `--languages`
selects configurations; use the default five to reproduce the recorded ranking.
The timeout is per process (`--timeout`, default 300 seconds).

Artifacts go under `out/langarena/`: `report.json` records source revisions,
source hashes, versions, commands, checksums, raw samples, memory and failures;
`results.md` summarizes the results; `logs/` keeps each build and execution.
The generated configs retain exactly the selected upstream `test.js` and
`run.js` entries, including their original input sizes, iteration counts and
expected checksums.

## Measurement and implementation details

- Each process runs one workload, on one allowed CPU chosen at startup.
  Preparation and the original warmup happen before the inner measurement.
  Measurement order rotates across configurations for every workload/repetition.
- The same state survives warmup, including its accumulated checksum. The
  pseudo-random generator starts at 42 for preparation and resets to 42 before
  the measured iterations, exactly as in LangArena. This detail affects hashes
  and sorting and must not be replaced with a fresh post-warmup benchmark.
- Every original small checksum must pass before production measurement.
  Every measured process must also pass its original production checksum.
  Failures or timeouts suppress the aggregate ranking rather than dropping
  the failed workloads from the denominator.
- The runtime rank sorts the **sum of per-workload median inner runtimes**,
  following LangArena's total-runtime comparison. The additional geometric
  mean time/C ratio weights each workload equally. These are distinct metrics.
  This runner does not compute LangArena's normalized 0–100 score.
- Peak RSS includes preparation and warmup, as it measures the complete process.
  C, Rust, Node and PyPy report inner times to three decimal places; Jihoo uses
  `CLOCK_MONOTONIC` nanoseconds. Small-test timings are not used for ranking.
- Jihoo uses `-O2 --release`, retaining bounds checks and using wrapping integer
  arithmetic; the checksum calculations also use explicit wrapping operators.
  C uses the upstream safe O2 flags and Rust its upstream release profile.
  No PGO, CPU-specific flags, fast math or unchecked array indexing are added.
- `main.jh` implements the algorithms in Jihoo using standard `Vec`, `Box` and
  sorting. C interoperation supplies only a clock and the upstream float
  checksum's `snprintf("%.7f")` formatting. `Hash::SHA256` deliberately retains
  LangArena's custom eight-lane hash; it is not cryptographic SHA-256.
- The C adapter only registers the chosen factories; its algorithm and harness
  sources are compiled directly from the supplied LangArena checkout. Rust,
  JavaScript and PyPy use their original runners and implementations.
- Rust compiles its full suite whereas Jihoo and C compile the selected
  workloads. Compilation is recorded for provenance and is **not ranked**.
  Expressiveness and official normalized runtime scores are not ranked either.
- Execution is local without Docker. Absolute times from LangArena's published
  Ryzen host must not be mixed with measurements from this host. These results
  do not validate the dependent kernel or resume its paused formal-proof task.

The workload algorithms derive from LangArena, copyright (c) 2026 Konstantin
Makarchev, under the MIT license retained in [UPSTREAM-LICENSE](UPSTREAM-LICENSE).
