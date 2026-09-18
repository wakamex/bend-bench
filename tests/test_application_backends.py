"""Real compiler checks; opt-in native/GPU smoke tests share the harness lock."""

import os
import json
import re
from pathlib import Path
import tempfile
import unittest

from bend_bench.applications import stage
from bend_bench.core import append, correct, execute, load_config
from bend_bench.experiment import prepare, measure
from bend_bench.suites import plan, stage as stage_all
from bend_bench.profiling import kernel_totals


class ApplicationBackends(unittest.TestCase):
    def config(self, output):
        config = load_config(Path(__file__).resolve().parents[1] / "applications.toml")
        config.update(
            output=str(output),
            label="application-development-smoke",
            pricing_depths=[8],
            pricing_steps=[16],
            bfs_depths=[6],
            mnk_games=[[3, 3, 3, 4]],
            threads=[1, 16],
        )
        return config

    def test_real_bend_source_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            config = self.config(work)
            stage(config, work)
            for source in sorted((work / "ports").glob("*.bend")):
                result = execute(
                    [
                        "taskset",
                        "-c",
                        str(config["cpus"][-1]),
                        "nice",
                        "-n",
                        "19",
                        config["tools"]["bun"],
                        Path(config["bend"]["path"]) / "bend2/main.ts",
                        source,
                        "-o",
                        source.with_suffix(".js"),
                    ]
                )
                self.assertEqual(
                    result["returncode"], 0, source.name + "\n" + result["stderr"]
                )
                result = execute(
                    [
                        "taskset",
                        "-c",
                        str(config["cpus"][-1]),
                        "nice",
                        "-n",
                        "19",
                        config["tools"]["bun"],
                        source.with_suffix(".js"),
                    ]
                )
                case = dict(
                    expected_vector=str(source.with_suffix(".json")),
                    implementation="bend-js",
                    contract=dict(
                        vector_kind="f32-bits"
                        if source.name.startswith("pricing")
                        else "u32",
                        abs_tolerance=0.002,
                        rel_tolerance=0.0001,
                    ),
                )
                self.assertTrue(
                    correct(case, result),
                    source.name
                    + "\n"
                    + result["stderr"]
                    + "\n"
                    + result["stdout"][:300],
                )

    @unittest.skipUnless(
        os.environ.get("BEND_BENCH_APP_NATIVE") == "1",
        "Opt-in real CPU/CUDA correctness checks",
    )
    def test_real_native_backends(self):
        root = Path(__file__).resolve().parents[1]
        config = self.config(root / "runs")
        prepare(config)
        run, failed = measure(config, checking=True)
        self.assertFalse(failed, str(run))
        # Correct output can come from CPU evaluation before an offload seam.
        # Require actual kernels from the BFS GPU entry point as well.
        case = next(c for c in json.loads((run / "plan.json").read_text())["cases"]
                    if c["suite"] == "bfs" and c["implementation"] == "bend-cuda")
        folder = Path(tempfile.mkdtemp(prefix="bfs-offload-", dir=run))
        stem = folder / "trace"
        nsys = "/usr/local/cuda-13.1/bin/nsys"
        result = execute([nsys, "profile", "--trace=cuda", "--sample=none", "--cpuctxsw=none",
                          "-o", stem, *case["command"]], gpu_policy=config)
        append(folder / "evidence.jsonl", result)
        output = "\n".join(line for line in result["stdout"].splitlines() if re.fullmatch(r"\d+", line))
        self.assertTrue(correct(case, {**result, "stdout": output}))
        database = stem.with_suffix(".sqlite")
        exported = execute([nsys, "export", "--type=sqlite", "-o", database, str(stem) + ".nsys-rep"])
        append(folder / "evidence.jsonl", exported)
        self.assertEqual(exported["returncode"], 0)
        self.assertGreater(kernel_totals(database)["kernel_launches"], 0)

    def test_real_baseline_source_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            config = self.config(work)
            stage_all(config, work)
            builds, _ = plan(config, work)
            for command in builds:
                if not any(str(x).endswith((".cpp", ".cu")) for x in command):
                    continue
                output = command.index("-o")
                argv = [*command[:output], *command[output + 2 :], "-fsyntax-only"]
                argv = [x for x in argv if not str(x).endswith(".o")]
                result = execute(
                    [
                        "taskset",
                        "-c",
                        str(config["cpus"][-1]),
                        "nice",
                        "-n",
                        "19",
                        *argv,
                    ]
                )
                folder = Path(__file__).resolve().parents[1] / "runs"
                folder.mkdir(exist_ok=True)
                append(folder / "application-source-checks.jsonl", result)
                errors = "\n".join(
                    line for line in result["stderr"].splitlines() if "error:" in line
                )
                self.assertEqual(
                    result["returncode"], 0, " ".join(argv) + "\n" + errors
                )


if __name__ == "__main__":
    unittest.main()
