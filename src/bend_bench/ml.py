"""Machine-learning workloads from bend-ml (https://github.com/nuxyel/bend-ml, MIT, Renan Vinicius).

A reduced copy of the pinned bend-ml checkout is staged in work/ml, so its Bend programs and
PyTorch scripts run with their own relative paths. Two kinds of text edit are applied, each
asserted to match exactly once: BendHub imports become relative imports of the packages vendored
from the same checkout (the network plays no part), and each Bend program reports its timed
region on stderr as EVAL_COMPUTE_SECONDS. References are computed during preparation, never
inside a timed sample:

- gpt2: GPT-2 small (124 M) greedy generation, demos/gpt2/fast.bend; reference bend-ml's
  reference/gpt2_ref.py (full recompute per token), baseline a PyTorch forward with a KV cache.
- nanogpt: nanoGPT's shakespeare-char sizes (6 layers, 6 heads, 384 wide, 65 characters),
  generated from fast.bend with seeded weights from Python's standard library; reference and
  baseline as for gpt2 (the reference recomputes the full context per token).
- mnist: one epoch of a 784-128-10 MLP, demos/mnist/fast.bend against reference/mnist_torch.py.
- mm_array, mv: bend-ml's bench/ products: 128,000 dot products of 784 elements over Array<F32>,
  and 101 products of a 768 vector with a 2304 x 768 matrix.
"""
import array
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys

from .core import hash_file

ASSETS = Path(__file__).parent / "assets/ml"

# Public inputs, pinned by content (Hugging Face openai-community/gpt2, and the MNIST mirror
# bend-ml's setup.sh downloads from).
DATA = {
    "gpt2/model.safetensors": "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707",
    "gpt2/vocab.json": "196139668be63f3b5d6574427317ae82f612a97c5d1cdaf36ed2256dbf636783",
    "gpt2/merges.txt": "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
    "mnist/train-images-idx3-ubyte": "ba891046e6505d7aadcbbe25680a0738ad16aec93bde7f9b65e87a2fc25776db",
    "mnist/train-labels-idx1-ubyte": "65a50cbbf4e906d70832878ad85ccda5333a97f0f4c3dd2ef09a8a9eef7101c5",
    "mnist/t10k-images-idx3-ubyte": "0fa7898d509279e482958e8ce81c8e77db3f2f8254e26661ceb7762c4d494ce7",
    "mnist/t10k-labels-idx1-ubyte": "ff7bcfd416de33731a308c3f266cc351222c34898ecbeaf847f06e48f7ec33f2",
}
PACKAGES = {"bend-ml-tensor": "tensor", "bend-ml-tensor-array": "tensor-array",
            "bend-ml-nat-lemmas": "nat-lemmas", "bend-ml-bpe-tokenizer": "bpe"}
WORKLOADS = ("gpt2", "nanogpt", "mnist", "mm_array", "mv")
GPT2_PROMPT, GPT2_TOKENS = "The capital of France is", 24
NANO_PROMPT, NANO_TOKENS, NANO_REPS = "ROMEO:", 24, 10
NANO_VOCAB = "\n !$&',-.3:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
NANO = dict(layers=6, heads=6, width=384, vocab=65, context=256)
MV = dict(KN=768, MN=2304, REPS=100, PAR=0)
# The seeded weights, every tensor in nano_tensors() order: the vendored reference
# (assets/ml/nanogpt-reference.json) holds only for these bytes.
NANO_WEIGHTS_SHA256 = "07915cb787d3b56289bf01a5a4bb2a373be065aa8924e8cd2666e07afd3eef4a"
VENDORED = ASSETS / "bend-ml"  # bend-ml at BEND_ML_COMMIT: what nanogpt needs, for the fast profile
BEND_ML_COMMIT = "91fc6dd3f2bb147238480fc764057548acd6c40f"


def replace_once(text, old, new, where):
    if text.count(old) != 1:
        raise ValueError(f"bend-ml source changed ({where}): {old[:60]!r}")
    return text.replace(old, new)


def relink(text, pkg):
    """BendHub imports of bend-ml's own packages become imports of the vendored copies."""
    def sub(m):
        if m[1] not in PACKAGES:
            raise ValueError(f"Unknown BendHub package {m[1]}")
        return f"import {pkg}/{PACKAGES[m[1]]}/main.bend as {m[2]}"
    return re.sub(r"^import (bend-ml-[a-z-]+?)@[0-9.]+/main\.bend as (\w+)$", sub, text, flags=re.M)


