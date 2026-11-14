import Base

def mk(+f: Nat, +n: Nat, +k: U32) -> List<&2, U32>:
  match f:
    case 0n:
      Nil{}
    case 1n+g:
      match n:
        case 0n:
          Nil{}
        case 1n+p:
          match p:
            case 0n:
              k <> Nil{}
            case 1n+q:
              +h = Nat.div(n, 2n)
              lo hi = mk(g, h, k) mk(g, Nat.sub(n, h), (k + 1 : U32))
              List.append(&2, U32, lo, hi)

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(Nat.show(List.length(&2, U32, mk!(64n, 100000n, 0))))
