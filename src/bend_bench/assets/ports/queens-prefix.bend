# Child/sibling recursion adapted from our matched bit-mask N-Queens port.
# Count candidate peels below row four, matching the published Stats contract.
def fork.solve(+fuel: Nat, +full: U32, +cols: U32, +left: U32, +right: U32, +avail: U32, done: Bool, empty: Bool) -> Stats:
  match fuel:
    case 0n:
      Stats{0, 0}
    case 1n+p:
      match done:
        case True{}:
          Stats{1, 0}
        case False{}:
          match empty:
            case True{}:
              Stats{0, 0}
            case False{}:
              +bit = U32.and(avail, U32.sub(0, avail))
              +cs = U32.or(cols, bit)
              +ls = U32.shl(U32.or(left, bit))
              +rs = U32.shr(U32.or(right, bit))
              +next = U32.and(full, U32.not(U32.or(cs, U32.or(ls, rs))))
              +rest = U32.xor(avail, bit)
              a b = fork.solve(p, full, cs, ls, rs, next, U32.is_eq(cs, full), U32.is_zero(next)) fork.solve(p, full, cols, left, right, rest, False{}, U32.is_zero(rest))
              smerge(Stats{0, 1}, smerge(a, b))

def leaf(fuel: U32, +full: U32, +cols: U32, +left: U32, +right: U32) -> Stats:
  +avail = U32.and(full, U32.not(U32.or(cols, U32.or(left, right))))
  fork.solve(U32.to_nat(fuel), full, cols, left, right, avail, U32.is_eq(cols, full), U32.is_zero(avail))

def bit.index(fuel: Nat, +bit: U32, one: Bool) -> U32:
  match fuel:
    case 0n:
      0
    case 1n+p:
      match one:
        case True{}:
          0
        case False{}:
          +next = U32.shr(bit)
          U32.inc(bit.index(p, next, U32.is_eq(next, 1)))

def prefix.leaf(take: Bool, +nn: U32, full: U32, cols: U32, left: U32, right: U32) -> Stats:
  match take:
    case True{}:
      leaf(U32.mul(nn, nn), full, cols, left, right)
    case False{}:
      Stats{0, 0}

# Explore legal placements recursively, selecting the identical base-N prefix
# IDs at row four. Prefix construction is excluded from the reported node count.
def prefix(+fuel: Nat, +rows: Nat, +nn: U32, +bound: U32, +full: U32, +cols: U32, +left: U32, +right: U32, +avail: U32, +index: U32, empty: Bool) -> Stats:
  match fuel:
    case 0n:
      Stats{0, 0}
    case 1n+p:
      match rows:
        case 0n:
          prefix.leaf(U32.is_lt(index, bound), nn, full, cols, left, right)
        case 1n+r:
          match empty:
            case True{}:
              Stats{0, 0}
            case False{}:
              +bit = U32.and(avail, U32.sub(0, avail))
              +cs = U32.or(cols, bit)
              +ls = U32.shl(U32.or(left, bit))
              +rs = U32.shr(U32.or(right, bit))
              +next = U32.and(full, U32.not(U32.or(cs, U32.or(ls, rs))))
              +rest = U32.xor(avail, bit)
              +child = U32.add(U32.mul(index, nn), bit.index(32n, bit, U32.is_eq(bit, 1)))
              a b = prefix(p, r, nn, bound, full, cs, ls, rs, next, child, U32.is_zero(next)) prefix(p, rows, nn, bound, full, cols, left, right, rest, index, U32.is_zero(rest))
              smerge(a, b)

def emit.stats(st: Stats) -> IO(Unit):
  match st:
    case Stat0{}:
      IO.print("0 0")
    case Stats{s, n}:
      IO.print(String.append(U32.show(s), String.append(" ", U32.show(n))))
