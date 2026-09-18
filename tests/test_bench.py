import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from bend_bench.core import append, correct, environment, exclusive, execute, fingerprint, hash_file, load_config, provenance, repository, service_state, write_json
from bend_bench.experiment import artifacts, compare, measure, prepare, report, summarize, validate
from bend_bench.suites import plan, stage, vendor_outputs


class CoreTests(unittest.TestCase):
    def test_entrypoints(self):
        for command in ([sys.executable, "-m", "bend_bench", "--help"], ["bend-bench", "--help"]):
            result = execute(command)
            self.assertEqual(result["returncode"], 0, result)
            self.assertIn("prepare", result["stdout"])

    def test_real_process_validation_and_timeout(self):
        case = {"expected_regex": "42"}
        result = execute([sys.executable, "-c", "print(42)"], measured=True)
        self.assertTrue(correct(case, result))
        self.assertIsNotNone(result["host_peak_rss_kb"])
        self.assertFalse(correct(case, execute([sys.executable, "-c", "print(41)"])))
        result = execute([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.03)
        self.assertTrue(result["timeout"])
        self.assertFalse(correct(case, result))

    def test_exclusive_lock(self):
        with exclusive({}):
            with self.assertRaisesRegex(ValueError, "Another"):
                with exclusive({}):
                    self.fail("Second lock admitted")

    def test_real_git_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            def git(*args):
                return subprocess.check_output(["git", "-C", tmp, *args], text=True).strip()
            git("init", "-q")
            (path / "source").write_text("before\n")
            git("add", "source")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            spec = dict(path=tmp, commit=git("rev-parse", "HEAD"))
            before = repository(spec)
            (path / "source").write_text("after\n")
            with self.assertRaisesRegex(ValueError, "allow_patch"):
                repository(spec)
            after = repository({**spec, "allow_patch": True})
            self.assertNotEqual(fingerprint(before), fingerprint(after))
            self.assertIn("+after", after["patch"])
            (path / "patch.diff").write_text(after["patch"] + "\n")
            git("apply", "--check", "--reverse", "patch.diff")
            with self.assertRaisesRegex(ValueError, "untracked"):
                repository(spec)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.case = dict(id="vendor/test/bend/1", contract={"input": "fixed"}, implementation="bend", threads=1, unsupported=None)
        self.evidence = dict(config={"repetitions": 10, "warmups": 1}, host={"cpu": "test"})
        write_json(self.run / "provenance.json", self.evidence)
        write_json(self.run / "plan.json", {"cases": [self.case]})
        write_json(self.run / "prepared.json", {"fingerprint": "abc", "plan_sha256": hash_file(self.run / "plan.json")})

    def row(self, phase, rep, ok=True, seconds=1):
        append(self.run / "samples.jsonl", dict(fingerprint="abc", case=self.case["id"], phase=phase, rep=rep,
                                                correct=ok, end_to_end_seconds=seconds, host_peak_rss_kb=100))

    def complete(self):
        self.row("check", 0, seconds=999)
        self.row("warmup", 0, seconds=999)
        for i in range(10):
            self.row("measure", i, seconds=i + 1)

    def test_warmups_and_gate(self):
        self.assertEqual(summarize(self.run)["cases"][0]["status"], "pending")
        self.complete()
        row = summarize(self.run)["cases"][0]
        self.assertEqual(row["status"], "passed")
        self.assertEqual(row["end_to_end_seconds"], 5.5)
        self.assertIsNone(row["kernel_seconds"])
        self.assertTrue(report(self.run).is_file())

    def test_failure_never_becomes_timing(self):
        self.complete()
        self.row("measure", 10, ok=False)
        row = summarize(self.run)["cases"][0]
        self.assertEqual(row["status"], "failed")
        self.assertIsNone(row["end_to_end_seconds"])

    def test_duplicate_and_foreign_identity_rejected(self):
        self.row("check", 0)
        self.row("check", 0)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize(self.run)
        append(self.run / "samples.jsonl", dict(fingerprint="foreign"))
        with self.assertRaisesRegex(ValueError, "Mixed"):
            summarize(self.run)

    def test_unsupported(self):
        self.case["unsupported"] = "No compatible GPU"
        write_json(self.run / "plan.json", {"cases": [self.case]})
        (self.run / "prepared.json").unlink()
        self.assertEqual(summarize(self.run)["cases"][0]["status"], "unsupported")

    def test_comparison_contract_and_host(self):
        self.complete()
        with tempfile.TemporaryDirectory() as other:
            after = Path(other) / "after"
            shutil.copytree(self.run, after)
            self.assertEqual(compare(self.run, after)["comparisons"][0]["before_over_after"], 1)
            modified = copy.deepcopy(self.evidence)
            modified["host"]["cpu"] = "different"
            write_json(after / "provenance.json", modified)
            self.assertEqual(compare(self.run, after)["comparisons"][0]["reason"], "host changed")

    def test_binary_mutation_rejected(self):
        work = self.run / "work"
        (work / "build").mkdir(parents=True)
        binary = work / "build/program"
        binary.write_bytes(b"original")
        write_json(self.run / "prepared.json", dict(artifacts=artifacts(work), libraries={}, plan_sha256=hash_file(self.run / "plan.json")))
        validate({}, self.run, self.evidence)
        binary.write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "binaries changed"):
            validate({}, self.run, self.evidence)


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class RunnerIntegrationTests(unittest.TestCase):
    def test_real_build_check_measure_resume(self):
        # A tiny real C program tests the runner without launching a benchmark workload.
        with tempfile.TemporaryDirectory() as tmp:
            config = dict(output=tmp, repetitions=10, warmups=1, timeout=10, blocked_services=[])
            evidence = dict(config=config, sources={}, host={"test": True})

            def staging(config, work):
                (work / "build").mkdir(parents=True)
                (work / "build/main.c").write_text('#include <stdio.h>\nint main(void) { puts("42"); return 0; }\n')

            def planning(config, work):
                binary = work / "build/main"
                builds = [["cc", "-O3", str(work / "build/main.c"), "-o", str(binary)]]
                cases = [dict(id="test/constant/c/1", contract={"expected": "42"}, implementation="c", threads=1,
                              command=[str(binary)], env={}, expected_regex="42", unsupported=None)]
                return builds, cases

            with patch("bend_bench.experiment.provenance", return_value=evidence), patch("bend_bench.experiment.stage", staging), patch("bend_bench.experiment.plan", planning):
                run = prepare(config)
                with self.assertRaisesRegex(ValueError, "Missing correctness"):
                    measure(config)
                self.assertFalse(measure(config, checking=True)[1])
                self.assertFalse(measure(config)[1])
                saved = (run / "samples.jsonl").read_bytes()
                self.assertFalse(measure(config)[1])
                self.assertEqual(saved, (run / "samples.jsonl").read_bytes())
                self.assertEqual(summarize(run)["cases"][0]["status"], "passed")
                self.assertEqual(len(saved.splitlines()), 12)
                self.assertEqual(prepare(config), run)
                evidence["host"]["changed"] = True
                with self.assertRaisesRegex(ValueError, "No preparation"):
                    measure(config)


