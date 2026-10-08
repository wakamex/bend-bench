from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import tomllib
import unittest

from bend_bench import ml
from bend_bench.core import load_config

ROOT = Path(__file__).resolve().parents[1]


class Sources(unittest.TestCase):
    def test_bendhub_imports_become_vendored_paths(self):
        text = "import Base\nimport bend-ml-tensor-array@0.1.3.0/main.bend as TA\nimport ./load.bend as L\n"
        self.assertEqual(ml.relink(text, "../../pkg"),
                         "import Base\nimport ../../pkg/tensor-array/main.bend as TA\nimport ./load.bend as L\n")
        with self.assertRaises(ValueError):
            ml.relink("import bend-ml-unknown@1.0/main.bend as U\n", "..")

    def test_compute_marker_times_one_line(self):
        text = "import Base\n\ndef main() -> IO(Unit):\n  do IO<Unit>:\n    r : F32 <- IO.pure(F32, f())\n    IO.print(F32.show(r))\n"
        out = ml.compute_marker(text, "    r : F32 <- IO.pure(F32, f())", "test")
        self.assertIn("    t_begin : Nat <- IO.now()\n    r : F32 <- IO.pure(F32, f())\n    t_end : Nat <- IO.now()\n"
                      "    bench_report(t_begin, t_end)\n", out)
        self.assertLess(out.index("def bench_report"), out.index("def main"))
        with self.assertRaises(ValueError):
            ml.compute_marker(text, "    missing line", "test")

    def test_nanogpt_port_has_only_nanogpt_sizes(self):
        source = ml.nano_source((ml.VENDORED / "demos/gpt2/fast.bend").read_text())
        for size in ("768", "2304", "3072", "50257", "1024", "12n"):
            self.assertNotRegex(source, rf"\b{size}\b")
        for text in ("TA.Mat<1152n, 384n>", "TA.Mat<65n, 384n>", "attn(6n", "load_layers(6n", '"demos/nanogpt/w/"', "bench_report"):
            self.assertIn(text, source)

    def test_batch_program_forks_prebuilt_handles(self):
        source = ml.nano_batch_source((ml.VENDORED / "demos/gpt2/fast.bend").read_text())
        self.assertEqual(source.count("def bench_report("), 1)
        self.assertEqual(source.count("def main() -> IO(Unit):"), 1)
        self.assertIn("batch!(d, model", source)
        self.assertIn("generations(handles(d, m), ids, n)", source)
        self.assertNotRegex(source, r"@[A-Z]+@")

    def test_pytorch_mnist_gains_cuda_and_the_compute_marker(self):
        checkout = Path("/code/bend-ml")
        if not (checkout / ".git").exists():
            self.skipTest("bend-ml checkout unavailable")
        text = subprocess.run(["git", "-C", checkout, "show", f"{ml.BEND_ML_COMMIT}:reference/mnist_torch.py"], capture_output=True,
                              check=True, text=True).stdout
        source = ml.mnist_torch_source(text)
        compile(source, "mnist_bench.py", "exec")
        for line in ('ap.add_argument("--cuda"', 'device="cuda" if a.cuda else "cpu"', "EVAL_COMPUTE_SECONDS="):
            self.assertIn(line, source)

    def test_seeded_weights_are_the_pinned_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            ml.nano_weights(Path(tmp))
            self.assertEqual((Path(tmp) / "wte.bin").stat().st_size, 65 * 384 * 4)
            with self.assertRaises(ValueError):
                ml.nano_weights(Path(tmp), seed=1)

    def test_vendored_files_match_the_pinned_commit(self):
        checkout = Path("/code/bend-ml")
        if not (checkout / ".git").exists():
            self.skipTest("bend-ml checkout unavailable")
        for path in sorted(p for p in ml.VENDORED.rglob("*") if p.is_file()):
            rel = path.relative_to(ml.VENDORED).as_posix()
            pinned = subprocess.run(["git", "-C", checkout, "show", f"{ml.BEND_ML_COMMIT}:{rel}"], capture_output=True, check=True).stdout
            self.assertEqual(path.read_bytes(), pinned, rel)


