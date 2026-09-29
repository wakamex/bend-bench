# Mandelbrot for the GPU comparison: the algorithm of gpu/vendor-mandelbrot.cu, the result of
# Bend's published bench/runtime/mandelbrot (3101455856 at 51 iterations). Each pixel stops
# iterating at escape, and one pass over the 4096x4096 grid collects each bucket's pixel count, the
# sum of i * 2654435761 + 1 over its pixels, and the total escape time. The equalization colours
# then apply to those sums (the sum over pixels of colour * (i * 2654435761 + 1) + it), where the
# published program recolours every pixel in a second pass and runs every iteration of every pixel.
# The pass forks 2^14 leaves, and leaf j takes pixels j, j + 2^14, ...; from 2^13 to 2^16 leaves ran
# the same on an RTX 3090. Knob: ITERS (its), as in the published program.
import Base

# 2^14 leaves (lanes, lanes.n), each with 2^24 / 2^14 = 1024 pixels (per.leaf)
def lanes() -> Nat:
  14n

def lanes.n() -> U32:
  16384

def per.leaf() -> Nat:
  Nat.mul(16n, 64n)

type Acc is Data:
  A{c0: U32, c1: U32, c2: U32, c3: U32, c4: U32, c5: U32, c6: U32, c7: U32,
    w0: U32, w1: U32, w2: U32, w3: U32, w4: U32, w5: U32, w6: U32, w7: U32, t: U32}

def b2u(b: Bool) -> U32:
  match b:
    case False{}:
      0
    case True{}:
      1

# arithmetic shift right by 8 over two's-complement u32
def asr8(+v: U32) -> U32:
  U32.or(U32.shrn(v, 8n), U32.mul(U32.shrn(v, 31n), 4278190080))

# escape-time iterations: z (with squares r2, i2) steps until it escapes (out) or n runs out; it
# counts the iterations before escape
def mit(n: Nat, out: Bool, +cr: U32, +ci: U32, +zr: U32, +zi: U32, +r2: U32, +i2: U32, it: U32) -> U32:
  match n:
    case 0n:
      it
    case 1n+p:
      match out:
        case True{}:
          it
        case False{}:
          +nzr = U32.add(U32.sub(r2, i2), cr)
          +nzi = U32.add(asr8(U32.mul(2, U32.mul(zr, zi))), ci)
          +nr2 = asr8(U32.mul(nzr, nzr))
          +ni2 = asr8(U32.mul(nzi, nzi))
          mit(p, U32.is_gt(U32.add(nr2, ni2), 1024), cr, ci, nzr, nzi, nr2, ni2, U32.add(it, 1))

# one pixel: viewport [-2, 1) x [-1.5, 1.5) over the 4096x4096 grid
def pix(+id: U32, tn: Nat) -> U32:
  cr = U32.sub(U32.div(U32.mul(U32.and(id, 4095), 768), 4096), 512)
  ci = U32.sub(U32.div(U32.mul(U32.shrn(id, 12n), 768), 4096), 384)
  mit(tn, False{}, cr, ci, 0, 0, 0, 0, 0)

# pixel i with escape time it, in bucket b ((it*8)/ITERS clamped), added to the sums
def add(a: Acc, +i: U32, +it: U32, +b: U32) -> Acc:
  match a:
    case A{c0, c1, c2, c3, c4, c5, c6, c7, w0, w1, w2, w3, w4, w5, w6, w7, t}:
      +w = U32.add(U32.mul(i, 2654435761), 1)
      +m0 = b2u(U32.is_eq(b, 0))
      +m1 = b2u(U32.is_eq(b, 1))
      +m2 = b2u(U32.is_eq(b, 2))
      +m3 = b2u(U32.is_eq(b, 3))
      +m4 = b2u(U32.is_eq(b, 4))
      +m5 = b2u(U32.is_eq(b, 5))
      +m6 = b2u(U32.is_eq(b, 6))
      +m7 = b2u(U32.is_eq(b, 7))
      A{U32.add(c0, m0), U32.add(c1, m1), U32.add(c2, m2), U32.add(c3, m3), U32.add(c4, m4), U32.add(c5, m5), U32.add(c6, m6), U32.add(c7, m7),
        U32.add(w0, U32.mul(w, m0)), U32.add(w1, U32.mul(w, m1)), U32.add(w2, U32.mul(w, m2)), U32.add(w3, U32.mul(w, m3)),
        U32.add(w4, U32.mul(w, m4)), U32.add(w5, U32.mul(w, m5)), U32.add(w6, U32.mul(w, m6)), U32.add(w7, U32.mul(w, m7)), U32.add(t, it)}

