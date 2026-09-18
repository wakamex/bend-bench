import Base

type Answers is Data:
  Answer{v: U32}
  Both{a: Answers, b: Answers}

def won(+board: U32) -> Bool:
  @WIN@

def legal(me: U32, other: U32, +i: U32) -> Bool:
  Bool.and(U32.is_lt(i, @CELLS@), U32.is_zero(U32.and(U32.or(me, other), U32.shln(1, U32.to_nat(i)))))

# One structurally fuel-bounded definition avoids unsafe mutual recursion.
# Each ply needs seven calls; 128 exceeds the maximum for these endgames.
# Values outside 0/1/2 reject exhausted or otherwise invalid computations.
def search(+fuel: Nat, mode: Bool, terminal: Bool, +left: Nat, +d: Nat, valid: Bool, +me: U32, +other: U32, +i: U32) -> U32:
  match fuel:
    case 0n: 4294967294
    case 1n+rest:
      match mode:
        case True{}:
          match terminal:
            case True{}: 0
            case False{}:
              match left:
                case 0n: 1
                case 1n+p: search(rest, False{}, False{}, p, 5n, True{}, me, other, 0)
        case False{}:
          match d:
            case 0n:
              match valid:
                case False{}: 0
                case True{}:
                  +next = U32.or(me, U32.shln(1, U32.to_nat(i)))
                  U32.sub(2, search(rest, True{}, won(next), left, 0n, True{}, other, next, 0))
            case 1n+p:
              +a = U32.shl(i)
              +b = U32.inc(a)
              x y = search(rest, False{}, False{}, left, p, legal(me, other, a), me, other, a) search(rest, False{}, False{}, left, p, legal(me, other, b), me, other, b)
              U32.max(x, y)

def answer(pair: U32 & U32) -> Answers:
  (me, other) = pair
  Answer{search(128n, True{}, False{}, @EMPTY@n, 0n, True{}, me, other, 0)}

def position(+i: U32) -> U32 & U32:
  @POSITIONS@

def batch(+d: Nat, +i: U32) -> Answers:
  match d:
    case 0n:
      answer(position(i))
    case 1n+p:
      a b = batch(p, U32.shl(i)) batch(p, U32.inc(U32.shl(i)))
      Both{a, b}

def output(a: Answers, tail: String) -> String:
  match a:
    case Answer{v}: U32.show(v) ++ "\n" ++ tail
    case Both{a, b}: output(a, output(b, tail))

def main() -> IO(Unit):
  IO.print(output(batch!(4n, 0), ""))
