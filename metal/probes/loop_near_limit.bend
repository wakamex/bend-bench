import Base

def dive(d: Nat, +acc: U32) -> U32:
  match d:
    case 0n:
      acc
    case 1n+p:
      y = dive(p, (acc + 1 : U32))
      ((y * 3 : U32) + acc : U32)

def loop(n: Nat, +acc: U32) -> U32:
  match n:
    case 0n:
      acc
    case 1n+p:
      x = dive(30n, acc)
      loop(p, (x + 1 : U32))

def down(d: Nat, +n: Nat) -> U32:
  match d:
    case 0n:
      loop(n, 0)
    case 1n+p:
      x = down(p, n)
      (x + 1 : U32)

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(U32.show(down!(2010n, 3000n)))
