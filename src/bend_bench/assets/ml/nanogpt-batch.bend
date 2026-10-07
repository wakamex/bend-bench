# ---------------------------------------------------------------------
# a batch of independent generations (bend-bench, not bend-ml): 2^d greedy
# generations from one prompt, each a pure function of its own model handle.
# The model forks with Array.fork, two handles to the same weights that only
# read them, so the batch holds one copy; `batch!` runs the batch on the GPU.
# ---------------------------------------------------------------------

type Gen is Type:
  Gen{ids: List<&2, Nat>, lgs: List<&2, F32>}

# The batch's results as a tree, flattened on the host: appending lists at
# each join recursed once per sequence on a GPU lane's stack, which overflowed
# at 2,048 sequences.
type GenTree is Type:
  GenLeaf{g: Gen}
  GenNode{l: GenTree, r: GenTree}

@unsafe
def mat_fork2(-r: Nat, -c: Nat, p: Array<F32> & Array<F32>) -> TA.Mat<r, c> & TA.Mat<r, c>:
  (a, b) = p
  ({TA.Mat{a} : TA.Mat<r, c>}, {TA.Mat{b} : TA.Mat<r, c>})

@unsafe
def mat_fork(-r: Nat, -c: Nat, m: TA.Mat<r, c>) -> TA.Mat<r, c> & TA.Mat<r, c>:
  match m:
    case TA.Mat{d}:
      mat_fork2(r, c, Array.fork(F32, d))

@unsafe
def layer_fork2(+ln1g: List<&2, F32>, +ln1b: List<&2, F32>, +ab: List<&2, F32>, +pb: List<&2, F32>, +ln2g: List<&2, F32>, +ln2b: List<&2, F32>, +fb: List<&2, F32>, +mb: List<&2, F32>, a: TA.Mat<@QKV@, @D@> & TA.Mat<@QKV@, @D@>, p: TA.Mat<@D@, @D@> & TA.Mat<@D@, @D@>, f: TA.Mat<@MLP@, @D@> & TA.Mat<@MLP@, @D@>, m: TA.Mat<@D@, @MLP@> & TA.Mat<@D@, @MLP@>) -> Layer & Layer:
  match a p f m:
    case Tuple{a1, a2} Tuple{p1, p2} Tuple{f1, f2} Tuple{m1, m2}:
      (Layer{ln1g, ln1b, a1, ab, p1, pb, ln2g, ln2b, f1, fb, m1, mb}, Layer{ln1g, ln1b, a2, ab, p2, pb, ln2g, ln2b, f2, fb, m2, mb})

@unsafe
def layer_fork(l: Layer) -> Layer & Layer:
  match l:
    case Layer{+ln1g, +ln1b, aw, +ab, pw, +pb, +ln2g, +ln2b, fw, +fb, mw, +mb}:
      layer_fork2(ln1g, ln1b, ab, pb, ln2g, ln2b, fb, mb, mat_fork(@QKV@, @D@, aw), mat_fork(@D@, @D@, pw), mat_fork(@MLP@, @D@, fw), mat_fork(@D@, @MLP@, mw))

@unsafe
def layers_fork2(p: Layer & Layer, q: List<&1, Layer> & List<&1, Layer>) -> List<&1, Layer> & List<&1, Layer>:
  match p q:
    case Tuple{a, b} Tuple{x, y}:
      (a <> x, b <> y)

@unsafe
def layers_fork(ls: List<&1, Layer>) -> List<&1, Layer> & List<&1, Layer>:
  match ls:
    case Nil{}:
      (Nil{}, Nil{})
    case Con{l, t}:
      layers_fork2(layer_fork(l), layers_fork(t))

@unsafe
def model_fork2(+lnfg: List<&2, F32>, +lnfb: List<&2, F32>, e: TA.Mat<@V@, @D@> & TA.Mat<@V@, @D@>, p: TA.Mat<@CTX@, @D@> & TA.Mat<@CTX@, @D@>, l: List<&1, Layer> & List<&1, Layer>) -> Model & Model:
  match e p l:
    case Tuple{e1, e2} Tuple{p1, p2} Tuple{l1, l2}:
      (Model{e1, p1, l1, lnfg, lnfb}, Model{e2, p2, l2, lnfg, lnfb})

@unsafe
def model_fork(m: Model) -> Model & Model:
  match m:
    case Model{wte, wpe, layers, +lnfg, +lnfb}:
      model_fork2(lnfg, lnfb, mat_fork(@V@, @D@, wte), mat_fork(@CTX@, @D@, wpe), layers_fork(layers))

