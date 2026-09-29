"""Generated compile-time stress programs for Bend's native inline rule.

Each program is built of large U32 functions (natives) that NVRTC would copy
into every call site if they were inlined: flatmany calls four loop-free ones
32 times each, flatchain chains ten loop-free ones that each call the next
twice, and loopchain chains twelve looping ones the same way. A fork tree
under `!` reaches them, so every build compiles them for the CPU and the GPU.
They are build-only: loopchain's running time grows exponentially.

python -m bend_bench.compile_stress OUT_DIR
"""
from pathlib import Path
import sys

LETS = 300  # U32 lets per function, several emitted C lines each


def body(x, tag):
    lines, prev, cur = [], x, x
    for j in range(LETS):
        name = f'{tag}{j}'
        lines.append(f'  +{name} = U32.xor(U32.mul({cur}, {2654435761 + j}), U32.add({prev}, {j * 7919 + 1}))')
        prev, cur = cur, name
    return lines, cur


def tree(call):
    return f'''
def tree(+d: Nat, +b: U32) -> U32:
  match d:
    case 0n:
      {call}
    case 1n+p:
      l r = tree(p, b) tree(p, U32.add(b, U32.shln(1, p)))
      U32.add(l, r)

def main() -> IO(Unit):
  IO.print(U32.show(tree!(10n, 0)))
'''


def flatmany(k=4, m=32):
    src = ['import Base', '']
    for i in range(k):
        lines, last = body('x', f'f{i}_')
        src += [f'def big{i}(+x: U32) -> U32:', *lines, f'  {last}', '']
    calls = [f'big{i}(U32.add(b, {c}))' for i in range(k) for c in range(m)]
    work = calls[-1]
    for c in reversed(calls[:-1]):
        work = f'U32.add({c}, {work})'
    src += ['def work(+b: U32) -> U32:', f'  {work}', '']
    return '\n'.join(src) + tree('work(b)')


def flatchain(k=10):
    # A def must precede its first use, so the chain is written from its end.
    src = ['import Base', '']
    for i in reversed(range(k)):
        lines, last = body('x', f'c{i}_')
        tail = f'U32.add(ch{i + 1}({last}), ch{i + 1}(U32.inc({last})))' if i + 1 < k else last
        src += [f'def ch{i}(+x: U32) -> U32:', *lines, f'  {tail}', '']
    return '\n'.join(src) + tree('ch0(b)')


def loopchain(k=12):
    src = ['import Base', '']
    for i in reversed(range(k)):
        lines, last = body('x', f'l{i}_')
        nxt = f'U32.add(lp{i + 1}(2n, {last}), lp{i + 1}(3n, U32.inc({last})))' if i + 1 < k else last
        src += [f'def lp{i}(n: Nat, +x: U32) -> U32:', '  match n:', '    case 0n:', '      x', '    case 1n+p:',
                *['    ' + line for line in lines], f'    +nx = {nxt}', f'    lp{i}(p, nx)', '']
    return '\n'.join(src) + tree('lp0(2n, b)')


PROGRAMS = {'flatmany': flatmany, 'flatchain': flatchain, 'loopchain': loopchain}


def write(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, make in PROGRAMS.items():
        path = folder / f'stress-{name}.bend'
        path.write_text(make() + '\n')
        paths.append(path)
    return paths


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -m bend_bench.compile_stress OUT_DIR')
    for path in write(sys.argv[1]):
        print(path)