REPORT = """
# bend-bench: the timed region's seconds, on stderr
def bench_report(+a: Nat, +b: Nat) -> IO(Unit):
  IO.print_err("EVAL_COMPUTE_SECONDS=" ++ Nat.show(Nat.div(Nat.sub(b, a), 1000n)) ++ "." ++ Nat.show(Nat.div(Nat.mod(Nat.sub(b, a), 1000n), 100n)) ++ Nat.show(Nat.div(Nat.mod(Nat.sub(b, a), 100n), 10n)) ++ Nat.show(Nat.mod(Nat.sub(b, a), 10n)))
"""


def compute_marker(text, line, where):
    """Times `line` (an exact line of a do block) and reports it on stderr as EVAL_COMPUTE_SECONDS,
    through bench_report, which goes after the file's imports."""
    indent = re.match(r" *", line)[0]
    text = replace_once(text, line + "\n", f"{indent}t_begin : Nat <- IO.now()\n{line}\n{indent}t_end : Nat <- IO.now()\n"
                        f"{indent}bench_report(t_begin, t_end)\n", where)
    imports = list(re.finditer(r"^import .*\n", text, re.M))
    return text[:imports[-1].end()] + REPORT + text[imports[-1].end():]


# ----------------------------------------------------------------------------------------------
# nanoGPT from fast.bend


def nano_source(fast):
    """bend-ml's demos/gpt2/fast.bend at nanoGPT's shakespeare-char sizes, characters in place of
    the BPE tokenizer, run repeatedly from position 0 so positions stay short."""
    start = fast.index("def selb(b: Bool")
    model = fast.index("# ---------------------------------------------------------------------\n# model")
    gen = fast.index("# ---------------------------------------------------------------------\n# main program")
    body = fast[:start] + fast[model:gen]
    marks = [("50257n", "@V"), ("2304n", "@QKV"), ("3072n", "@MLP"), ("1536n", "@TWOD"), ("1024n", "@CTX"),
             ("768n", "@D"), ("768.0", "@DF"), ("attn(12n", "@ATTN"), ("load_layers(12n", "@LL")]
    for old, mark in marks:
        if old not in body:
            raise ValueError(f"fast.bend changed: {old}")
        body = body.replace(old, mark)
    d, L = NANO["width"], NANO["layers"]
    for mark, new in [("@V", f"{NANO['vocab']}n"), ("@QKV", f"{3 * d}n"), ("@MLP", f"{4 * d}n"), ("@TWOD", f"{2 * d}n"),
                      ("@CTX", f"{NANO['context']}n"), ("@DF", f"{d}.0"), ("@D", f"{d}n"), ("@ATTN", f"attn({NANO['heads']}n"),
                      ("@LL", f"load_layers({L}n")]:
        body = body.replace(mark, new)
    body = (body.replace("one row of 768 numbers", f"one row of {d} numbers")
            .replace("(768 -> 3072)", f"({d} -> {4 * d})").replace("q (768), k (768), v (768)", f"q ({d}), k ({d}), v ({d})"))
    if re.search(r"\b(768|2304|3072|50257|1024)\b", body):
        raise ValueError("fast.bend has a GPT-2 size the nanoGPT port does not translate")
    body = body.replace("import bend-ml-bpe-tokenizer@0.1.2.0/main.bend as BPE\n", "").replace("import ./tok.bend as K\n", "")
    if body.count('"demos/gpt2/data/w/"') != 2:
        raise ValueError("fast.bend changed: its two weight paths")
    body = body.replace('"demos/gpt2/data/w/"', '"demos/nanogpt/w/"')
    body = re.sub(r"\A(#.*\n)+", "# nanoGPT shakespeare-char sizes over bend-ml's demos/gpt2/fast.bend (bend_bench/ml.py).\n"
                  "#   nano \"prompt\" n_tokens [repetitions]\n", body)
    main = (ASSETS / "nanogpt-main.bend").read_text().replace("@KV@", f"{L}n").replace("@VOCAB@", json.dumps(NANO_VOCAB))
    text = body.rstrip("\n") + "\n" + main
    return compute_marker(text, "    reps(k, ids_of(String.to_list(prompt)), n, SM{St{Nil{}, 0n, 0n, Nil{}, 0n, Nil{}}, model})", "nanogpt")


