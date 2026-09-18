import Base

type Values is Data:
  Value{v: F32}
  Pair{a: Values, b: Values}

type Price is Data:
  Price{mean: F32, payoffs: Values}

def hash(+x: U32) -> U32:
  +a = U32.mul(U32.xor(x, U32.shrn(x, 16n)), 2246822507)
  +b = U32.mul(U32.xor(a, U32.shrn(a, 13n)), 3266489909)
  U32.xor(b, U32.shrn(b, 16n))

# Park-Miller with Schrage arithmetic; identical integer stream on every backend.
def rng(+x: U32) -> U32:
  +a = U32.mul(16807, U32.mod(x, 127773))
  +b = U32.mul(2836, U32.div(x, 127773))
  Bool.pick(U32, U32.is_gt(a, b), U32.sub(a, b), U32.add(U32.sub(2147483647, b), a))

def uniform(x: U32) -> F32:
  F32.mul(F32.add(U32.to_f32(U32.shrn(x, 8n)), 0.5), 0.00000011920928955078125)

def path(left: Nat, +state: U32, +spot: F32, total: F32) -> F32:
  match left:
    case 0n:
      F32.mul(0.951229424500714, F32.max(0.0, F32.sub(F32.div(total, @STEPS@.0), 100.0)))
    case 1n+rest:
      +a = rng(state)
      +b = rng(a)
      z = F32.mul(F32.sqrt(F32.mul(F32.neg(2.0), F32.log(uniform(a)))), F32.cos(F32.mul(6.283185307179586, uniform(b))))
      +next = F32.mul(spot, F32.exp(F32.add(@DRIFT@, F32.mul(@VOL@, z))))
      path(rest, b, next, F32.add(total, next))

def paths(+d: Nat, +i: U32) -> Values:
  match d:
    case 0n: Value{path(@STEPS@n, U32.inc(U32.mod(hash(U32.inc(i)), 2147483646)), 100.0, 0.0)}
    case 1n+p:
      a b = paths(p, U32.shl(i)) paths(p, U32.inc(U32.shl(i)))
      Pair{a, b}

def output(v: Values, tail: String) -> String:
  match v:
    case Value{x}: U32.show(F32.bits(x)) ++ "\n" ++ tail
    case Pair{a, b}: output(a, output(b, tail))

def total(v: Values) -> F32:
  match v:
    case Value{x}: x
    case Pair{a, b}:
      x y = total(a) total(b)
      F32.add(x, y)

def price(+d: Nat) -> Price:
  +payoffs = paths(d, 0)
  Price{F32.div(total(payoffs), U32.to_f32(U32.shln(1, d))), payoffs}

def print_price(p: Price) -> IO(Unit):
  match p:
    case Price{mean, payoffs}:
      IO.print(U32.show(F32.bits(mean)) ++ "\n" ++ output(payoffs, ""))

def main() -> IO(Unit):
  print_price(price!(@DEPTH@n))
