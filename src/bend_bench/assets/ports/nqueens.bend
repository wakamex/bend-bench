# BOTS N-Queens input/output contract, using conventional bit-mask search.
import Base

def queens(+fuel: Nat, +full: U32, +cols: U32, +left: U32, +right: U32, +avail: U32, done: Bool, empty: Bool) -> Nat:
  match fuel:
    case 0n:
      0n
    case 1n+p:
      match done:
        case True{}:
          1n
        case False{}:
          match empty:
            case True{}:
              0n
            case False{}:
              +bit = U32.and(avail, U32.sub(0, avail))
              +cs = U32.or(cols, bit)
              +ls = U32.shln(U32.or(left, bit), 1n)
              +rs = U32.shrn(U32.or(right, bit), 1n)
              +next = U32.and(full, U32.not(U32.or(cs, U32.or(ls, rs))))
              +rest = U32.xor(avail, bit)
              a b = queens(p, full, cs, ls, rs, next, U32.is_eq(cs, full), U32.is_zero(next)) queens(p, full, cols, left, right, rest, False{}, U32.is_zero(rest))
              Nat.add(a, b)

# At N=14 a path has at most N*(N+1) sibling/child steps. Fuel 256
# exceeds that structural bound; no scheduling cutoff is used.
def main() -> IO(Unit):
  IO.print(Nat.show(queens!(256n, @MASK@, 0, 0, 0, @MASK@, False{}, False{})))
