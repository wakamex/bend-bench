type Moments is Data:
  Moments{sum: F32, square: F32@AUDIT_FIELD@}

type Quote is Data:
  Quote{mean: F32, error: F32, count: U32@AUDIT_FIELD@}

def merge(a: Moments, b: Moments) -> Moments:
  match a:
    case Moments{x, xx@AUDIT_A@}:
      match b:
        case Moments{y, yy@AUDIT_B@}:
          Moments{F32.add(x, y), F32.add(xx, yy)@AUDIT_PAIR@}

def moments(+d: Nat, +i: U32, +offset: U32) -> Moments:
  match d:
    case 0n:
      +x = path(@STEPS@n, U32.inc(U32.mod(hash(U32.inc(U32.add(i, offset))), 2147483646)), 100.0, 0.0)
      Moments{x, F32.mul(x, x)@AUDIT_LEAF@}
    case 1n+p:
      a b = moments(p, U32.shl(i), offset) moments(p, U32.inc(U32.shl(i)), offset)
      merge(a, b)

def finish(m: Moments) -> Quote:
  match m:
    case Moments{sum, square@AUDIT_VALUES@}:
      +s = sum
      +mean = F32.div(s, @N@.0)
      variance = F32.div(F32.max(0.0, F32.sub(square, F32.mul(s, mean))), @NM1@.0)
      Quote{mean, F32.sqrt(F32.div(variance, @N@.0)), @N@@AUDIT_VALUES@}

def quote(offset: U32) -> Quote:
  finish(moments(@DEPTH@n, 0, offset))

def emit(q: Quote, start: Nat) -> IO(Unit):
  match q:
    case Quote{mean, error, count@AUDIT_VALUES@}:
      do IO<Unit>:
        end : Nat <- IO.now()
        Unit <- IO.print("RESULT " ++ U32.show(F32.bits(mean)) ++ " " ++ U32.show(F32.bits(error)) ++ " " ++ U32.show(count))
        @AUDIT_PRINT@
        done : Nat <- IO.now()
        IO.print_err("PHASE_MS " ++ Nat.show(start) ++ " " ++ Nat.show(end) ++ " " ++ Nat.show(done))

def repeat(+left: Nat, +offset: U32) -> IO(Unit):
  match left:
    case 0n: IO.pure(Unit, Unit{})
    case 1n+p:
      do IO<Unit>:
        start : Nat <- IO.now()
        Unit <- emit(quote!(offset), start)
        repeat(p, U32.add(offset, @N@))

def main() -> IO(Unit):
  do IO<Unit>:
    Unit <- IO.print("READY")
    repeat(@BATCHES@n, 0)