class Correctness(unittest.TestCase):
    def check(self, kind, contract, reference, stdout):
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "ref.json"
            ref.write_text(json.dumps(reference))
            case = dict(ml_kind=kind, ml_reference=str(ref), contract=contract)
            return ml.correct(case, dict(returncode=0, timeout=False, stdout=stdout))

    def test_generation_matches_ids_and_logits_per_repetition(self):
        ref = dict(generated=[3, 4], logits=[1.5, -2.25])
        good = "  id 3  logit 1.5  pos 1  t=5ms\n  id 4  logit -2.2500004  pos 2\n"
        contract = dict(logit_tolerance=1e-3, repetitions=2)
        self.assertTrue(self.check("nanogpt", contract, ref, good * 2))
        self.assertFalse(self.check("nanogpt", contract, ref, good))
        self.assertFalse(self.check("nanogpt", contract, ref, good + good.replace("id 4", "id 5")))
        self.assertFalse(self.check("nanogpt", contract, ref, good + good.replace("1.5", "1.51")))

    def test_mnist_and_products(self):
        ref = dict(train_loss=0.520477, test_correct=9128)
        contract = dict(loss_tolerance=1e-4, correct_tolerance=2)
        self.assertTrue(self.check("mnist", contract, ref, "epoch 1 train_loss=0.5204771 test_correct=9129/10000 train_seconds=7.1"))
        self.assertTrue(self.check("mnist", contract, ref, "torch\nepoch 1 train_loss=0.520477 test_acc=0.9128 seconds=0.2"))
        self.assertFalse(self.check("mnist", contract, ref, "epoch 1 train_loss=0.5206 test_correct=9129/10000"))
        self.assertFalse(self.check("mnist", contract, ref, "epoch 1 train_loss=0.5204771 test_correct=9140/10000"))
        products = dict(mm_array=12544098.0, mv=1000.0)
        self.assertTrue(self.check("mm_array", {}, products, "12544098.0"))
        self.assertFalse(self.check("mm_array", {}, products, "12544099.0"))
        self.assertTrue(self.check("mv", dict(rel_tolerance=1e-4), products, "1000.05"))
        self.assertFalse(self.check("mv", dict(rel_tolerance=1e-4), products, "1000.2"))


class Configuration(unittest.TestCase):
    def test_ml_suite_needs_its_sources_and_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ml.toml"
            base = 'schema = 1\nsuites = ["ml"]\n[bend]\npath = "."\ncommit = "' + "0" * 40 + '"\n'
            path.write_text(base)
            with self.assertRaisesRegex(ValueError, "bend_ml"):
                load_config(path)
            path.write_text(base + '[bend_ml]\npath = "."\ncommit = "' + "0" * 40 + '"\n[ml_data]\npath = "."\n')
            with self.assertRaisesRegex(ValueError, "python_ml"):
                load_config(path)
            path.write_text('cuda = true\n' + base + '[bend_ml]\npath = "."\ncommit = "' + "0" * 40 + '"\n[ml_data]\npath = "."\n'
                            '[tools]\npython_ml = "/usr/bin/python3"\n')
            with self.assertRaisesRegex(ValueError, "python_ml_cuda"):
                load_config(path)
            path.write_text('ml_workloads = ["gpt3"]\n' + base + '[bend_ml]\npath = "."\ncommit = "' + "0" * 40 + '"\n[ml_data]\npath = "."\n')
            with self.assertRaisesRegex(ValueError, "ml_workloads"):
                load_config(path)


