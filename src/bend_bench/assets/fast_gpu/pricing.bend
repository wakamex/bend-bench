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
      F32.mul(0.951229424500714, F32.max(0.0, F32.sub(F32.div(total, 256.0), 100.0)))
    case 1n+rest:
      +a = rng(state)
      +b = rng(a)
      z = F32.mul(F32.sqrt(F32.mul(F32.neg(2.0), F32.log(uniform(a)))), F32.cos(F32.mul(6.283185307179586, uniform(b))))
      +next = F32.mul(spot, F32.exp(F32.add(0.0001171875, F32.mul(0.0125, z))))
      path(rest, b, next, F32.add(total, next))

type Moments is Data:
  Moments{sum: F32, square: F32}

type Quote is Data:
  Quote{mean: F32, error: F32, count: U32}

def merge(a: Moments, b: Moments) -> Moments:
  match a:
    case Moments{x, xx}:
      match b:
        case Moments{y, yy}:
          Moments{F32.add(x, y), F32.add(xx, yy)}

def moments(+d: Nat, +i: U32, +offset: U32) -> Moments:
  match d:
    case 0n:
      +x = path(256n, U32.inc(U32.mod(hash(U32.inc(U32.add(i, offset))), 2147483646)), 100.0, 0.0)
      Moments{x, F32.mul(x, x)}
    case 1n+p:
      a b = moments(p, U32.shl(i), offset) moments(p, U32.inc(U32.shl(i)), offset)
      merge(a, b)

def finish(m: Moments) -> Quote:
  match m:
    case Moments{sum, square}:
      +s = sum
      +mean = F32.div(s, 262144.0)
      variance = F32.div(F32.max(0.0, F32.sub(square, F32.mul(s, mean))), 262143.0)
      Quote{mean, F32.sqrt(F32.div(variance, 262144.0)), 262144}

def quote(offset: U32) -> Quote:
  finish(moments(18n, 0, offset))

def emit(q: Quote, start: Nat) -> IO(Unit):
  match q:
    case Quote{mean, error, count}:
      do IO<Unit>:
        end : Nat <- IO.now()
        Unit <- IO.print("RESULT " ++ U32.show(F32.bits(mean)) ++ " " ++ U32.show(F32.bits(error)) ++ " " ++ U32.show(count))
        
        done : Nat <- IO.now()
        IO.print_err("PHASE_MS " ++ Nat.show(start) ++ " " ++ Nat.show(end) ++ " " ++ Nat.show(done))

def repeat(+left: Nat, +offset: U32) -> IO(Unit):
  match left:
    case 0n: IO.pure(Unit, Unit{})
    case 1n+p:
      do IO<Unit>:
        start : Nat <- IO.now()
        Unit <- emit(quote!(offset), start)
        repeat(p, U32.add(offset, 262144))

def main() -> IO(Unit):
  do IO<Unit>:
    Unit <- IO.print("READY")
    repeat(32n, 0)