def nano_tensors():
    d, L = NANO["width"], NANO["layers"]
    std, proj = 0.02, 0.02 / math.sqrt(2 * L)  # nanoGPT's initialisation scales the residual projections
    yield "wte", (NANO["vocab"], d), std
    yield "wpe", (NANO["context"], d), std
    for i in range(L):
        for name, shape, how in (("ln1_g", (d,), "ones"), ("ln1_b", (d,), "zeros"), ("aw", (3 * d, d), std),
                                 ("ab", (3 * d,), "zeros"), ("pw", (d, d), proj), ("pb", (d,), "zeros"),
                                 ("ln2_g", (d,), "ones"), ("ln2_b", (d,), "zeros"), ("fw", (4 * d, d), std),
                                 ("fb", (4 * d,), "zeros"), ("mw", (d, 4 * d), proj), ("mb", (d,), "zeros")):
            yield f"h{i}.{name}", shape, how
    yield "lnf_g", (d,), "ones"
    yield "lnf_b", (d,), "zeros"


def nano_weights(out, seed=1337):
    """Seeded weights, uniform with nanoGPT's standard deviations; standard library only."""
    rand = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    for name, shape, how in nano_tensors():
        n = math.prod(shape)
        if how in ("ones", "zeros"):
            values = array.array("f", [1.0 if how == "ones" else 0.0]) * n
        else:
            a = how * math.sqrt(3)
            values = array.array("f", (rand.uniform(-a, a) for _ in range(n)))
        if sys.byteorder != "little":
            values.byteswap()
        with open(out / f"{name}.bin", "wb") as f:
            values.tofile(f)
        digest.update((out / f"{name}.bin").read_bytes())
    if digest.hexdigest() != NANO_WEIGHTS_SHA256:
        raise ValueError("Seeded nanoGPT weights differ from the pinned ones (Python's random module changed?)")


def stage_nano(fast_bend, folder, pkg):
    """nano.bend and its weights; folder/demos/nanogpt, packages at folder/pkg."""
    target = folder / "demos/nanogpt"
    target.mkdir(parents=True, exist_ok=True)
    (target / "nano.bend").write_text(relink(nano_source(fast_bend.read_text()), pkg))
    shutil.copy2(fast_bend.parent / "load.bend", target / "load.bend")
    (target / "load.bend").write_text(relink((target / "load.bend").read_text(), pkg))
    nano_weights(folder / "demos/nanogpt/w")


def vendor_packages(checkout, folder, names=tuple(PACKAGES.values())):
    for name in names:
        (folder / "pkg" / name).mkdir(parents=True, exist_ok=True)
        (folder / "pkg" / name / "main.bend").write_text(relink((checkout / name / "main.bend").read_text(), ".."))
        shutil.copy2(checkout / name / "LICENSE", folder / "pkg" / name / "LICENSE")


FAST = "ports/nanogpt"  # the fast CPU profile's nanoGPT tree, inside the work directory


def stage_fast(work):
    """The fast CPU profile's nanoGPT, from the vendored bend-ml subset."""
    folder = work / FAST
    vendor_packages(VENDORED, folder, ("tensor", "tensor-array", "nat-lemmas"))
    stage_nano(VENDORED / "demos/gpt2/fast.bend", folder, "../../pkg")


def plan_fast(work, bend_build, case, cases, contract):
    binary = bend_build(work / FAST / "demos/nanogpt/nano.bend", "nanogpt")
    for threads in (1, 16):
        case("cpu-regression", "nanogpt", "bend", threads, binary, [NANO_PROMPT, NANO_TOKENS, NANO_REPS, "--threads", threads, "--gpu", "off"],
             "", contract=dict(contract, workload="nanogpt-shakespeare-char-greedy", prompt=NANO_PROMPT, tokens=NANO_TOKENS,
                               repetitions=NANO_REPS, sizes=NANO, bend_ml=BEND_ML_COMMIT, logit_tolerance=1e-3,
                               reference=hash_file(ASSETS / "nanogpt-reference.json")))
        cases[-1].update(cwd=FAST, ml_kind="nanogpt", ml_reference=str(ASSETS / "nanogpt-reference.json"))


# ----------------------------------------------------------------------------------------------
# staging


