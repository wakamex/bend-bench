import Base

def deep(n: Nat, +k: U32) -> U32:
  match n:
    case 0n:
      k
    case 1n+p:
      x = deep(p, (k + 1 : U32))
      ((x * 3 : U32) + k : U32)

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(U32.show(deep!(1000000n, 0)))
