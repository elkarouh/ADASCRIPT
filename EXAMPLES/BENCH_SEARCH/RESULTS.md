# bench_search: Adascript on someone else's benchmark

`bench_search.ady` is a translation of `bench.py`, from the performance
tests of [ais](https://github.com/Anode1/ais), an associative index engine
written in C. Those tests time the two operations that engine spends its time
on, in five languages with one algorithm each:

- **scan**: count the lines of an 80 MB store that contain a substring
  (`--find`);
- **intersect**: merge the two largest posting lists, sorted integer files,
  and count the ids in both (a multi-key `get`).

Their sources and their own results, which this page follows:

| | |
|---|---|
| [`tests/perf/`](https://github.com/Anode1/ais/tree/main/tests/perf) | the directory |
| [`bench.py`](https://github.com/Anode1/ais/blob/main/tests/perf/bench.py), [`bench.c`](https://github.com/Anode1/ais/blob/main/tests/perf/bench.c), [`bench.rs`](https://github.com/Anode1/ais/blob/main/tests/perf/bench.rs), [`Bench.java`](https://github.com/Anode1/ais/blob/main/tests/perf/Bench.java), [`bench.adb`](https://github.com/Anode1/ais/blob/main/tests/perf/bench.adb) | the same algorithm in five languages |
| [`gen.py`](https://github.com/Anode1/ais/blob/main/tests/perf/gen.py) | the seeded data generator |
| [`lang_bench.sh`](https://github.com/Anode1/ais/blob/main/tests/perf/lang_bench.sh) | their driver |
| [`LANG_COMPARISON.md`](https://github.com/Anode1/ais/blob/main/tests/perf/LANG_COMPARISON.md) | their results and analysis |

`bench_search.ady` takes the same command line as theirs (`find STORE WORD`,
`and LIST_A LIST_B`) and prints the same lines, so their driver's method
applies unchanged. Like theirs, it reads and parses its input before the
clock starts and times one pass over data in memory.

## What is different from their data and their machine

- **The data is regenerated, not theirs.** `gen.py` reads `/home/vas/kul` (a
  home directory of paths) and `/usr/share/dict/words`, and neither is here.
  `prepare.sh` runs their generator, unmodified, against a stand-in word list
  (6,000 seeded pronounceable words) and the files under `/usr/lib` as the
  value paths. The shape is theirs: 1,000,000 records, 1 or 2 Zipf-drawn keys
  each, and the two largest posting lists hold 270,304 and 132,570 ids, 21,894
  in common (theirs: 270,011, 132,637, 21,923). The store is **39.7 MB, not
  80.9 MB**, because these value paths are shorter. The index itself is built
  by ais's own C engine (`ais -y --compact`), as in their script.
- **The substring is `std`** (227,036 of the 1,000,000 lines match; theirs was
  `Outputs`, 379,090). A scan reads the whole store either way.
- **The machine is not theirs.** A shared 4-core Linux container, no Ada
  compiler (`gnatmake` is absent, so the Ada rows are missing). Each row is
  the **median of 10 process launches**, each pinned to one core with
  `taskset`, over the warm in-process iterations (the first of each launch is
  dropped). C here scans 40 MB in 59–65 ms where their i7 scans 81 MB in
  50 ms, so compare ratios, not absolute times.
- **Adascript prints every timing to a tenth of a millisecond** (`{:7.1f}`,
  the same on both backends). An earlier draft of this page printed whole
  milliseconds by truncating, which turned the Nim merge's 1.7 ms into "1"
  and made it look faster than C; the numbers below are from the tenth-ms
  output.

Files are text in Adascript (a `str`), not bytes as in their Python; that is
the one difference in what is being searched.

## Results

Milliseconds, median. "Library way" is what a program would write (a
substring `count`, a set `&`); "hand loop" is the explicit algorithm the other
languages use (a scan of the lines, a two-pointer merge).

| | scan, library way | scan, hand loop | merge, hand loop | set intersection |
|---|---:|---:|---:|---:|
| C `-O2` | | 64.5 | 1.6 | |
| C `-O3` | | 65.0 | 1.7 | |
| Rust `-O2` | | 59.0 | 1.8 | |
| Java (warm) | | 82.0 | 1.8 | |
| Python (their `bench.py`) | 33.0 | 191.5 | 96.5 | 11.5 |
| **Adascript → Python** | 32.8 | 61.5 | 64.8 | 10.7 |
| **Adascript → Nim, default build** (`ady2nim c`) | 35.7 | 87.9 | 4.0 | 80.3 |
| **Adascript → Nim, `-d:release`** | **29.4** | **54.1** | **1.7** | 18.8 |

C, Rust and Java have one loop each, so one column: their "scan" row is the
hand loop and their "merge" row is the merge. Their Python has both, as
Adascript's does.

## Reading it

- **Build for release.** `ady2nim c` alone gives an unoptimised Nim build,
  with checks on: 4.0 ms on the merge and 80 ms on the hash-set
  intersection. `ady2nim c -d:release` gives **1.7 ms** and 19 ms, and
  `-d:danger` (checks off) is no different. Before timing anything, delete
  the built binary and rebuild: the up-to-date check does not notice a
  change of compiler flags, and even `-f` did not force it, so a
  `-d:release` build here was more than once silently a stale default one.
- **The release build matches C on the merge**: 1.7 ms against 1.6–1.8 for
  C and Rust. It is not faster; range-checked `Natural` counters cost
  nothing measurable (1.6–1.8 ms with `Natural` or `int`).
- **The scan is faster than the C and Rust loops**, but for a different
  algorithm: the store is split into lines before the clock starts, and the
  timed loop is `word in line` over them (54 ms), or a single `count` over
  the whole text (29 ms). The C and Rust loops walk the bytes once and split
  as they go. Same answer, not the same work.
- **On the Python backend, Adascript's hand loops are 2–3× faster than their
  Python's** (scan 61.5 against 192 ms, merge 65 against 97 ms). Both
  are CPython; theirs counts with a generator expression per line and
  compares bytes, ours is a loop with `+=` over text. This was not chased
  further.
- **The hash-set intersection is the weak spot on Nim**: 19 ms release, 80 ms
  default, against CPython's 11–12 ms. It is the one row where the native
  build loses to the interpreter. The emitted code is Nim's own `a * b`
  (Adascript adds nothing), and a stand-alone profile of it, release build,
  on the same two lists says where the time goes:

  | | ms |
  |---|---:|
  | `a * b` on string sets | 18.9 |
  | iterate the smaller set, probe the larger, count only | 16.2 |
  | hash the smaller set's 132,570 strings, nothing else | 4.3 |
  | `a * b` on **integer** sets, the same ids | **5.7** (CPython's: 6.4) |

  Nim already iterates the smaller set, and hashing is about a fifth of the
  time (CPython hashes a string once, when it is put in a set). The cost is
  the string keys, which are separate heap objects to fetch and compare on
  every probe: the same table on integers is faster than CPython's. The
  fix, if it matters, is integer sets, not a different hash function.

## Reproducing it

```sh
git clone https://github.com/Anode1/ais ~/ais
sh prepare.sh /tmp/bench_search_data          # ~2.5 min: the data and the index

D=/tmp/bench_search_data/data
B=/tmp/bench_search_build; mkdir -p $B; P=~/ais/tests/perf
cc -O2 -o $B/bench_c2 $P/bench.c
cc -O3 -o $B/bench_c3 $P/bench.c
rustc -C opt-level=2 -C strip=symbols $P/bench.rs -o $B/bench_rust
javac -d $B $P/Bench.java

ady2nim c -f EXAMPLES/BENCH_SEARCH/bench_search.ady
cp EXAMPLES/BENCH_SEARCH/bench_search $B/bench_ady_nim_default
ady2nim c -f -d:release EXAMPLES/BENCH_SEARCH/bench_search.ady
cp EXAMPLES/BENCH_SEARCH/bench_search $B/bench_ady_nim_release
ady2py EXAMPLES/BENCH_SEARCH/bench_search.ady > $B/bench_ady.py

python3 run_bench.py $D $B                    # LAUNCHES=2 for a quick look
```

`bench_search` can also be run by hand: `bench_search find STORE WORD` and
`bench_search and LIST_A LIST_B`, where the lists are files under
`$D/idx/idx/`.
