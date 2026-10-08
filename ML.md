# Machine-learning workloads from bend-ml

How fast is Bend at machine-learning work written the way a Bend programmer writes it today? The `ml` suite times [bend-ml](https://github.com/nuxyel/bend-ml), Renan Vinícius's machine learning in Bend 2 with tensor shapes checked by the type system, against [PyTorch](https://pytorch.org/) on the same CPU threads, and on the GPU where Bend can use one. bend-ml's own measurements put PyTorch about 35× ahead on MNIST and 2–5× on GPT-2, and attribute the gap to Bend's scalar code rather than its types. This suite tracks that gap on Bend's latest revision and on compiler changes.

## First results

On Bend d052d4f3 (5 October 2026), Bend takes 4–5× PyTorch's time on transformer inference and 13–82× on training and single products. Each cell is Bend's median compute time divided by PyTorch's, with both medians, ten correctness-checked runs each on the shared Ryzen 9 3950X host; above 1× means PyTorch is faster:

| Workload | 1 thread | 16 threads |
|---|---:|---:|
| GPT-2 small, 24 tokens | 4.1× (3.95 s / 0.96 s) | 4.2× (4.16 s / 0.99 s) |
| nanoGPT sizes, 10 × 24 tokens | 4.4× (6.23 s / 1.42 s) | 5.2× (6.59 s / 1.27 s) |
| MNIST MLP, one training epoch | 82× (38.1 s / 0.46 s) | 46× (16.5 s / 0.36 s) |
| `mm_array`, 128,000 dot products | 26× (87 ms / 3.3 ms) | 41× (75 ms / 1.8 ms) |
| `mv`, 101 matrix-vector products | 13× (173 ms / 12.9 ms) | 16× (195 ms / 12.6 ms) |

Bend's transformer times do not improve with threads, since bend-ml computes its products sequentially; MNIST's batched products run in parallel blocks and gain 2.3× from 16 threads. The raw report is `runs/d6e9954a0fb909dd5375/report.md`.

## Workloads

| Workload | Bend program | What it exercises | PyTorch baseline | Correctness |
|---|---|---|---|---|
| `gpt2` | bend-ml's GPT-2 small (124 M parameters), 24 greedy tokens after "The capital of France is" | Large-model inference; matrix-vector products are about 42% of generation time | Same weights, key/value cache | Generated ids identical and every step's top logit within 0.05 of bend-ml's `gpt2_ref.py` |
| `nanogpt` | The same program at [nanoGPT](https://github.com/karpathy/nanoGPT)'s character-level Shakespeare sizes (6 layers, 6 heads, 384 wide, 65 characters), 10 × 24 greedy tokens after "ROMEO:" | Small-model inference; per-layer list, attention and sharing work dominates | Same weights, key/value cache | Ids identical and logits within 0.001 of a full-recompute PyTorch pass |
| `nanogpt-batch` | The `nanogpt` model generating 24 tokens for each of 1,024 sequences, at 16 threads, on Bend's CPU and GPU | Inference at a batch large enough to use the hardware; on the GPU, each lane runs whole generations | One batched forward pass per step, on the CPU and on CUDA | Every sequence's ids and logits as for `nanogpt` |
| `mnist` | bend-ml's 784-128-10 MLP, one epoch of 600 batches of 100 | Training | bend-ml's `mnist_torch.py` | Mean training loss within 1e-4 and test hits within 2 of PyTorch on one thread |
| `mm_array` | 128,000 dot products of 784 elements over `Array<F32>` | One scalar product loop | Ten 100×784 by 784×128 products and one dot | Exactly 12,544,098 |
| `mv` | 101 products of a 768 vector with a 2304×768 matrix | GPT-2's matrix-vector shape | Same products | Within 1e-4 of the exact value |

The timed region is the work itself: generation after loading the weights, the training epoch, or the products. Each program reports it as `EVAL_COMPUTE_SECONDS`; complete-process time is recorded beside it. bend-ml runs its products sequentially, since copying a matrix per parallel block made matrix-vector products 10× slower in its experiments, so Bend's time barely changes with threads on the two transformers.

Bend can only use the GPU when the parallel work is independent: a `!` call fans out over lanes, and each lane runs its own sequential code. bend-ml's products cannot split over lanes, since its parallel product copies both matrices per block and its shared-`Array` product faults on the GPU (bend-ml's NOTES.md, experiment 10). The `nanogpt-batch` wrapper, bend-bench's own code in [assets/ml/nanogpt-batch.bend](src/bend_bench/assets/ml/nanogpt-batch.bend), sidesteps that by giving each sequence a whole generation, forked over shared weights. Training has no such independent work: each MNIST step needs the previous step's weights, so a Bend GPU MNIST needs a matrix product that splits across lanes, and the suite runs Bend's MNIST on the CPU only. 1,024 sequences stays well below the 8,192 at which Bend's GPU run faults.

The CPU fast profile also runs `nanogpt` at one and 16 threads, without PyTorch: its weights come from Python's standard library and its reference is [assets/ml/nanogpt-reference.json](src/bend_bench/assets/ml/nanogpt-reference.json).

## How the programs are staged

Preparation copies the pinned bend-ml checkout's programs, packages and reference scripts into the run's work directory, so they run with their own relative paths. Two kinds of edit are applied to the Bend sources, each required to match exactly once:

- BendHub imports of bend-ml's packages (`bend-ml-tensor-array@0.1.3.0/main.bend` and the others) become relative imports of the same packages from the pinned checkout. Building needs no network.
- One line reports the timed region on stderr, between two `IO.now()` calls added around the timed statement.

The nanoGPT program is generated from bend-ml's `demos/gpt2/fast.bend` by `nano_source` in [ml.py](src/bend_bench/ml.py): GPT-2's sizes become nanoGPT's, characters replace the BPE tokenizer, and the generation repeats from position 0 so the context stays short. Its weights are uniform with nanoGPT's initial standard deviations, generated from a fixed seed and checked against a pinned SHA-256. Bend's output matches nanoGPT's PyTorch model on the same weights to within 2.5e-6 in the logits.

bend-ml's GPT-2 preparation (`gpt2_prep.py`) converts the downloaded weights into 1.5 GB of per-tensor files. It runs once into `ml_data/.prepared/`, keyed by the preparation scripts and the input hashes, and later runs link to it. References are computed during preparation, never inside a timed sample.

## Setup

The suite needs a bend-ml checkout at the pinned commit, its data, and a Python with PyTorch:

```sh
git clone https://github.com/nuxyel/bend-ml ../bend-ml
git -C ../bend-ml checkout 91fc6dd3f2bb147238480fc764057548acd6c40f
uv venv ../bend-ml/reference/.venv
VIRTUAL_ENV=../bend-ml/reference/.venv uv pip install --index-strategy unsafe-best-match -r ../bend-ml/reference/requirements.txt
uv venv ../bend-ml-local/venv-cuda
VIRTUAL_ENV=../bend-ml-local/venv-cuda uv pip install numpy torch --index-url https://download.pytorch.org/whl/cu130 --extra-index-url https://pypi.org/simple
mkdir -p sources/ml-data/gpt2 sources/ml-data/mnist
for f in model.safetensors vocab.json merges.txt; do curl -fsSL -o sources/ml-data/gpt2/$f https://huggingface.co/openai-community/gpt2/resolve/main/$f; done
for f in train-images-idx3-ubyte train-labels-idx1-ubyte t10k-images-idx3-ubyte t10k-labels-idx1-ubyte; do curl -fsSL https://ossci-datasets.s3.amazonaws.com/mnist/$f.gz | gunzip > sources/ml-data/mnist/$f; done
uv run --locked bend-bench run ml.toml
```

[ml.toml](ml.toml) pins the Bend revision, the bend-ml commit, the CUDA toolkit and the two PyTorch interpreters: `python_ml` for the CPU and references, `python_ml_cuda` for the CUDA columns. Without `cuda = true` the suite runs the CPU columns only. The data files are pinned by SHA-256 in [ml.py](src/bend_bench/ml.py); a different file stops preparation. `ml_workloads` selects a subset.
