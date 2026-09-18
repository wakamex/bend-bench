import Base

type Answers is Data:
  Answer{v: U32}
  Both{a: Answers, b: Answers}

def won(+board: U32) -> Bool:
  @WIN@

def negate(value: U32, valid: Bool) -> U32:
  match valid:
    case True{}: U32.sub(2, value)
    case False{}: 4294967294

# One structurally fuel-bounded definition avoids unsafe mutual recursion.
# Entry and move-loop calls consume fuel. For E <= 9 empty squares,
# E*(E+1)/2 + E + 1 <= 55 calls suffice along any dependency path.
# Values outside 0/1/2 reject exhausted or otherwise invalid computations.
# Scores 0/1/2 mean loss/draw/win; negation is 2-score.
def search(+fuel: Nat, mode: Bool, terminal: Bool, +left: Nat, +me: U32, +other: U32, +avail: U32, +alpha: U32, +beta: U32) -> U32:
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
                case 1n+p:
                  +free = U32.and(U32.sub(U32.shln(1, @CELLS@n), 1), U32.not(U32.or(me, other)))
                  search(rest, False{}, False{}, p, me, other, free, alpha, beta)
        case False{}:
          match terminal:
            case True{}: alpha
            case False{}:
              +bit = U32.and(avail, U32.sub(0, avail))
              +next = U32.or(me, bit)
              +child = search(rest, True{}, won(next), left, other, next, 0, U32.sub(2, beta), U32.sub(2, alpha))
              +best = U32.max(alpha, negate(child, U32.is_lt(child, 3)))
              +remaining = U32.xor(avail, bit)
              search(rest, False{}, Bool.or(U32.is_zero(remaining), Bool.not(U32.is_lt(best, beta))), left, me, other, remaining, best, beta)

def answer(pair: U32 & U32) -> Answers:
  (me, other) = pair
  Answer{search(128n, True{}, False{}, @EMPTY@n, me, other, 0, 0, 2)}

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