def stage(config, work):
    checkout, data = Path(config["bend_ml"]["path"]), Path(config["ml_data"]["path"])
    python = config["tools"]["python_ml"]
    for rel, want in DATA.items():
        if hash_file(data / rel) != want:
            raise ValueError(f"ML data file differs from its pinned content: {data / rel}")
    ml = work / "bend-ml"
    ml.mkdir(exist_ok=True)
    vendor_packages(checkout, ml)
    shutil.copytree(checkout / "reference", ml / "reference", dirs_exist_ok=True)
    shutil.copy2(checkout / "LICENSE", ml / "LICENSE")
    # GPT-2: his program, his data layout, his preparation
    g = ml / "demos/gpt2"
    g.mkdir(parents=True, exist_ok=True)
    (g / "data").mkdir(exist_ok=True)
    for name in ("load.bend", "tok.bend", "unicode.bend"):
        (g / name).write_text(relink((checkout / "demos/gpt2" / name).read_text(), "../../pkg"))
    fast = relink((checkout / "demos/gpt2/fast.bend").read_text(), "../../pkg")
    fast = compute_marker(fast, "        st : St <- loop(Nat.add(List.length(&2, Nat, ids), Nat.sub(n, 1n)), t0ms, SM{St{List.replicate(KV, 12n, KV{Nil{}, Nil{}}), t0, 0n, qt, n, Nil{}}, model})",
                          "gpt2 generation")
    (g / "fast.bend").write_text(fast)
    # bend-ml's preparation writes 1.5 GB derived from the pinned files; it runs once into a cache
    # beside them, keyed by the preparation scripts and the inputs, and each run links to it.
    key = hashlib.sha256("".join(hash_file(ml / "reference" / f) for f in ("gpt2_prep.py", "bpe_ref.py")).encode()
                         + "".join(DATA[f"gpt2/{n}"] for n in ("model.safetensors", "vocab.json", "merges.txt")).encode()).hexdigest()[:16]
    cache = data / ".prepared" / f"gpt2-{key}"
    if not (cache / "complete").exists():
        shutil.rmtree(cache, ignore_errors=True)
        (cache / "tree/demos/gpt2/data").mkdir(parents=True)
        shutil.copytree(ml / "reference", cache / "tree/reference")
        for name in ("model.safetensors", "vocab.json", "merges.txt"):
            link(data / "gpt2" / name, cache / "tree/demos/gpt2/data" / name)
        run([python, "reference/gpt2_prep.py"], cache / "tree")
        run([python, "reference/gpt2_prep.py", "--split"], cache / "tree")
        (cache / "complete").write_text("")
    shutil.rmtree(g / "data")
    link(cache / "tree/demos/gpt2/data", g / "data")
    reference = run([python, "reference/gpt2_ref.py", GPT2_PROMPT, str(GPT2_TOKENS)], ml)
    write_reference(ml / "gpt2.json", reference, prompt_ids=re.search(r"^prompt_ids (\[.*\])", reference, re.M)[1])
    # nanoGPT
    stage_nano(checkout / "demos/gpt2/fast.bend", ml, "../../pkg")
    ids = " ".join(str(NANO_VOCAB.index(c)) for c in NANO_PROMPT)
    reference = run([python, str(ASSETS / "gpt_torch.py"), "demos/nanogpt/w", str(NANO["layers"]), str(NANO["heads"]),
                     ids, str(NANO_TOKENS), "1", "1", "--recompute"], ml)
    write_reference(ml / "nanogpt.json", reference, prompt_ids=json.dumps([int(x) for x in ids.split()]))
    # MNIST
    m = ml / "demos/mnist"
    (m / "data").mkdir(parents=True, exist_ok=True)
    mnist = relink((checkout / "demos/mnist/fast.bend").read_text(), "../../pkg")
    mnist = compute_marker(mnist, "        r : St2 <- tloop(nb, 0, lr, 0.0, St2{0.0, pm})", "mnist epoch")
    (m / "fast.bend").write_text(mnist)
    for name in ("train-images-idx3-ubyte", "train-labels-idx1-ubyte", "t10k-images-idx3-ubyte", "t10k-labels-idx1-ubyte"):
        link(data / "mnist" / name, m / "data" / name)
    torch_mnist = (ml / "reference/mnist_torch.py").read_text()
    torch_mnist = replace_once(torch_mnist, "        dt = time.time() - t0\n",
                               "        dt = time.time() - t0\n        print(f\"EVAL_COMPUTE_SECONDS={dt:.6f}\", file=sys.stderr)\n", "mnist_torch")
    torch_mnist = replace_once(torch_mnist, "import argparse, os, time\n", "import argparse, os, sys, time\n", "mnist_torch")
    (ml / "reference/mnist_bench.py").write_text(torch_mnist)
    run([python, "reference/mnist_torch.py", "--make-init", "--epochs", "1", "--max-batches", "1"], ml)
    reference = run([python, "reference/mnist_torch.py", "--epochs", "1", "--threads", "1"], ml)
    loss, acc = re.search(r"^epoch 1 train_loss=([\d.]+) test_acc=([\d.]+)", reference, re.M).groups()
    (ml / "mnist.json").write_text(json.dumps(dict(train_loss=float(loss), test_correct=round(float(acc) * 10000))))
    # the two products
    b = ml / "bench"
    b.mkdir(exist_ok=True)
    mm = (checkout / "bench/mm_array.bend").read_text()
    mm = replace_once(mm, "    IO.print(F32.show(many(128000n, 0.0, dot([0.5 : F32*1024n], [0.25 : F32*1024n]))))",
                      "    r : F32 <- IO.pure(F32, many(128000n, 0.0, dot([0.5 : F32*1024n], [0.25 : F32*1024n])))\n"
                      "    IO.print(F32.show(r))", "mm_array")
    mm = compute_marker(mm, "    r : F32 <- IO.pure(F32, many(128000n, 0.0, dot([0.5 : F32*1024n], [0.25 : F32*1024n])))", "mm_array")
    (b / "mm_array.bend").write_text(mm)
    mv = relink((checkout / "bench/mv.bend").read_text(), "../pkg")
    for key, value in MV.items():
        mv = re.sub(rf"\b{key}\b", f"{value}n", mv)
    mv = replace_once(mv, "  IO.print(F32.show(loop(", "  do IO<Unit>:\n    r : F32 <- IO.pure(F32, loop(", "mv")
    mv = replace_once(mv, "Nil{}))))))\n", "Nil{})))))\n    IO.print(F32.show(r))\n", "mv")
    mv = compute_marker(mv, next(l for l in mv.split("\n") if l.startswith("    r : F32 <- IO.pure(F32, loop(")), "mv")
    (b / "mv.bend").write_text(mv)
    x = [(k % 13) / 10 for k in range(MV["KN"])][::-1]
    w = [(k % 13) / 10 for k in range(MV["KN"] * MV["MN"])][::-1]
    best = max(math.fsum(w[r * MV["KN"] + k] * x[k] for k in range(MV["KN"])) for r in range(MV["MN"]))
    (ml / "products.json").write_text(json.dumps(dict(mm_array=98.0 * 128001, mv=best * (MV["REPS"] + 1))))


