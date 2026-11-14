#!/bin/bash
# Compare two Bend checkouts on an Apple-silicon Mac (Metal backend).
#
#   metal/compare.sh BASE CANDIDATE > metal.log
#   uv run bend-bench metal-report metal.log
#
# BASE and CANDIDATE are Bend checkouts. It runs with macOS /bin/bash 3.2; bun, perl and bc must be on PATH. The log has,
# for base then candidate: every test that uses a bang call, run with --gpu on against its
# #| expectation; each program in metal/probes with its wall time and last output line;
# then, for every bench/runtime program in the candidate, `bend -o` and `+RTS --gpu-build`
# times over 7 runs a side in alternating order, an output comparison, and runtimes in
# 4 blocks of A B B A / B A A B (A is base, B is candidate).
set -u
[ $# -eq 2 ] || { echo "usage: $0 BASE CANDIDATE" >&2; exit 2; }
base=$(cd "$1" && pwd) candidate=$(cd "$2" && pwd)
dir() { [ "$1" = base ] && echo "$base" || echo "$candidate"; }
probes=$(cd "$(dirname "$0")/probes" && pwd)
work=$(mktemp -d)
T() { perl -MTime::HiRes=time -e 'printf "%.4f", time'; }
compile() { (cd "$2" && bun "$(dir $1)/bend2/main.ts" "$3" -o "$4" > /dev/null 2>&1); }
echo "== bang tests"
for v in base candidate; do
  for t in $(grep -rlE '[a-zA-Z_.]!\(' "$(dir $v)/tests" --include=*.bend | sort); do
    want=$(grep '^#|' "$t" | sed 's/^#|//'); n=$(basename "$t" .bend)
    compile $v "$(dir $v)" "$t" "$work/t-$v-$n" || { echo "BUILDFAIL $v $n"; continue; }
    got=$(cd "$(dirname "$t")" && "$work/t-$v-$n" +RTS --gpu on 2>&1; c=$?; [ $c -ne 0 ] && echo "exit $c")
    [ "$got" == "$want" ] && echo "PASS $v $n" || echo "FAIL $v $n"
  done
done
echo "== programs"
for p in "$probes"/*.bend; do
  n=$(basename "$p" .bend)
  for v in base candidate; do
    compile $v "$(dir $v)" "$p" "$work/p-$v-$n" || { echo "BUILDFAIL $v $n"; continue; }
    t0=$(T); r=$("$work/p-$v-$n" +RTS --gpu on 2>&1 | tail -1); t1=$(T)
    echo "prog $n $v $(echo "$t1 - $t0" | bc) $r"
  done
done
B=$(ls "$candidate/bench/runtime" | grep -v _pin_)
echo "== build"
for b in $B; do
  for v in base candidate; do compile $v "$(dir $v)/bench/runtime/$b" main.bend "$work/run-$v-$b"; done
  for i in 1 2 3 4 5 6 7; do
    for v in $([ $((i % 2)) = 1 ] && echo "base candidate" || echo "candidate base"); do
      d=$(dir $v)/bench/runtime/$b
      t0=$(T); compile $v "$d" main.bend "$work/run-$v-$b"; t1=$(T)
      (cd "$d" && "$work/run-$v-$b" +RTS --gpu-build > /dev/null); t2=$(T)
      echo "build $b $v $i $(echo "$t1 - $t0" | bc) $(echo "$t2 - $t1" | bc)"
    done
  done
done
echo "== runtime"
for b in $B; do
  for v in base candidate; do (cd "$(dir $v)/bench/runtime/$b" && "$work/run-$v-$b" > "$work/out-$v-$b.txt" 2>&1); done
  cmp -s "$work/out-base-$b.txt" "$work/out-candidate-$b.txt" && echo "same-output $b" || echo "DIFF-output $b"
done
for blk in 1 2 3 4; do
  for b in $B; do for v in $([ $((blk % 2)) = 1 ] && echo "base candidate candidate base" || echo "candidate base base candidate"); do
    t0=$(T); (cd "$(dir $v)/bench/runtime/$b" && "$work/run-$v-$b" > /dev/null 2>&1); t1=$(T)
    echo "run $blk $b $v $(echo "$t1 - $t0" | bc)"
  done; done
done
rm -rf "$work"
echo DONE