def bkt(+it: U32, +tu: U32) -> U32:
  U32.min(U32.div(U32.mul(it, 8), tu), 7)

def pixel(a: Acc, +i: U32, +tn: Nat, +tu: U32) -> Acc:
  +it = pix(i, tn)
  add(a, i, it, bkt(it, tu))

# a leaf: n pixels from i, each lanes.n() on
def leaf(n: Nat, +i: U32, +tn: Nat, +tu: U32, a: Acc) -> Acc:
  match n:
    case 0n:
      a
    case 1n+p:
      leaf(p, U32.add(i, lanes.n()), tn, tu, pixel(a, i, tn, tu))

def zip(a: Acc, b: Acc) -> Acc:
  match a b:
    case A{a0, a1, a2, a3, a4, a5, a6, a7, x0, x1, x2, x3, x4, x5, x6, x7, at} A{b0, b1, b2, b3, b4, b5, b6, b7, y0, y1, y2, y3, y4, y5, y6, y7, bt}:
      A{U32.add(a0, b0), U32.add(a1, b1), U32.add(a2, b2), U32.add(a3, b3), U32.add(a4, b4), U32.add(a5, b5), U32.add(a6, b6), U32.add(a7, b7),
        U32.add(x0, y0), U32.add(x1, y1), U32.add(x2, y2), U32.add(x3, y3), U32.add(x4, y4), U32.add(x5, y5), U32.add(x6, y6), U32.add(x7, y7), U32.add(at, bt)}

def sweep(+d: Nat, +i: U32, +tn: Nat, +tu: U32) -> Acc:
  match d:
    case 0n:
      leaf(per.leaf(), i, tn, tu, A{0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0})
    case 1n+p:
      a b = sweep(p, i, tn, tu) sweep(p, U32.add(i, U32.shln(1, p)), tn, tu)
      zip(a, b)

# the colours (cumulative count * 255 / pixels) mixed as the published program's LUT hash, then applied
# to the weighted sums
def rend.mix(a: Acc) -> U32:
  match a:
    case A{+c0, c1, c2, c3, c4, c5, c6, c7, w0, w1, w2, w3, w4, w5, w6, w7, t}:
      +s1 = U32.add(c0, c1)
      +s2 = U32.add(s1, c2)
      +s3 = U32.add(s2, c3)
      +s4 = U32.add(s3, c4)
      +s5 = U32.add(s4, c5)
      +s6 = U32.add(s5, c6)
      +s7 = U32.add(s6, c7)
      +l0 = U32.div(U32.mul(c0, 255), s7)
      +l1 = U32.div(U32.mul(s1, 255), s7)
      +l2 = U32.div(U32.mul(s2, 255), s7)
      +l3 = U32.div(U32.mul(s3, 255), s7)
      +l4 = U32.div(U32.mul(s4, 255), s7)
      +l5 = U32.div(U32.mul(s5, 255), s7)
      +l6 = U32.div(U32.mul(s6, 255), s7)
      +l7 = U32.div(U32.mul(s7, 255), s7)
      m1 = U32.add(U32.mul(l0, 2654435761), l1)
      m2 = U32.add(U32.mul(m1, 2654435761), l2)
      m3 = U32.add(U32.mul(m2, 2654435761), l3)
      m4 = U32.add(U32.mul(m3, 2654435761), l4)
      m5 = U32.add(U32.mul(m4, 2654435761), l5)
      m6 = U32.add(U32.mul(m5, 2654435761), l6)
      m7 = U32.add(U32.mul(m6, 2654435761), l7)
      r = U32.add(t, U32.add(U32.add(U32.add(U32.mul(l0, w0), U32.mul(l1, w1)), U32.add(U32.mul(l2, w2), U32.mul(l3, w3))),
        U32.add(U32.add(U32.mul(l4, w4), U32.mul(l5, w5)), U32.add(U32.mul(l6, w6), U32.mul(l7, w7)))))
      U32.add(U32.mul(m7, 2654435761), r)

def rend(+tn: Nat) -> U32:
  rend.mix(sweep(lanes(), 0, tn, U32.from_nat(tn)))

def its() -> Nat:
  51n

# expect 3101455856, as the published program
def main() -> IO(Unit):
  IO.print(U32.show(rend!(its())))
