"""Development correctness gate for the archived Rodinia 3.1 sources.

Does not run GPU code or publish performance results.
"""
from pathlib import Path
import difflib
import json
import struct
import sys

from bend_bench.core import append, execute, hash_file, write_json

ROOT = Path(__file__).resolve().parent
SOURCE = Path("/code/bend2/rodinia/rodinia_3.1")
WORK = ROOT / "runs/hotspot-development"
ASSETS = ROOT / "src/bend_bench/assets/gpu"
WORK.mkdir(exist_ok=True)


def run(command, **kwargs):
    result = execute(command, **kwargs)
    append(WORK / "development.jsonl", result)
    if result["returncode"]:
        raise RuntimeError(result["stderr"] or result["stdout"])
    return result


def values(result):
    return [struct.unpack("f", struct.pack("I", int(line)))[0] for line in result["stdout"].splitlines() if line]


def main():
    original = (SOURCE / "openmp/hotspot/hotspot_openmp.cpp").read_text()
    marker = "                    result[r*col+c] =temp[r*col+c]+ delta;"
    assert original.count(marker) == 1
    addition = """                    else {
                        delta = Cap_1 * (power[r*col+c] +
                            (temp[(r+1)*col+c] + temp[(r-1)*col+c] - 2.f*temp[r*col+c]) * Ry_1 +
                            (temp[r*col+c+1] + temp[r*col+c-1] - 2.f*temp[r*col+c]) * Rx_1 +
                            (amb_temp - temp[r*col+c]) * Rz_1);
                    }
"""
    patched = original.replace(marker, addition + marker)
    (WORK / "hotspot_openmp.cpp").write_text(patched)
    (WORK / "openmp-boundary.patch").write_text("".join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True), "original/hotspot_openmp.cpp", "patched/hotspot_openmp.cpp")))
    write_json(WORK / "sources.json", dict(
        archive="https://www.cs.virginia.edu/~skadron/lava/Rodinia/Packages/rodinia_3.1.tar.bz2",
        archive_sha256=hash_file("/code/bend2/sources/rodinia_3.1.tar.bz2"),
        source_files={str(p.relative_to(SOURCE)): hash_file(p) for p in SOURCE.rglob("*") if p.is_file()},
        adapter_sha256=hash_file(ASSETS / "hotspot-driver.cpp"),
        boundary_patch_sha256=hash_file(WORK / "openmp-boundary.patch")))
    flags = ["-O3", "-march=native", "-ffp-contract=off", "-fopenmp", f"-I{WORK}"]
    for name, extra in (("reference", ["-DHOTSPOT_REFERENCE"]), ("openmp", [])):
        run(["/usr/bin/g++", *flags, *extra, ASSETS / "hotspot-driver.cpp", "-o", WORK / name])
    run(["/usr/bin/g++", "-O3", "-march=native", "-ffp-contract=off", "-fopenmp",
         f"-I{SOURCE}/openmp/hotspot", ASSETS / "hotspot-audit.cpp", "-o", WORK / "original-audit"])
    audit = execute([WORK / "original-audit"])
    append(WORK / "development.jsonl", dict(stage="unmodified-openmp-counterfactual", **audit))
    if audit["returncode"] != 1 or "interior_tile_errors=0" not in audit["stdout"]:
        raise RuntimeError("Original-source counterfactual changed")
    for n in (64, 512, 1024):
        data = SOURCE / "data/hotspot"
        args = [n, 10, 1, data / f"temp_{n}", data / f"power_{n}"]
        reference = run([WORK / "reference", *args])
        actual = run([WORK / "openmp", *args])
        expected, observed = values(reference), values(actual)
        assert len(expected) == len(observed) == n*n
        error = max(abs(a-b) for a,b in zip(expected,observed))
        if any(abs(a-b)>0.0001+1e-6*abs(a) for a,b in zip(expected,observed)):
            raise RuntimeError(f"Patched OpenMP differs at size {n}: {error}")
        print(f"OpenMP {n}x{n}: all {n*n} values pass; max error {error}", flush=True)
        if n != 64:
            continue
        coefficients = run([WORK / "reference", n, "coeff"])["stdout"].split()
        literal = lambda value: value if any(c in value for c in ".eE") else value+".0"
        source = (ASSETS / "hotspot.bend").read_text().replace("Coeff{0.0, 0.0, 0.0, 0.0}", "Coeff{"+", ".join(map(literal,coefficients))+"}")
        source = source.replace('"temp.txt"', json.dumps(str(data / f"temp_{n}"))).replace('"power.txt"', json.dumps(str(data / f"power_{n}")))
        (WORK / "hotspot.bend").write_text(source)
        run(["/code/bend2/tools/bun-linux-x64/bun", "/code/bend2/upstream/bend2/main.ts", WORK / "hotspot.bend", "-o", WORK / "hotspot.c"])
        run(["/usr/bin/clang", "-O3", "-march=native", "-ffp-contract=off", WORK / "hotspot.c", "-lpthread", "-lm", "-o", WORK / "bend"])
        bend = values(run([WORK / "bend", "--gpu", "off", "--threads", "1"]))
        assert len(bend) == n*n
        error = max(abs(a-b) for a,b in zip(expected,bend))
        if any(abs(a-b)>0.0001+1e-6*abs(a) for a,b in zip(expected,bend)):
            raise RuntimeError(f"Bend differs: {error}")
        print(f"Bend {n}x{n}: full output passes; max error {error}", flush=True)


if __name__ == "__main__":
    main()
