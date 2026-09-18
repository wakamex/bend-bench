import Base

# Balanced rows with cached boundary values; runtime chooses CPU/GPU scheduling.
type Coeff is Data:
  Coeff{cap: F32, rx: F32, ry: F32, rz: F32}
type Row is Data:
  Cell{temp: F32, power: F32}
  Columns{first: F32, last: F32, left: Row, right: Row}
type Grid is Data:
  Single{row: Row}
  Rows{first: Row, last: Row, upper: Grid, lower: Grid}

def first(r: Row) -> F32:
  match r:
    case Cell{t, _}: t
    case Columns{f, _, _, _}: f

def last(r: Row) -> F32:
  match r:
    case Cell{t, _}: t
    case Columns{_, l, _, _}: l

def grid_first(g: Grid) -> Row:
  match g:
    case Single{r}: r
    case Rows{f, _, _, _}: f

def grid_last(g: Grid) -> Row:
  match g:
    case Single{r}: r
    case Rows{_, l, _, _}: l

def row_join(+a: Row, +b: Row) -> Row:
  Columns{first(a), last(b), a, b}

def grid_join(+a: Grid, +b: Grid) -> Grid:
  Rows{grid_first(a), grid_last(b), a, b}

def cell_step(+t: F32, p: F32, n: F32, s: F32, w: F32, e: F32, k: Coeff) -> F32:
  Coeff{cap, rx, ry, rz} = k
  vertical = F32.mul(F32.sub(F32.add(s, n), F32.mul(2.0, t)), ry)
  horizontal = F32.mul(F32.sub(F32.add(e, w), F32.mul(2.0, t)), rx)
  ambient = F32.mul(F32.sub(80.0, t), rz)
  F32.add(t, F32.mul(cap, F32.add(F32.add(F32.add(p, vertical), horizontal), ambient)))

def row_step(r: Row, n: Row, s: Row, w: F32, e: F32, +k: Coeff) -> Row:
  match r n s:
    case Cell{t, +p} Cell{nt, _} Cell{st, _}:
      Cell{cell_step(t, p, nt, st, w, e, k), p}
    case Columns{_, _, +left, +right} Columns{_, _, na, nb} Columns{_, _, sa, sb}:
      a b = row_step(left, na, sa, w, first(right), k) row_step(right, nb, sb, last(left), e, k)
      row_join(a, b)
    case _ _ _:
      Cell{F32.div(0.0, 0.0), 0.0}

def grid_step(g: Grid, n: Row, s: Row, +k: Coeff) -> Grid:
  match g:
    case Single{+r}:
      Single{row_step(r, n, s, first(r), last(r), k)}
    case Rows{_, _, +left, +right}:
      a b = grid_step(left, n, grid_first(right), k) grid_step(right, grid_last(left), s, k)
      grid_join(a, b)

def solve(steps: Nat, +grid: Grid, +k: Coeff) -> Grid:
  match steps:
    case 0n: grid
    case 1n+rest:
      next = grid_step(grid, grid_first(grid), grid_last(grid), k)
      solve(rest, next, k)

def parse_value(v: Maybe<&2, F32>) -> F32:
  match v:
    case Some{v}: v
    case None{}: F32.div(0.0, 0.0)

def row_done(a: Row, right: Row & (List<&2, String> & List<&2, String>)) -> Row & (List<&2, String> & List<&2, String>):
  (b, tail) = right
  (row_join(a, b), tail)

def row_then(left: Row & (List<&2, String> & List<&2, String>),
             next: List<&2, String> -> List<&2, String> -> Row & (List<&2, String> & List<&2, String>)) -> Row & (List<&2, String> & List<&2, String>):
  (a, (ta, pa)) = left
  row_done(a, next(ta, pa))

def load_row(d: Nat, ts: List<&2, String>, ps: List<&2, String>) -> Row & (List<&2, String> & List<&2, String>):
  match d:
    case 0n:
      match ts ps:
        case Con{t, tr} Con{p, pr}:
          (Cell{parse_value(F32.read(t)), parse_value(F32.read(p))}, (tr, pr))
        case _ _:
          (Cell{F32.div(0.0, 0.0), 0.0}, (Nil{}, Nil{}))
    case 1n+q:
      +depth = q
      row_then(load_row(depth, ts, ps), ta => pa => load_row(depth, ta, pa))

def grid_leaf(value: Row & (List<&2, String> & List<&2, String>)) -> Grid & (List<&2, String> & List<&2, String>):
  (r, tail) = value
  (Single{r}, tail)

def grid_done(a: Grid, right: Grid & (List<&2, String> & List<&2, String>)) -> Grid & (List<&2, String> & List<&2, String>):
  (b, tail) = right
  (grid_join(a, b), tail)

def grid_then(left: Grid & (List<&2, String> & List<&2, String>),
              next: List<&2, String> -> List<&2, String> -> Grid & (List<&2, String> & List<&2, String>)) -> Grid & (List<&2, String> & List<&2, String>):
  (a, (ta, pa)) = left
  grid_done(a, next(ta, pa))

def load_grid(d: Nat, +width: Nat, ts: List<&2, String>, ps: List<&2, String>) -> Grid & (List<&2, String> & List<&2, String>):
  match d:
    case 0n: grid_leaf(load_row(width, ts, ps))
    case 1n+q:
      +depth = q
      grid_then(load_grid(depth, width, ts, ps), ta => pa => load_grid(depth, width, ta, pa))

def row_output(r: Row, tail: String) -> String:
  match r:
    case Cell{t, _}: U32.show(F32.bits(t)) ++ "\n" ++ tail
    case Columns{_, _, a, b}: row_output(a, row_output(b, tail))

def grid_output(g: Grid, tail: String) -> String:
  match g:
    case Single{r}: row_output(r, tail)
    case Rows{_, _, a, b}: grid_output(a, grid_output(b, tail))

def read_done(pair: File & Result<&1, &1, U32 & String, String>) -> IO(String):
  (file, result) = pair
  do IO<String>:
    Unit <- File.close(file)
    IO.pass(String, result)

def read_file(path: String) -> IO(String):
  do IO<String>:
    f : File <- IO.try(File, File.open(path, "r"))
    pair : File & Result<&1, &1, U32 & String, String> <- File.read(f, 33554432)
    read_done(pair)

def run_grid(value: Grid & (List<&2, String> & List<&2, String>)) -> IO(Unit):
  (g, _) = value
  result = solve!(10n, g, Coeff{0.0, 0.0, 0.0, 0.0})
  IO.print(grid_output(result, ""))

def main() -> IO(Unit):
  do IO<Unit>:
    ts : String <- read_file("temp.txt")
    ps : String <- read_file("power.txt")
    run_grid(load_grid(6n, 6n, String.lines(ts), String.lines(ps)))