def link(source, target):
    if target.is_symlink() or target.exists():
        target.unlink()
    target.symlink_to(source)


def run(command, cwd):
    result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"ML preparation failed: {' '.join(map(str, command))}\n{result.stderr[-2000:]}")
    return result.stdout


def write_reference(path, text, prompt_ids):
    ids = json.loads(re.search(r"^generated (\[.*\])", text, re.M)[1])
    logits = [float(v) for v in re.search(r"^logits (.*)$", text, re.M)[1].split()]
    path.write_text(json.dumps(dict(prompt_ids=json.loads(prompt_ids), generated=ids, logits=logits)))


# ----------------------------------------------------------------------------------------------
# cases and correctness


def plan(config, work, build, case, cases, bend_build):
    python = config["tools"]["python_ml"]
    ml = work / "bend-ml"
    threads = config["threads"]
    sources = {"gpt2": "demos/gpt2/fast.bend", "nanogpt": "demos/nanogpt/nano.bend", "mnist": "demos/mnist/fast.bend",
               "mm_array": "bench/mm_array.bend", "mv": "bench/mv.bend"}
    gpt2_ids = " ".join(map(str, json.loads((ml / "gpt2.json").read_text())["prompt_ids"]))
    nano_ids = " ".join(str(NANO_VOCAB.index(c)) for c in NANO_PROMPT)
    commands = {
        "gpt2": ([GPT2_PROMPT, GPT2_TOKENS],
                 lambda t: [python, ASSETS / "gpt_torch.py", "demos/gpt2/data/w", 12, 12, gpt2_ids, GPT2_TOKENS, 1, t]),
        "nanogpt": ([NANO_PROMPT, NANO_TOKENS, NANO_REPS],
                    lambda t: [python, ASSETS / "gpt_torch.py", "demos/nanogpt/w", NANO["layers"], NANO["heads"], nano_ids,
                               NANO_TOKENS, NANO_REPS, t]),
        "mnist": ([1, 0, 0.1], lambda t: [python, "reference/mnist_bench.py", "--epochs", 1, "--threads", t]),
        "mm_array": ([], lambda t: [python, ASSETS / "products_torch.py", "mm_array", t]),
        "mv": ([], lambda t: [python, ASSETS / "products_torch.py", "mv", t, MV["KN"], MV["MN"], MV["REPS"]]),
    }
    contracts = {
        "gpt2": dict(workload="gpt2-small-greedy", prompt=GPT2_PROMPT, tokens=GPT2_TOKENS, weights="openai-community/gpt2",
                     timed="generation after loading", reference="bend-ml reference/gpt2_ref.py", logit_tolerance=0.05),
        "nanogpt": dict(workload="nanogpt-shakespeare-char-greedy", prompt=NANO_PROMPT, tokens=NANO_TOKENS, repetitions=NANO_REPS,
                        sizes=NANO, weights="seeded uniform, nanoGPT standard deviations, seed 1337",
                        timed="generation after loading", reference="full recompute per token", logit_tolerance=1e-3),
        "mnist": dict(workload="mnist-mlp-784-128-10-one-epoch", batch=100, lr=0.1, timed="training epoch",
                      reference="bend-ml reference/mnist_torch.py, 1 thread", loss_tolerance=1e-4, correct_tolerance=2),
        "mm_array": dict(workload="dot-784-x128000", timed="products", expected=98.0 * 128001),
        "mv": dict(workload="matvec-768x2304-x101", timed="products", rel_tolerance=1e-4),
    }
    for name in config.get("ml_workloads", WORKLOADS):
        binary = bend_build(ml / sources[name], f"ml-{name}")
        args, baseline = commands[name]
        contract = dict(contracts[name], bend_ml=config["bend_ml"]["commit"])
        for t in threads:
            case("ml", name, "bend", t, binary, ["--threads", t, *args], "", contract=contract)
            case("ml", name, "pytorch", t, python, baseline(t)[1:], "", contract=contract)
        for item in cases:
            if item["suite"] == "ml" and item["workload"] == name:
                item["cwd"] = "bend-ml"
                item["ml_kind"] = name
                item["ml_reference"] = str(ml / {"gpt2": "gpt2.json", "nanogpt": "nanogpt.json", "mnist": "mnist.json"}.get(name, "products.json"))


