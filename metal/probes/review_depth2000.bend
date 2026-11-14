import Base

def h(n: Nat, +a: U32) -> U32:
  match n:
    case 0n:
      a
    case 1n+p:
      y = h(p, a)
      ((y * 31 : U32) + 7 : U32)

def loop(n: Nat, +acc: U32) -> U32:
  match n:
    case 0n:
      acc
    case 1n+p:
      x = h(2n, acc)
      y = h(2n, x)
      loop(p, (y + 1 : U32))

def down(d: Nat, +n: Nat) -> U32:
  match d:
    case 0n:
      loop(n, 0)
    case 1n+p:
      x = down(p, n)
      (x + 1 : U32)

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(U32.show(down!(2000n, 30000n)))