class Plan(unittest.TestCase):
    def cases(self, cuda):
        cases = []
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bend-ml").mkdir()
            (Path(tmp) / "bend-ml/gpt2.json").write_text(json.dumps(dict(prompt_ids=[1, 2])))
            config = dict(threads=[1, 16], cuda=cuda, gpu_heap="8GB", bend_ml=dict(commit="0" * 40),
                          ml_workloads=["nanogpt-batch", "mnist"], tools=dict(python_ml="/cpu/python", python_ml_cuda="/cuda/python"))

            def case(suite, workload, implementation, threads, binary, args, expected, reason=None, contract=None):
                cases.append(dict(id=f"{suite}/{workload}/{implementation}/{threads}", suite=suite, workload=workload,
                                  command=[str(binary), *map(str, args)], unsupported=reason, contract=contract))
            ml.plan(config, Path(tmp), case, cases, lambda source, name, gpu=False: f"/build/{name}", None)
        return {c["id"]: c for c in cases}

    def test_the_batch_runs_on_four_implementations_at_the_most_threads(self):
        cases = self.cases(cuda=True)
        self.assertEqual(sorted(cases), ["ml/mnist/bend/1", "ml/mnist/bend/16", "ml/mnist/pytorch-cuda/16", "ml/mnist/pytorch/1",
                                         "ml/mnist/pytorch/16", "ml/nanogpt-batch/bend-cuda/16", "ml/nanogpt-batch/bend/16",
                                         "ml/nanogpt-batch/pytorch-cuda/16", "ml/nanogpt-batch/pytorch/16"])
        self.assertEqual(cases["ml/nanogpt-batch/bend-cuda/16"]["command"][0], "/build/ml-nanogpt-batch-cuda")
        self.assertEqual(cases["ml/nanogpt-batch/bend-cuda/16"]["command"][-2:], ["--gpu", "8GB"])
        self.assertEqual(cases["ml/nanogpt-batch/bend/16"]["command"][-2:], ["--gpu", "off"])
        self.assertEqual(cases["ml/nanogpt-batch/pytorch-cuda/16"]["command"][0], "/cuda/python")
        self.assertEqual(cases["ml/nanogpt-batch/pytorch-cuda/16"]["command"][-3:], ["--batch", "1024", "--cuda"])
        batch = cases["ml/nanogpt-batch/bend/16"]
        self.assertEqual((batch["ml_kind"], batch["contract"]["repetitions"]), ("nanogpt", 1024))
        self.assertTrue(batch["ml_reference"].endswith("nanogpt.json"))

    def test_without_cuda_only_cpu_cases(self):
        self.assertFalse([name for name in self.cases(cuda=False) if "cuda" in name])


class FastNanoGPT(unittest.TestCase):
    def test_built_program_matches_the_reference(self):
        config = tomllib.loads((ROOT / "fast-gpu.toml").read_text())
        bun = (ROOT / config["tools"]["bun"]).resolve()
        bend = (ROOT / config["bend"]["path"]).resolve()
        if not bun.exists() or not (bend / "bend2/main.ts").exists() or not shutil.which("clang"):
            self.skipTest("Bend checkout, bun or clang unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            ml.stage_fast(work)
            folder = work / ml.FAST
            source = folder / "demos/nanogpt/nano.bend"
            subprocess.run([bun, bend / "bend2/main.ts", source, "-o", work / "nano.c"], check=True, capture_output=True)
            subprocess.run(["clang", "-std=c11", "-O3", work / "nano.c", "-lpthread", "-lm", "-o", work / "nano"], check=True, capture_output=True)
            result = subprocess.run([work / "nano", "--threads", "1", ml.NANO_PROMPT, str(ml.NANO_TOKENS), "1"], cwd=folder,
                                    capture_output=True, text=True, timeout=120)
            self.assertIn("EVAL_COMPUTE_SECONDS=", result.stderr)
            case = dict(ml_kind="nanogpt", ml_reference=str(ml.ASSETS / "nanogpt-reference.json"),
                        contract=dict(logit_tolerance=1e-3, repetitions=1))
            self.assertTrue(ml.correct(case, dict(stdout=result.stdout)))


if __name__ == "__main__":
    unittest.main()