WORKSPACE = Path(__file__).resolve().parents[2] / "bend2"


@unittest.skipUnless((WORKSPACE / "upstream/bend2/main.ts").exists(), "Archived evaluation workspace unavailable")
class AcceptanceTests(unittest.TestCase):
    def config(self):
        return load_config(Path(__file__).resolve().parents[1] / "experiment.toml")

    def test_all_vendor_contracts_against_real_outputs(self):
        config = self.config()
        self.assertEqual(len(vendor_outputs(config["bend"]["path"])), 16)
        _, cases = plan(config, Path("/tmp/bend-bench-plan-only"))
        contracts = {c["workload"]: c for c in cases if c["suite"] == "vendor" and c["implementation"] == "bend"}
        real = [json.loads(line) for line in (WORKSPACE / "results/smoke.jsonl").read_text().splitlines()]
        seen = set()
        for row in real:
            if row.get("correct") and row["mode"].startswith("bend-"):
                self.assertTrue(correct(contracts[row["bench"]], row))
                seen.add(row["bench"])
        self.assertEqual(seen, set(contracts))

    def test_real_provenance_is_stable(self):
        config = self.config()
        self.assertEqual(provenance(config), provenance(config))

    def test_uts_contracts_against_real_outputs(self):
        _, cases = plan(self.config(), Path("/tmp/bend-bench-plan-only"))
        cases = {c["implementation"]: c for c in cases if c["suite"] == "uts" and c["workload"] == "test" and c["threads"] == 1}
        real = [json.loads(line) for line in (WORKSPACE / "results/uts-smoke.jsonl").read_text().splitlines()]
        self.assertTrue(correct(cases["bend"], real[0]))
        self.assertTrue(correct(cases["serial-c"], real[1]))
        wrong = {**real[1], "stdout": real[1]["stdout"].replace("4112897", "4112896")}
        self.assertFalse(correct(cases["serial-c"], wrong))

    def test_staged_baselines_and_uts(self):
        config = self.config()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            stage(config, work)
            builds, cases = plan(config, work)
            self.assertTrue(builds)
            self.assertEqual(len(list((work / "baselines").glob("*-omp.c"))), 15)
            source = (work / "ports/uts-test.bend").read_text()
            self.assertIn("root(42)", source)
            self.assertIn("U32.to_nat(1000000)", source)
            uts = next(c for c in cases if c["suite"] == "uts" and c["implementation"] == "bend")
            self.assertTrue(correct(uts, dict(returncode=0, timeout=False, stdout="4112897 0\n")))
            self.assertFalse(correct(uts, dict(returncode=0, timeout=False, stdout="4112897 1\n")))

    def test_active_legacy_service_is_a_gate(self):
        config = self.config()
        if service_state("bend2-evaluation.service") != "active":
            self.skipTest("Legacy service no longer active")
        result = execute(["bend-bench", "prepare", Path(__file__).resolve().parents[1] / "experiment.toml"], env=os.environ.copy())
        self.assertEqual(result["returncode"], 2)
        self.assertIn("no overlapping", result["stderr"])


if __name__ == "__main__":
    unittest.main()
