#!/usr/bin/env python3
"""run_bench.py -- run the benchmarks the way tests/perf/lang_bench.sh does.

    python3 run_bench.py DATA_DIR BUILD_DIR [SUBSTRING]

DATA_DIR is what prepare.sh made; BUILD_DIR holds the built programs, named
as below. Each program is launched LAUNCHES times, pinned to one core; the
first in-process iteration of each launch (the cold one) is dropped, and the
median of the rest is printed per output label.
"""
import os, re, statistics, subprocess, sys

data, build = sys.argv[1], sys.argv[2]
sub = sys.argv[3] if len(sys.argv) > 3 else "std"
LAUNCHES = int(os.environ.get("LAUNCHES", 10))
perf = os.environ.get("AIS_PERF", os.path.expanduser("~/ais/tests/perf"))

# the two largest posting lists, and the store, read once to warm the cache
sizes = sorted(((os.path.getsize(os.path.join(d, f)), os.path.join(d, f))
                for d, _, fs in os.walk(os.path.join(data, "idx")) for f in fs),
               reverse=True)
k1, k2 = sizes[0][1], sizes[1][1]
store = os.path.join(data, "store")
for p in (store, k1, k2):
    open(p, "rb").read()

b = lambda name: os.path.join(build, name)
impls = {
    "C -O2":                   [b("bench_c2")],
    "C -O3":                   [b("bench_c3")],
    "Rust -O2":                [b("bench_rust")],
    "Java":                    ["java", "-cp", build, "Bench"],
    "Python (theirs)":         ["python3", os.path.join(perf, "bench.py")],
    "Adascript -> Nim default": [b("bench_ady_nim_default")],
    "Adascript -> Nim release": [b("bench_ady_nim_release")],
    "Adascript -> Python":     ["python3", b("bench_ady.py")],
}
env = dict(os.environ, JAVA_TOOL_OPTIONS="")
line = re.compile(r"(\S+)\s+iter(\d+)\s+([\d.]+) ms")
for name, cmd in impls.items():
    for op, args in (("scan", ["find", store, sub]), ("and", ["and", k1, k2])):
        samples = {}
        for _ in range(LAUNCHES):
            out = subprocess.run(["taskset", "-c", "1"] + cmd + args,
                                 capture_output=True, text=True, env=env).stdout
            for ln in out.splitlines():
                m = line.match(ln)
                if m and int(m.group(2)) >= 1:
                    samples.setdefault(m.group(1), []).append(float(m.group(3)))
        print(f"{name:26} {op:5}",
              {k: round(statistics.median(v), 2) for k, v in samples.items()})
