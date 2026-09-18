import Base

def key(i: U32) -> U32:
  +a = U32.mul(U32.inc(i), 2654435761)
  +b = U32.xor(a, U32.shln(a, 13n))
  +c = U32.xor(b, U32.shrn(b, 17n))
  U32.xor(c, U32.shln(c, 5n))

def sum(+d: Nat, +i: U32) -> U32:
  match d:
    case 0n:
      key(i)
    case 1n+p:
      a b = sum(p, U32.shl(i)) sum(p, U32.inc(U32.shl(i)))
      U32.add(a, b)

def main() -> IO(Unit):
  IO.print(U32.show(sum!(18n, 0)))
