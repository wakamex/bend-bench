"""Explicit Rodinia boundary fix and generated input/output contracts."""
import difflib
import json
from pathlib import Path
import sys

from .core import execute, hash_file, write_json


def stage_rodinia(source, work):
    original = (source / "openmp/hotspot/hotspot_openmp.cpp").read_text()
    marker = "                    result[r*col+c] =temp[r*col+c]+ delta;"
    if original.count(marker) != 1:
        raise ValueError("Rodinia boundary patch target changed")
    addition = """                    else {
                        delta = Cap_1 * (power[r*col+c] +
                            (temp[(r+1)*col+c] + temp[(r-1)*col+c] - 2.f*temp[r*col+c]) * Ry_1 +
                            (temp[r*col+c+1] + temp[r*col+c-1] - 2.f*temp[r*col+c]) * Rx_1 +
                            (amb_temp - temp[r*col+c]) * Rz_1);
                    }
"""
    patched = original.replace(marker, addition + marker)
    (work / "gpu/hotspot_openmp.cpp").write_text(patched)
    (work / "gpu/openmp-boundary.patch").write_text("".join(difflib.unified_diff(
        original.splitlines(True), patched.splitlines(True), "original/hotspot_openmp.cpp", "patched/hotspot_openmp.cpp")))


def generate(work, n, steps, source):
    reference = work / "build/hotspot-reference"
    data = source / "data/hotspot"
    args = [reference, n, steps, 1, data / f"temp_{n}", data / f"power_{n}"]
    result = execute(args)
    if result["returncode"] or len(result["stdout"].split()) != n*n:
        raise ValueError("HotSpot scalar reference failed")
    output = work / "ports" / f"hotspot-{n}-{steps}.bits"
    output.write_text(result.pop("stdout"))
    coefficients = execute([reference, n, "coeff"])
    if coefficients["returncode"]:
        raise ValueError("HotSpot coefficient generation failed")
    values = coefficients["stdout"].split()
    if len(values) != 4:
        raise ValueError("Expected four HotSpot coefficients")
    literal = lambda value: value if any(c in value for c in ".eE") else value + ".0"
    port = (work / "gpu/hotspot.bend").read_text()
    for old, new in (("Coeff{0.0, 0.0, 0.0, 0.0}", "Coeff{"+", ".join(map(literal, values))+"}"),
                     ("solve!(10n,", f"solve!({steps}n,"),
                     ("load_grid(6n, 6n,", f"load_grid({n.bit_length()-1}n, {n.bit_length()-1}n,"),
                     ('"temp.txt"', json.dumps(str(data / f"temp_{n}"))),
                     ('"power.txt"', json.dumps(str(data / f"power_{n}")))):
        if port.count(old) != 1:
            raise ValueError(f"HotSpot port template changed: {old}")
        port = port.replace(old, new)
    output.with_suffix(".bend").write_text(port)
    write_json(output.with_suffix(".json"), dict(reference=result, coefficients=coefficients,
               expected_sha256=hash_file(output), size=n, steps=steps))


if __name__ == "__main__":
    generate(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4]))
