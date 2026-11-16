# Local LangArena subset results

2026-11-16T12:51:52+0900 — 12th Gen Intel(R) Core(TM) i7-12700

12/50 workloads; 5 local configurations; 3 measurements per workload/configuration.
This is a local subset ranking, not the official 27-language, 50-workload ranking.

| Rank | Configuration | Sum of median runtimes (s) | Geometric mean time / C |
| ---: | --- | ---: | ---: |
| 1 | Rust | 13.6910 | 0.900 |
| 2 | C/Clang | 14.3940 | 1.000 |
| 3 | Jihoo | 15.2007 | 1.016 |
| 4 | Javascript/Node | 32.7840 | 2.301 |
| 5 | Python/PyPy | 53.2580 | 3.409 |

| Workload | Jihoo (s) | C/Clang (s) | Jihoo / C | Jihoo rank |
| --- | ---: | ---: | ---: | ---: |
| Binarytrees::Obj | 1.388423 | 1.865000 | 0.744 | 1/5 |
| Binarytrees::Arena | 0.363741 | 0.338000 | 1.076 | 3/5 |
| Matmul::Single | 4.283770 | 3.031000 | 1.413 | 4/5 |
| Etc::Sieve | 1.425853 | 1.562000 | 0.913 | 2/5 |
| Sort::Quick | 1.124597 | 1.022000 | 1.100 | 3/5 |
| Sort::Merge | 1.701438 | 0.959000 | 1.774 | 3/5 |
| Sort::Self | 0.787707 | 1.647000 | 0.478 | 2/5 |
| Hash::SHA256 | 0.857479 | 0.672000 | 1.276 | 3/5 |
| Hash::CRC32 | 0.825450 | 0.815000 | 1.013 | 2/5 |
| CLBG::Fannkuchredux | 0.893248 | 0.986000 | 0.906 | 1/5 |
| CLBG::Mandelbrot | 0.759212 | 0.745000 | 1.019 | 2/5 |
| CLBG::Spectralnorm | 0.789803 | 0.752000 | 1.050 | 3/5 |

All original small and production checksums passed for every included configuration.
Preparation and warmup are excluded from the inner runtime. Peak RSS includes them.
Bounds checks remain enabled. No PGO, native CPU flags, unsafe indexing or fast-math flags were added.
Compilation times cover different source coverage (Rust builds its complete suite); they are not ranked.
See [sample-results.json](sample-results.json) for versions, source hashes, commands and all raw samples.
Raw process logs remain in `out/langarena/logs/` on the measurement host.
