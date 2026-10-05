"""GPT-2-style greedy generation in PyTorch from bend-ml's per-tensor weights (DIR/*.bin, F32,
weights as output x input), the baseline and reference for bend_bench's gpt2 and nanogpt.

  gpt_torch.py DIR LAYERS HEADS "prompt ids" N REPS THREADS [--recompute]

Prints `  id N  logit X` per generated token, as the Bend programs do, for REPS independent
generations from the prompt, each with a key/value cache, and the generation time on stderr as
EVAL_COMPUTE_SECONDS. --recompute instead runs the whole context through the model for every
token, with no cache, and prints `generated [ids]` and `logits ...` (the reference).
"""
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F


def load(d, layers):
    def get(name, *shape):
        return torch.from_numpy(np.fromfile(os.path.join(d, name + ".bin"), dtype="<f4").reshape(*shape))
    width = os.path.getsize(os.path.join(d, "lnf_g.bin")) // 4
    vocab = os.path.getsize(os.path.join(d, "wte.bin")) // 4 // width
    context = os.path.getsize(os.path.join(d, "wpe.bin")) // 4 // width
    p = dict(width=width, wte=get("wte", vocab, width), wpe=get("wpe", context, width),
             lnf_g=get("lnf_g", width), lnf_b=get("lnf_b", width), layers=[])
    for i in range(layers):
        g = lambda n, *s: get(f"h{i}.{n}", *s)
        p["layers"].append(dict(ln1_g=g("ln1_g", width), ln1_b=g("ln1_b", width), aw=g("aw", 3 * width, width),
                                ab=g("ab", 3 * width), pw=g("pw", width, width), pb=g("pb", width),
                                ln2_g=g("ln2_g", width), ln2_b=g("ln2_b", width), fw=g("fw", 4 * width, width),
                                fb=g("fb", 4 * width), mw=g("mw", width, 4 * width), mb=g("mb", width)))
    return p


def block(L, x, heads, cache):
    """x: the new positions (t x width); cache: this layer's keys and values so far, extended."""
    d = x.shape[1]
    h = F.layer_norm(x, (d,), L["ln1_g"], L["ln1_b"], eps=1e-5)
    q, k, v = (h @ L["aw"].T + L["ab"]).split(d, dim=1)
    cache["k"] = k if cache.get("k") is None else torch.cat([cache["k"], k])
    cache["v"] = v if cache.get("v") is None else torch.cat([cache["v"], v])
    K, V = cache["k"], cache["v"]
    t, total = x.shape[0], K.shape[0]
    hd = d // heads
    mask = torch.ones(t, total, dtype=torch.bool).tril(total - t)
    out = []
    for i in range(heads):
        sl = slice(i * hd, (i + 1) * hd)
        s = (q[:, sl] @ K[:, sl].T) / hd ** 0.5
        out.append(torch.softmax(s.masked_fill(~mask, float("-inf")), dim=1) @ V[:, sl])
    x = x + torch.cat(out, dim=1) @ L["pw"].T + L["pb"]
    h = F.layer_norm(x, (d,), L["ln2_g"], L["ln2_b"], eps=1e-5)
    return x + F.gelu(h @ L["fw"].T + L["fb"], approximate="tanh") @ L["mw"].T + L["mb"]


def logits(p, ids, start, heads, caches):
    x = p["wte"][ids] + p["wpe"][start:start + len(ids)]
    for L, cache in zip(p["layers"], caches):
        x = block(L, x, heads, cache)
    x = F.layer_norm(x[-1:], (p["width"],), p["lnf_g"], p["lnf_b"], eps=1e-5)
    return (x @ p["wte"].T)[0]


@torch.no_grad()
def main():
    d, layers, heads, prompt, n, reps, threads = sys.argv[1:8]
    layers, heads, n, reps = int(layers), int(heads), int(n), int(reps)
    torch.set_num_threads(int(threads))
    p = load(d, layers)
    ids = [int(x) for x in prompt.split()]
    if "--recompute" in sys.argv:
        cur, gen, lgs = list(ids), [], []
        for _ in range(n):
            lg = logits(p, cur, 0, heads, [{} for _ in range(layers)])
            nxt = int(lg.argmax())
            gen.append(nxt); lgs.append(float(lg[nxt])); cur.append(nxt)
        print("generated", gen)
        print("logits", " ".join(f"{v:.6f}" for v in lgs))
        return
    lines = []
    t0 = time.perf_counter()
    for _ in range(reps):
        caches = [{} for _ in range(layers)]
        lg = logits(p, ids, 0, heads, caches)
        for step in range(n):
            nxt = int(lg.argmax())
            lines.append(f"  id {nxt}  logit {float(lg[nxt]):.6f}")
            if step + 1 < n:
                lg = logits(p, [nxt], len(ids) + step, heads, caches)
    print(f"EVAL_COMPUTE_SECONDS={time.perf_counter() - t0:.6f}", file=sys.stderr)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
