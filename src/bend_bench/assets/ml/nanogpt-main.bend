# ---------------------------------------------------------------------
# characters (nanoGPT's shakespeare-char vocabulary, ids 0..64)
# ---------------------------------------------------------------------

def vocab() -> List<&2, Char>:
  String.to_list(@VOCAB@)

def index_sel(b: Bool, x: Nat, y: Nat) -> Nat:
  match b:
    case True{}:
      x
    case False{}:
      y

def char_id(cs: List<&2, Char>, +c: Char, +i: Nat) -> Nat:
  match cs:
    case Nil{}:
      0n
    case Con{h, t}:
      index_sel(Char.is_eq(h, c), i, char_id(t, c, 1n+i))

def ids_of(cs: List<&2, Char>) -> List<&2, Nat>:
  match cs:
    case Nil{}:
      Nil{}
    case Con{c, t}:
      char_id(vocab(), c, 0n) <> ids_of(t)

def show_nats(xs: List<&2, Nat>) -> String:
  match xs:
    case Nil{}:
      ""
    case Con{h, t}:
      Nat.show(h) ++ " " ++ show_nats(t)

# ---------------------------------------------------------------------
# main program
# ---------------------------------------------------------------------

def fin(ids: List<&2, Nat>, st: St) -> IO(Unit):
  match st:
    case St{cs, tok, pos, queue, left, gen}:
      IO.print("ids: " ++ show_nats(List.append(&2, Nat, ids, List.reverse(&2, Nat, gen))))

def start2(model: Model, +ids: List<&2, Nat>, +n: Nat) -> IO(Unit):
  match ids:
    case Nil{}:
      IO.print("empty prompt")
    case Con{t0, qt}:
      do IO<Unit>:
        t0ms : Nat <- IO.now()
        IO.print("prompt ids: " ++ show_nats(ids))
        st : St <- loop(Nat.add(List.length(&2, Nat, ids), Nat.sub(n, 1n)), t0ms, SM{St{List.replicate(KV, @KV@, KV{Nil{}, Nil{}}), t0, 0n, qt, n, Nil{}}, model})
        fin(ids, st)

def run1(prompt: String, mn: Maybe<&2, Nat>) -> IO(Unit):
  match mn:
    case None{}:
      IO.print("usage: nano \"prompt\" n_tokens")
    case Some{n}:
      do IO<Unit>:
        t0 : Nat <- IO.now()
        model : Model <- load_model()
        t1 : Nat <- IO.now()
        IO.print("weights loaded in " ++ Nat.show(Nat.div(Nat.sub(t1, t0), 1000n)) ++ "s")
        start2(model, ids_of(String.to_list(prompt)), n)

# repeated generation: each repetition starts fresh at position 0 with empty caches, so the
# positions stay short however many tokens are timed in all
def loop2(fuel: Nat, +t0: Nat, sm: SM) -> IO(SM):
  match fuel sm:
    case 0n SM{st, m}:
      IO.pure(SM, SM{st, m})
    case 1n+p SM{st, m}:
      do IO<SM>:
        s2 : SM <- adv(m, st, t0)
        loop2(p, t0, s2)

def rep1(+ids: List<&2, Nat>, +n: Nat, m: Model) -> IO(SM):
  match ids:
    case Nil{}:
      IO.pure(SM, SM{St{Nil{}, 0n, 0n, Nil{}, 0n, Nil{}}, m})
    case Con{t0, qt}:
      do IO<SM>:
        t0ms : Nat <- IO.now()
        loop2(Nat.add(List.length(&2, Nat, ids), Nat.sub(n, 1n)), t0ms, SM{St{List.replicate(KV, @KV@, KV{Nil{}, Nil{}}), t0, 0n, qt, n, Nil{}}, m})

def reps(k: Nat, +ids: List<&2, Nat>, +n: Nat, sm: SM) -> IO(Unit):
  match k sm:
    case 0n SM{st, m}:
      IO.pure(Unit, Unit{})
    case 1n+p SM{st, m}:
      do IO<Unit>:
        s2 : SM <- rep1(ids, n, m)
        reps(p, ids, n, s2)

def run_reps(prompt: String, +n: Nat, +k: Nat) -> IO(Unit):
  do IO<Unit>:
    model : Model <- load_model()
    t1 : Nat <- IO.now()
    reps(k, ids_of(String.to_list(prompt)), n, SM{St{Nil{}, 0n, 0n, Nil{}, 0n, Nil{}}, model})
    t2 : Nat <- IO.now()
    IO.print("gen_ms " ++ Nat.show(Nat.sub(t2, t1)) ++ " reps " ++ Nat.show(k))

def run_reps2(prompt: String, mn: Maybe<&2, Nat>, mk: Maybe<&2, Nat>) -> IO(Unit):
  match mn mk:
    case Some{n} Some{k}:
      run_reps(prompt, n, k)
    case _ _:
      IO.print("usage: nano \"prompt\" n_tokens [repetitions]")

def dispatch(args: List<String>) -> IO(Unit):
  match args:
    case Con{prog, Con{prompt, Con{n, Nil{}}}}:
      run1(prompt, Nat.read(n))
    case Con{prompt, Con{n, Nil{}}}:
      run1(prompt, Nat.read(n))
    case Con{prog, Con{prompt, Con{n, Con{k, Nil{}}}}}:
      run_reps2(prompt, Nat.read(n), Nat.read(k))
    case _:
      IO.print("usage: nano \"prompt\" n_tokens")

def main() -> IO(Unit):
  do IO<Unit>:
    args : List<String> <- IO.args()
    dispatch(args)
