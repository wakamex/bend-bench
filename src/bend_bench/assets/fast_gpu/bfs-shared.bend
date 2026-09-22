import Base

type Tree is Data:
  Leaf{v: U32}
  Node{a: Tree, b: Tree}

def hash(+x: U32) -> U32:
  +a = U32.mul(U32.xor(x, U32.shrn(x, 16n)), 2246822507)
  +b = U32.mul(U32.xor(a, U32.shrn(a, 13n)), 3266489909)
  U32.xor(b, U32.shrn(b, 16n))

def init(+d: Nat, +i: U32) -> Tree:
  match d:
    case 0n: Leaf{Bool.pick(U32, U32.is_zero(i), 0, 4294967295)}
    case 1n+p:
      a b = init(p, U32.shl(i)) init(p, U32.inc(U32.shl(i)))
      Node{a, b}

def get(+d: Nat, t: Tree, +i: U32) -> U32:
  match d t:
    case 0n Leaf{v}: v
    case 1n+p Node{a, b}:
      get(p, Bool.pick(Tree, U32.is_zero(U32.and(U32.shrn(i, p), 1)), a, b), i)
    case _ _: 4294967295

def incoming(+t: Tree, +v: U32, +j: Nat) -> U32:
  match j:
    case 0n: 4294967295
    case 1n+p:
      source = U32.and(hash(U32.add(U32.mul(v, 8), U32.from_nat(p))), 262143)
      a b = get(18n, t, source) incoming(t, v, p)
      U32.min(a, b)

def visit(t: Tree, i: U32, old: U32, known: Bool) -> Tree:
  match known:
    case True{}: Leaf{old}
    case False{}:
      +near = incoming(t, i, 8n)
      Leaf{Bool.pick(U32, U32.is_eq(near, 4294967295), near, U32.inc(near))}

def step(+d: Nat, +i: U32, +t: Tree) -> Tree:
  match d:
    case 0n:
      +old = get(18n, t, i)
      visit(t, i, old, Bool.not(U32.is_eq(old, 4294967295)))
    case 1n+p:
      a b = step(p, U32.shl(i), t) step(p, U32.inc(U32.shl(i)), t)
      Node{a, b}

def same(a: Tree, b: Tree) -> Bool:
  match a b:
    case Leaf{x} Leaf{y}: U32.is_eq(x, y)
    case Node{a, b} Node{c, d}: Bool.and(same(a, c), same(b, d))
    case _ _: False{}

def solve(fuel: Nat, +t: Tree, done: Bool) -> Tree:
  match fuel:
    case 0n: Leaf{4294967294}
    case 1n+p:
      match done:
        case True{}: t
        case False{}:
          +next = step(18n, 0, t)
          solve(p, next, same(t, next))

def output(t: Tree, tail: String) -> String:
  match t:
    case Leaf{v}: U32.show(v) ++ "\n" ++ tail
    case Node{a, b}: output(a, output(b, tail))

def bfs() -> Tree:
  solve(64n, init(18n, 0), False{})

def main() -> IO(Unit):
  IO.print(output(bfs!(), ""))