def generated(stdout):
    return [int(x) for x in re.findall(r"^\s*id (\d+) +logit", stdout, re.M)], \
        [float(x) for x in re.findall(r"^\s*id \d+ +logit (-?[\d.e+-]+)", stdout, re.M)]


def correct(case, result):
    """Bend and PyTorch print the same lines: per generated token `id N  logit X`, the MNIST epoch
    line, or the products' value."""
    kind, out = case["ml_kind"], result["stdout"]
    try:
        reference = json.loads(Path(case["ml_reference"]).read_text())
        if kind in ("gpt2", "nanogpt"):
            ids, logits = generated(out)
            reps = case["contract"].get("repetitions", 1)
            want_ids, want_logits = reference["generated"] * reps, reference["logits"] * reps
            return (ids == want_ids and len(logits) == len(want_logits)
                    and max(abs(a - b) for a, b in zip(logits, want_logits)) < case["contract"]["logit_tolerance"])
        if kind == "mnist":
            bend = re.search(r"train_loss=([\d.]+) test_correct=(\d+)/10000", out)
            torch = re.search(r"train_loss=([\d.]+) test_acc=([\d.]+)", out)
            loss, hits = (float(bend[1]), int(bend[2])) if bend else (float(torch[1]), round(float(torch[2]) * 10000))
            return (abs(loss - reference["train_loss"]) <= case["contract"]["loss_tolerance"]
                    and abs(hits - reference["test_correct"]) <= case["contract"]["correct_tolerance"])
        value = float(out.split()[-1])
        want = reference[kind]
        return abs(value - want) <= (0 if kind == "mm_array" else case["contract"]["rel_tolerance"] * abs(want))
    except (OSError, ValueError, TypeError, IndexError, KeyError):
        return False
