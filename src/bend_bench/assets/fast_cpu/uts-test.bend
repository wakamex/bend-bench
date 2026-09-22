# BOTS binomial UTS: SHA-1(parent-state || child-index), seed 42.
# The test.input tree is 4,112,897 nodes, with root branching 2000,
# non-root branching 8, and probability .124875.
# No precomputed tree, task queue, cutoffs, or balancing by subtree size.
import Base

type Digest is Data:
  Digest{a: U32, b: U32, c: U32, d: U32, e: U32}

type Round is Type:
  Round{w: Array<U32>, s: Digest}

def rol(+x: U32, +n: Nat) -> U32:
  U32.or(U32.shln(x, n), U32.shrn(x, Nat.sub(32n, n)))

def choose(t: Bool, x: U32, y: U32) -> U32:
  match t:
    case True{}: x
    case False{}: y

def fk(+i: U32, +b: U32, +c: U32, +d: U32) -> U32 & U32:
  +parity = U32.xor(U32.xor(b, c), d)
  maj = U32.or(U32.or(U32.and(b, c), U32.and(b, d)), U32.and(c, d))
  ch = U32.or(U32.and(b, c), U32.and(U32.not(b), d))
  f = choose(U32.is_lt(i, 20), ch, choose(U32.is_lt(i, 40), parity, choose(U32.is_lt(i, 60), maj, parity)))
  k = choose(U32.is_lt(i, 20), 1518500249, choose(U32.is_lt(i, 40), 1859775393, choose(U32.is_lt(i, 60), 2400959708, 3395469782)))
  (f, k)

def word.d(i: U32, a: U32, b: U32, c: U32, r: Array<U32> & U32) -> Array<U32> & U32:
  (w, d) = r
  +v = rol(U32.xor(U32.xor(a, b), U32.xor(c, d)), 1n)
  (w[U32.and(i, 15)] <- v, v)

def word.c(+i: U32, a: U32, b: U32, r: Array<U32> & U32) -> Array<U32> & U32:
  (w, c) = r
  word.d(i, a, b, c, w[U32.and(i, 15)])

def word.b(+i: U32, a: U32, r: Array<U32> & U32) -> Array<U32> & U32:
  (w, b) = r
  word.c(i, a, b, w[U32.and(U32.sub(i, 14), 15)])

def word.a(+i: U32, r: Array<U32> & U32) -> Array<U32> & U32:
  (w, a) = r
  word.b(i, a, w[U32.and(U32.sub(i, 8), 15)])

def word(early: Bool, +i: U32, w: Array<U32>) -> Array<U32> & U32:
  match early:
    case True{}:
      w[i]
    case False{}:
      word.a(i, w[U32.and(U32.sub(i, 3), 15)])

def advance.fin(w: Array<U32>, +a: U32, b: U32, c: U32, d: U32, e: U32, wi: U32, r: U32 & U32) -> Round:
  (f, k) = r
  t = U32.add(U32.add(U32.add(U32.add(rol(a, 5n), f), e), k), wi)
  Round{w, Digest{t, a, rol(b, 30n), c, d}}

def advance.word(i: U32, s: Digest, r: Array<U32> & U32) -> Round:
  Digest{a, +b, +c, +d, e} = s
  (w, wi) = r
  advance.fin(w, a, b, c, d, e, wi, fk(i, b, c, d))

def advance(+i: U32, s: Digest, w: Array<U32>) -> Round:
  advance.word(i, s, word(U32.is_lt(i, 16), i, w))

def rounds(n: Nat, +i: U32, r: Round) -> Round:
  match n:
    case 0n:
      r
    case 1n+p:
      Round{w, s} = r
      rounds(p, U32.add(i, 1), advance(i, s, w))

def finish(r: Round) -> Digest:
  match r:
    case Round{w, Digest{a, b, c, d, e}}:
      Digest{U32.add(a, 1732584193), U32.add(b, 4023233417), U32.add(c, 2562383102), U32.add(d, 271733878), U32.add(e, 3285377520)}

def sha(w: Array<U32>) -> Digest:
  finish(rounds(80n, 0, Round{w, Digest{1732584193, 4023233417, 2562383102, 271733878, 3285377520}}))

def root(seed: U32) -> Digest:
  w = [0 : U32*16n]
  w[4] <- seed
  w[5] <- 2147483648
  w[15] <- 160
  sha(w)

def spawn(s: Digest, i: U32) -> Digest:
  match s:
    case Digest{a, b, c, d, e}:
      w = [0 : U32*16n]
      w[0] <- a
      w[1] <- b
      w[2] <- c
      w[3] <- d
      w[4] <- e
      w[5] <- i
      w[6] <- 2147483648
      w[15] <- 192
      sha(w)

def arity.go(t: Bool) -> Nat:
  match t:
    case True{}: 8n
    case False{}: 0n

def arity(s: Digest) -> Nat:
  match s:
    case Digest{a, b, c, d, e}:
      arity.go(U32.is_lt(U32.and(e, 2147483647), 268167021))

type Count is Data:
  Count{nodes: Nat, exhausted: Nat}

def join(a: Count, b: Count) -> Count:
  match a b:
    case Count{x, ex} Count{y, ey}:
      Count{1n+Nat.add(x, y), Nat.add(ex, ey)}

# Fuel makes termination explicit. Exhaustion is printed and rejects the run;
# it never silently counts a truncated tree as a correct result.
def forest(+fuel: Nat, +s: Digest, n: Nat, +i: U32) -> Count:
  match fuel:
    case 0n:
      Count{0n, 1n}
    case 1n+p:
      match n:
        case 0n:
          Count{0n, 0n}
        case 1n+q:
          +child = spawn(s, i)
          a b = forest(p, child, arity(child), 0) forest(p, s, q, U32.add(i, 1))
          join(a, b)

def show(c: Count) -> String:
  match c:
    case Count{n, exhausted}:
      Nat.show(1n+n) ++ " " ++ Nat.show(exhausted)

def main() -> IO(Unit):
  IO.print(show(forest!(U32.to_nat(1000000), root(42), U32.to_nat(2000), 0)))