# fuel: forward passes left; r: the output of the last one, at position pos - 1
def gen(fuel: Nat, +pos: Nat, queue: List<&2, Nat>, ids: List<&2, Nat>, lgs: List<&2, F32>, r: Out) -> Gen:
  match fuel queue r:
    case 0n Nil{} Out{+id, +lg, cs, m}:
      Gen{id <> ids, lg <> lgs}
    case 0n Con{q, qt} Out{id, lg, cs, m}:
      Gen{ids, lgs}
    case 1n+p Con{q, qt} Out{id, lg, cs, m}:
      gen(p, 1n+pos, qt, ids, lgs, fwd(m, cs, q, pos))
    case 1n+p Nil{} Out{+id, +lg, cs, m}:
      gen(p, 1n+pos, Nil{}, id <> ids, lg <> lgs, fwd(m, cs, id, pos))

def gen1(m: Model, +ids: List<&2, Nat>, +n: Nat) -> Gen:
  match ids:
    case Nil{}:
      Gen{Nil{}, Nil{}}
    case Con{t0, qt}:
      gen(Nat.sub(Nat.add(List.length(&2, Nat, ids), n), 2n), 1n, qt, Nil{}, Nil{}, fwd(m, List.replicate(KV, @KV@, KV{Nil{}, Nil{}}), t0, 0n))

# The handles are built before any generation forks: Bend's CPU scheduler
# spreads a fork tree across threads when its forks follow each other, and a
# model fork between levels held the batch to about two threads.
type ModelTree is Type:
  ModelLeaf{m: Model}
  ModelNode{l: ModelTree, r: ModelTree}

@unsafe
def handles2(+e: Nat, p: Model & Model) -> ModelTree:
  (a, b) = p
  ModelNode{handles(e, a), handles(e, b)}

@unsafe
def handles(+d: Nat, m: Model) -> ModelTree:
  match d:
    case 0n:
      ModelLeaf{m}
    case 1n+e:
      handles2(e, model_fork(m))

@unsafe
def generations(t: ModelTree, +ids: List<&2, Nat>, +n: Nat) -> GenTree:
  match t:
    case ModelLeaf{m}:
      GenLeaf{gen1(m, ids, n)}
    case ModelNode{l, r}:
      x y = generations(l, ids, n) generations(r, ids, n)
      GenNode{x, y}

@unsafe
def batch(+d: Nat, m: Model, +ids: List<&2, Nat>, +n: Nat) -> GenTree:
  generations(handles(d, m), ids, n)

def show_gen(ids: List<&2, Nat>, lgs: List<&2, F32>) -> String:
  match ids lgs:
    case Con{i, it} Con{l, lt}:
      "  id " ++ Nat.show(i) ++ "  logit " ++ F32.show(l) ++ "\n" ++ show_gen(it, lt)
    case _ _:
      ""

def show_gens(gs: GenTree) -> String:
  match gs:
    case GenLeaf{Gen{ids, lgs}}:
      show_gen(List.reverse(&2, Nat, ids), List.reverse(&2, F32, lgs))
    case GenNode{l, r}:
      show_gens(l) ++ show_gens(r)

@unsafe
def run_batch(prompt: String, +n: Nat, +d: Nat) -> IO(Unit):
  do IO<Unit>:
    model : Model <- load_model()
    gs : GenTree <- IO.pure(GenTree, batch!(d, model, ids_of(String.to_list(prompt)), n))
    IO.print(show_gens(gs))

@unsafe
def dispatch_batch(args: List<String>) -> IO(Unit):
  match args:
    case Con{prog, Con{prompt, Con{n, Con{d, Nil{}}}}}:
      run_batch2(prompt, Nat.read(n), Nat.read(d))
    case _:
      IO.print("usage: nano_batch \"prompt\" n_tokens log2_sequences")

@unsafe
def run_batch2(prompt: String, mn: Maybe<&2, Nat>, md: Maybe<&2, Nat>) -> IO(Unit):
  match mn md:
    case Some{n} Some{d}:
      run_batch(prompt, n, d)
    case _ _:
      IO.print("usage: nano_batch \"prompt\" n_tokens log2_sequences")

@unsafe
def main() -> IO(Unit):
  do IO<Unit>:
    args : List<String> <- IO.args()
    dispatch_batch(args)
