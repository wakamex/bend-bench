"""Grow each published workload until the conventional GPU program's startup no longer dominates.

At the published sizes the conventional GPU programs spend milliseconds on the device inside about
0.2 s of process time, so a Bend GPU / CUDA ratio there mostly compares startup. This sweep runs the
scorecard's Bend revision and conventional GPU programs with one work knob scaled by doubling
multipliers. At each size the conventional output is checked against the serial C in its verify mode
while that fits the budget, and the Bend GPU checksum must equal the conventional one. Timing is one
warmup per implementation, then paired rounds in seeded random order. A workload stops growing once
the marginal ratio (scaling_fit.marginal_ratio: Bend's added time per unit of work over the conventional
program's, from fitted curves) holds within 3% without its newest size and the conventional GPU work is
at least half its time, or at its largest valid size. The settle check needs numpy and scipy:

uv run --locked --with numpy --with scipy python startup_scaling.py --workloads NAME ...
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import statistics
import time

from bend_bench.core import append, correct, environment, exclusive, execute, hash_file, load_config, write_json
from bend_bench.hotspot import stage_rodinia
from scorecard_paired_cpu import gpu_clear

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'src/bend_bench/assets'
CUDA = '/usr/local/cuda-13.1'
CC = '/usr/bin/clang-22'  # the scorecard's Bend builds; project CUDA used clang++ (same clang 22)
FLAGS = ['-O3', '-march=native', '-ffp-contract=off']
CCCL = ROOT / 'sources/cccl-clang'
CUDF = ROOT / 'dependencies/cudf/.venv/lib/python3.13/site-packages'
CLANG_CUDA = ['/usr/bin/clang++', '-std=c++17', *FLAGS, f'--cuda-path={CUDA}', '--cuda-gpu-arch=sm_86',
              '-Wno-unknown-cuda-version']
RODINIA = Path('/code/bend2/rodinia/rodinia_3.1')
HOTSPOT_INPUTS = [RODINIA / 'data/hotspot' / f'{kind}_1024' for kind in ('temp', 'power')]


def nat(k):
    """k as a Bend Nat expression: 2.0.3 expands a literal into a Succ chain, and 8192n overflows its stack."""
    return f'{k}n' if k <= 64 else f'Nat.mul(64n, {nat(k // 64)})' if k % 64 == 0 else f'Nat.mul({k % 64 or 64}n, {nat(k // (k % 64 or 64))})'


def lexer_template(k):
    """The lexer's line template with 3k expression groups (the published line has 3)."""
    return 'i = ' + ' o '.join(['( n o i )'] * (3 * k)) + ' ;'


def depth(base, k):
    return base + k.bit_length() - 1


# Conventional GPU builds, as the harness does them (suites.py): project CUDA, CUB, cuBLAS and cuDF.
def cuda_builder(folder, source, bend, program):
    return [[*CLANG_CUDA, f'-I{bend}/bench/runtime/{program}', source, f'-L{CUDA}/lib64', f'-Wl,-rpath,{CUDA}/lib64',
             '-lcudart', '-o', folder / 'cuda']]


def cub_builder(folder, source, bend, program):
    return [[*CLANG_CUDA, f'-I{CCCL}/cub', f'-I{CCCL}/thrust', f'-I{CCCL}/libcudacxx/include', f'-I{bend}/bench/runtime/{program}',
             source, f'-L{CUDA}/lib64', '-lcudart', '-o', folder / 'cuda']]


def cublas_builder(folder, source, bend, program):
    return [[*CLANG_CUDA, f'-I{bend}/bench/runtime/{program}', source, f'-L{CUDA}/lib64', f'-Wl,-rpath,{CUDA}/lib64',
             '-lcudart', '-lcublas', '-o', folder / 'cuda']]


def hotspot_builder(folder, source, bend, program):
    return [[*CLANG_CUDA, '-DHOTSPOT_CUDA', f'-I{RODINIA}/cuda/hotspot', '-x', 'cuda', source, f'-L{CUDA}/lib64',
             f'-Wl,-rpath,{CUDA}/lib64', '-lcudart', '-o', folder / 'cuda']]


def cudf_builder(folder, source, bend, program):
    includes = [CUDF / 'libcudf/include', CUDF / 'libcudf/include/rapids', CUDF / 'librmm/include',
                CUDF / 'rapids_logger/include', Path(CUDA) / 'include', bend / 'bench/runtime' / program]
    libraries = [CUDF / p for p in ('libcudf/lib64', 'librmm/lib64', 'rapids_logger/lib64', 'libkvikio/lib64',
                                    'libkvikio_cu13.libs', 'nvidia/libnvcomp/lib64', 'nvidia/cu13/lib')] + [Path(CUDA) / 'lib64']
    return [['/usr/bin/g++', '-std=c++20', *FLAGS, *[f'-I{p}' for p in includes], source,
             *[f'-L{p}' for p in libraries], '-Wl,--disable-new-dtags', '-Wl,-rpath,' + ':'.join(map(str, libraries)),
             '-Wl,--no-as-needed', '-lcudf', '-lrmm', '-lrapids_logger', '-lkvikio', '-l:libnvcomp.so.5', '-lcudart',
             '-Wl,--as-needed', '-o', folder / 'cuda']]


# Hash tables: the original launches one grid row per table (gridDim.y <= 65535, so at most 2^15 tables)
# and allocates 144 KiB of device state per table. The sweep copy runs the same kernels over chunks of at
# most 2048 tables (the published count, so 1x is one chunk and the same device sequence), sums the
# per-chunk event intervals and verifies per chunk.
HASHMAP_CHUNKS = [
    ('__global__ void insert_keys(uint32_t *slots,uint32_t *lengths,uint32_t count) {',
     '__global__ void insert_keys(uint32_t *slots,uint32_t *lengths,uint32_t count,uint32_t first) {'),
    ('uint32_t key=key_for((t+1)*2654435761u,j),', 'uint32_t key=key_for((first+t+1)*2654435761u,j),'),
    ('__global__ void lookups(const uint32_t *slots,uint32_t *hits,uint32_t count) {',
     '__global__ void lookups(const uint32_t *slots,uint32_t *hits,uint32_t count,uint32_t first) {'),
    ('key_for(random_word((t+1)*2654435761u),j)', 'key_for(random_word((first+t+1)*2654435761u),j)'),
    ('''  uint32_t tables=1u<<depth,*slots,*lengths,*hits,*out;
  CUDA(cudaMalloc(&slots,size_t(tables)*SLOTS*4)); CUDA(cudaMalloc(&lengths,size_t(tables)*4096*4));
  CUDA(cudaMalloc(&hits,tables*4)); CUDA(cudaMalloc(&out,tables*4));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  CUDA(cudaMemset(slots,0,size_t(tables)*SLOTS*4)); CUDA(cudaMemset(lengths,0,size_t(tables)*4096*4)); CUDA(cudaMemset(hits,0,tables*4));
  if(count) {
    insert_keys<<<dim3((count+255)/256,tables),256>>>(slots,lengths,count); CUDA(cudaGetLastError());
    lookups<<<dim3((count+255)/256,tables),256>>>(slots,hits,count); CUDA(cudaGetLastError());
  }
  fold_tables<<<(tables+127)/128,128>>>(lengths,hits,out,tables); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\\n",ms/1000.0);
  std::vector<uint32_t> values(tables); CUDA(cudaMemcpy(values.data(),out,tables*4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> bucket_lengths(size_t(tables)*4096),actual_hits(tables);
    CUDA(cudaMemcpy(bucket_lengths.data(),lengths,bucket_lengths.size()*4,cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(actual_hits.data(),hits,tables*4,cudaMemcpyDeviceToHost));
    for(uint32_t t=0;t<tables;t++) {
      if(values[t]!=table_run(t,count)) { fprintf(stderr,"Table mismatch %u\\n",t); return 3; }
      for(uint32_t b=0;b<4096;b++) if(bucket_lengths[size_t(t)*4096+b]!=table_len(&tab,b)) return 4;
      uint32_t expected_hits=0,s=word_prng((t+1)*2654435761u);
      for(uint32_t j=0;j<count;j++) { uint32_t key=draw_key(s,j); expected_hits+=table_has(&tab,key&4095,key); }
      if(actual_hits[t]!=expected_hits) return 5;
    }
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\\n",tables*4096);
  }
  uint32_t result=0; for(uint32_t v:values) result+=v; printf("%u\\n",result);''',
     '''  uint32_t tables=1u<<depth,chunk=tables<2048?tables:2048,*slots,*lengths,*hits,*out,result=0;
  CUDA(cudaMalloc(&slots,size_t(chunk)*SLOTS*4)); CUDA(cudaMalloc(&lengths,size_t(chunk)*4096*4));
  CUDA(cudaMalloc(&hits,chunk*4)); CUDA(cudaMalloc(&out,chunk*4));
  std::vector<uint32_t> values(chunk),bucket_lengths(verify?size_t(chunk)*4096:0),actual_hits(verify?chunk:0);
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  double total_ms=0;
  for(uint32_t first=0;first<tables;first+=chunk) {
    CUDA(cudaEventRecord(begin));
    CUDA(cudaMemset(slots,0,size_t(chunk)*SLOTS*4)); CUDA(cudaMemset(lengths,0,size_t(chunk)*4096*4)); CUDA(cudaMemset(hits,0,chunk*4));
    if(count) {
      insert_keys<<<dim3((count+255)/256,chunk),256>>>(slots,lengths,count,first); CUDA(cudaGetLastError());
      lookups<<<dim3((count+255)/256,chunk),256>>>(slots,hits,count,first); CUDA(cudaGetLastError());
    }
    fold_tables<<<(chunk+127)/128,128>>>(lengths,hits,out,chunk); CUDA(cudaGetLastError());
    CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
    float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); total_ms+=ms;
    CUDA(cudaMemcpy(values.data(),out,chunk*4,cudaMemcpyDeviceToHost));
    if(verify) {
      CUDA(cudaMemcpy(bucket_lengths.data(),lengths,bucket_lengths.size()*4,cudaMemcpyDeviceToHost));
      CUDA(cudaMemcpy(actual_hits.data(),hits,chunk*4,cudaMemcpyDeviceToHost));
      for(uint32_t i=0;i<chunk;i++) {
        uint32_t t=first+i;
        if(values[i]!=table_run(t,count)) { fprintf(stderr,"Table mismatch %u\\n",t); return 3; }
        for(uint32_t b=0;b<4096;b++) if(bucket_lengths[size_t(i)*4096+b]!=table_len(&tab,b)) return 4;
        uint32_t expected_hits=0,s=word_prng((t+1)*2654435761u);
        for(uint32_t j=0;j<count;j++) { uint32_t key=draw_key(s,j); expected_hits+=table_has(&tab,key&4095,key); }
        if(actual_hits[i]!=expected_hits) return 5;
      }
    }
    for(uint32_t v:values) result+=v;
  }
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\\n",total_ms/1000);
  if(verify) fprintf(stderr,"FULL_OUTPUT_VERIFIED=%llu\\n",(unsigned long long)tables*4096);
  printf("%u\\n",result);'''),
]

# Ray tracing: pixel indices exceed 2^32 from 16x the side (6000*4096*256 = 6.3e9); 64-bit indices at
# every size keep one kernel, with the same device time and checksums as the 32-bit one where both run.
RAYTRACE64 = [('for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<w*h;i+=gridDim.x*blockDim.x) {',
               'for(uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;i<uint64_t(w)*h;i+=uint64_t(gridDim.x)*blockDim.x) {'),
              ('uint32_t height=1u<<depth,n=width*height,*sum,*values=nullptr;',
               'uint32_t height=1u<<depth,*sum,*values=nullptr; uint64_t n=uint64_t(width)*height;'),
              ('for(uint32_t i=0;i<n;i++) {', 'for(uint64_t i=0;i<n;i++) {'),
              ('Pixel mismatch %u: %u != %u\\n",i,', 'Pixel mismatch %llu: %u != %u\\n",(unsigned long long)i,'),
              ('FULL_OUTPUT_VERIFIED=%u\\n",n);', 'FULL_OUTPUT_VERIFIED=%llu\\n",(unsigned long long)n);')]

# Option pricing and game search, as whole programs: the scorecard's quote-only and batch programs
# (pricing_sustained, mnk_sustained), built to answer one request or batch per process.
APPLICATIONS = Path(__file__).resolve().parent / 'applications.toml'


def pricing_prepare(folder, k):
    """Bend GPU and CUDA + CUB pricing of 262,144k paths, one quote each; the OpenMP quote is the reference."""
    from pricing_sustained import prepare
    config = load_config(APPLICATIONS)
    config.update(suites=['pricing'], threads=[16], pricing_steps=[256])
    cases = {c['implementation']: c for c in prepare(config, folder / 'work', 17 + k.bit_length(), 256, 1)}
    return {impl: (cases[case]['command'], cases[case].get('env', {}))
            for impl, case in (('bend', 'bend-cuda'), ('cuda', 'local-cuda'), ('reference', 'local-openmp'))}


def pricing_check(result, k):
    from pricing_sustained import parse
    quotes, _, times = parse(result, 262144 * k, 1)
    return quotes[0], times[0]


def pricing_agree(a, b):
    from pricing_sustained import compare_quotes
    try:
        compare_quotes([a], [b])
    except ValueError:
        return False
    return True


def game_prepare(folder, k):
    """Bend GPU and the tight-bound one-thread-per-position CUDA control on one batch of 524,288k positions
    from the 1,024-position corpus; answers are checked against the corpus oracle."""
    from bend_bench.suites import plan, stage
    from mnk_sustained import bend_resident, bulk_variants, control_variants, cpp_resident
    config = load_config(APPLICATIONS)
    config.update(suites=['mnk'], mnk_games=[[5, 5, 4, 8]], threads=[16])
    work, count = folder / 'work', 524288 * k
    work.mkdir()
    (work / 'build').mkdir()
    stage(config, work, mnk_count=1024)
    source = work / 'ports/mnk-5-5-4-8.bend'
    source.write_text(bend_resident(source.read_text(), 18 + k.bit_length(), 1, 1024))
    cpp = work / 'gpu/mnk.cpp'
    cpp.write_text(cpp_resident(cpp.read_text(), count, 1, 1024))
    builds, cases = plan(config, work)
    control_variants(builds, cases)
    bulk_variants(builds, cases)
    for command in builds:
        result = execute(command, timeout=900)
        append(folder / 'build.jsonl', logged(result))
        if result['returncode']:
            raise RuntimeError(f'game search x{k}: build failed: {command[0]}\n{result["stderr"][-2000:]}')
    (folder / 'expected.json').write_text(source.with_suffix('.json').read_text())
    cases = {c['implementation']: c for c in cases}
    return {impl: (cases[case]['command'], {}) for impl, case in (('bend', 'bend-cuda'), ('cuda', 'local-alpha-beta-position-tight-bulk-cuda'))}


def game_check(result, k, folder):
    """Every answer against the oracle (batch 0 starts at corpus offset 11); the search interval from stderr."""
    expected = json.loads((folder / 'expected.json').read_text())
    lines = result['stdout'].split('\n')
    if lines[0] != 'READY' or lines[-2:] != ['END', ''] or len(lines) != 524288 * k + 3:
        raise ValueError('incomplete game-search batch')
    for i, line in enumerate(lines[1:-2]):
        if line != str(expected[(i + 11) % len(expected)]):
            raise ValueError(f'game-search answer {i} differs from the oracle')
    phase = next(line.split() for line in result['stderr'].splitlines() if line.startswith(('PHASE_NS ', 'PHASE_MS ')))
    scale = 1e9 if phase[0] == 'PHASE_NS' else 1e3
    return hashlib.sha256(result['stdout'].encode()).hexdigest(), (int(phase[2]) - int(phase[1])) / scale


# Each entry: bend(k) and patch(k) are exact text replacements in main.bend and the conventional source
# (defaults and argument caps: timed runs cannot pass sizes); args(k) and verify(k) are its arguments.
# Optional: source (the bench/runtime program), serial (replacements in its main.c), builder, max (largest valid multiplier), share (device
# share required before the fitted ratio can stop the sweep), verify_until (largest serially checked
# size), work (work relative to the published size, when it is not the multiplier itself).
WORKLOADS = {
    'mandelbrot': dict(knob='iterations', base=51, grow=lambda k: 51 * k, cuda='gpu/vendor-mandelbrot.cu',
        bend=lambda k: [('def its() -> Nat:\n  51n', f'def its() -> Nat:\n  Nat.mul(51n, {nat(k)})')],
        patch=lambda k: [('uint32_t depth=18,steps=51;', f'uint32_t depth=18,steps={51 * k};'),
                         ('v<1 || v>51)', f'v<1 || v>{51 * k})')],
        args=lambda k: []),
    'merkle': dict(knob='tree depth', base=22, grow=lambda k: 22 + k.bit_length() - 1, cuda='gpu/vendor-merkle.cu',
        bend=lambda k: [('build!(22n, 0)', f'build!({21 + k.bit_length()}n, 0)'),
                        ('pgen!(22n, 1337, 0)', f'pgen!({21 + k.bit_length()}n, 1337, 0)')],
        patch=lambda k: [('uint32_t depth=22;', f'uint32_t depth={21 + k.bit_length()};'),
                         ('v>22) return 2;', f'v>{21 + k.bit_length()}) return 2;')],
        args=lambda k: [], max=16),  # 2^27 leaves exhaust Bend's 4 GB heap
    'merkle-blocks': dict(source='merkle', knob='blocks per leaf', base=30, grow=lambda k: 30 * k, cuda='gpu/vendor-merkle.cu',
        bend=lambda k: [('def blocks() -> Nat:\n  30n', f'def blocks() -> Nat:\n  Nat.mul(30n, {nat(k)})')],
        # Count BLOCKS iterations like the serial block_chain: the bound (b+1)*BLOCKS wraps past 2^32
        # leaf blocks (from 64x here), where the original loop would run zero times.
        patch=lambda k: [('#include <cuda_runtime.h>', f'#define BLOCKS {30 * k}\n#include <cuda_runtime.h>'),
                         ('for(uint32_t block=b*BLOCKS;block<(b+1)*BLOCKS;block++) {',
                          'for(uint32_t j=0,block=b*BLOCKS;j<BLOCKS;j++,block++) {')],
        args=lambda k: []),
    'nbody': dict(knob='simulation steps', base=300, grow=lambda k: 300 * k, cuda='gpu/vendor-nbody.cu',
        bend=lambda k: [('def st() -> Nat:\n  300n', f'def st() -> Nat:\n  Nat.mul(300n, {nat(k)})')],
        patch=lambda k: [('uint32_t depth=17,steps=300;', f'uint32_t depth=17,steps={300 * k};'),
                         ('v>(i==2?17u:300u)', f'v>(i==2?17u:{300 * k}u)')],
        args=lambda k: []),
    'gameoflife': dict(knob='soups (2^depth)', base=18, grow=lambda k: 17 + k.bit_length(), cuda='baselines/gameoflife-cuda.cu',
        bend=lambda k: [('def size() -> Nat:\n  18n', f'def size() -> Nat:\n  {17 + k.bit_length()}n')],
        # the argument cap is the only limit on soups; depth 26 needs 1 GiB of census arrays
        patch=lambda k: [('if (depth > 24) return 2;', 'if (depth > 26) return 2;')], args=lambda k: [str(17 + k.bit_length())],
        verify=None, max=256),
    'bfs': dict(knob='mazes (2^depth)', base=19, grow=lambda k: 18 + k.bit_length(), cuda='gpu/vendor-bfs.cu',
        bend=lambda k: [('def size() -> Nat:\n  19n', f'def size() -> Nat:\n  {18 + k.bit_length()}n')],
        # depth 31 (4096x) is the last u32 maze count (n=1u<<depth); batches of 4096 mazes bound device memory
        patch=lambda k: [('uint32_t depth=19;', f'uint32_t depth={18 + k.bit_length()};'),
                         ('v>19) return 2;', f'v>{18 + k.bit_length()}) return 2;')],
        args=lambda k: [], max=4096),
    'hashmap': dict(knob='tables (2^depth)', base=11, grow=lambda k: 10 + k.bit_length(), cuda='gpu/vendor-hashmap.cu',
        bend=lambda k: [('def tables() -> Nat:\n  11n', f'def tables() -> Nat:\n  {10 + k.bit_length()}n')],
        patch=lambda k: [('uint32_t depth=11,count=16384;', f'uint32_t depth={10 + k.bit_length()},count=16384;'),
                         ('v>(i==2?11u:16384u)', f'v>(i==2?{10 + k.bit_length()}u:16384u)'), *HASHMAP_CHUNKS],
        args=lambda k: []),
    'kmeans': dict(knob='Lloyd rounds', base=20, grow=lambda k: 20 * k, cuda='gpu/vendor-kmeans.cu',
        bend=lambda k: [('loop(20n, d,', f'loop(Nat.mul(20n, {nat(k)}), d,')],
        # every hard-coded 20 in the CUDA driver becomes ROUNDS (the launch loop, the verify trace and its replay)
        patch=lambda k: [('#include <cuda_runtime.h>', f'#define ROUNDS {20 * k}u\n#include <cuda_runtime.h>'),
                         ('cudaMalloc(&history,20*starts*8*4)', 'cudaMalloc(&history,size_t(ROUNDS)*starts*8*4)'),
                         ('for(uint32_t it=0;it<20;it++) {\n    assign', 'for(uint32_t it=0;it<ROUNDS;it++) {\n    assign'),
                         ('trace(20*starts*8)', 'trace(size_t(ROUNDS)*starts*8)'),
                         ('for(uint32_t it=0;it<20;it++) {\n        c=step', 'for(uint32_t it=0;it<ROUNDS;it++) {\n        c=step'),
                         ('if(it==19 &&', 'if(it==ROUNDS-1 &&'),
                         ('FULL_OUTPUT_VERIFIED=%u\\n",20*starts*8)',
                          'FULL_OUTPUT_VERIFIED=%llu\\n",(unsigned long long)ROUNDS*starts*8)')],
        args=lambda k: []),
    'lexer': dict(knob='lines (2^depth)', base=23, grow=lambda k: 22 + k.bit_length(), cuda='gpu/vendor-lexer.cu',
        bend=lambda k: [('def size.big() -> Nat:\n  23n', f'def size.big() -> Nat:\n  {22 + k.bit_length()}n')],
        # depth 31 (256x) is the last u32 line count (n=1u<<depth)
        patch=lambda k: [('uint32_t depth=23;', f'uint32_t depth={22 + k.bit_length()};'),
                         ('v>23) return 2;', f'v>{22 + k.bit_length()}) return 2;')],
        args=lambda k: [], max=256),
    # longer lines: 3k '( n o i )' groups per line instead of 3, the same token mix, 2^23 lines. Bend
    # builds each line as a string before lexing it; the line buffers of the CUDA kernel, its verify
    # loop and the serial main.c (which the CUDA program includes) grow to 128k bytes.
    'lexer-length': dict(source='lexer', knob='expression groups per line', base=3, grow=lambda k: 3 * k,
        cuda='gpu/vendor-lexer.cu',
        bend=lambda k: [('def tpl() -> String:\n  "i = ( n o i ) o ( n o i ) o ( n o i ) ;"',
                         f'def tpl() -> String:\n  "{lexer_template(k)}"')],
        patch=lambda k: [('__constant__ char pattern[]="i = ( n o i ) o ( n o i ) o ( n o i ) ;";',
                          f'__constant__ char pattern[]="{lexer_template(k)}";'),
                         ('char text[128];', f'char text[{128 * k}];'), ('char buf[128];', f'char buf[{128 * k}];')],
        serial=lambda k: [('static const char TPL[] = "i = ( n o i ) o ( n o i ) o ( n o i ) ;";',
                           f'static const char TPL[] = "{lexer_template(k)}";'),
                          ('char buf[128];', f'char buf[{128 * k}];')],
        args=lambda k: []),
    # four-row prefixes searched: min(limit, 17^4 = 83521) in both programs, so 8x is the full space (7.12x the base)
    'queens': dict(knob='four-row prefixes searched', base=11730, grow=lambda k: min(11730 * k, 17 ** 4), cuda='gpu/vendor-queens.cu',
        bend=lambda k: [('def limit() -> U32:\n  11730', f'def limit() -> U32:\n  {11730 * k}')],
        patch=lambda k: [('uint32_t size=17,limit=11730;', f'uint32_t size=17,limit={11730 * k};'),
                         ('v<1 || v>11730)', f'v<1 || v>{11730 * k})')],
        args=lambda k: [], max=8, work=lambda k: min(k, 17 ** 4 / 11730)),
    # board size at the full prefix space: 1x is 17 queens (the prefix sweep's 8x), 2x is 18, 4x is 19.
    # Both programs hash 2^17 task slots onto prefixes below size^4, which holds through 19 (130,321).
    'queens-board': dict(source='queens', knob='board size, every four-row prefix', base=17, grow=lambda k: 16 + k.bit_length(),
        cuda='gpu/vendor-queens.cu',
        bend=lambda k: [('def size() -> U32:\n  17', f'def size() -> U32:\n  {16 + k.bit_length()}'),
                        ('def limit() -> U32:\n  11730', f'def limit() -> U32:\n  {(16 + k.bit_length()) ** 4}')],
        patch=lambda k: [('uint32_t size=17,limit=11730;', f'uint32_t size={16 + k.bit_length()},limit={(16 + k.bit_length()) ** 4};'),
                         ('v<4 || v>17 : v<1 || v>11730)', f'v<4 || v>{16 + k.bit_length()} : v<1 || v>{(16 + k.bit_length()) ** 4})')],
        args=lambda k: [], max=4, verify_until=1),  # serial verification at 18 queens takes minutes
    # k is the linear resolution: width 6000k, 4096k rows, the same field of view, so k^2 the pixels
    'raytrace': dict(knob='image side (pixels = k^2 x 6000 x 4096)', base=6000, grow=lambda k: 6000 * k, cuda='gpu/vendor-raytrace.cu',
        bend=lambda k: [('def rows() -> Nat:\n  12n', f'def rows() -> Nat:\n  {11 + k.bit_length()}n'),
                        ('def width() -> U32:\n  6000', f'def width() -> U32:\n  {6000 * k}'),
                        ('colf(14n, 0,', f'colf({13 + k.bit_length()}n, 0,'),
                        ('U32.mul(x, 2654435761), 16383)', f'U32.mul(x, 2654435761), {(1 << (13 + k.bit_length())) - 1})')],
        patch=lambda k: [('uint32_t depth=12,width=6000;', f'uint32_t depth={11 + k.bit_length()},width={6000 * k};'),
                         ('(i==2?v>12:v<2 || v>6000)', f'(i==2?v>{11 + k.bit_length()}:v<2 || v>{6000 * k})'),
                         *RAYTRACE64],
        args=lambda k: [], max=32, verify_until=2, work=lambda k: k * k),  # Bend takes about 12 minutes per run at 32x the side
    # population 2^size: the parallel tournament grows; the sequential 32-round climb stays at 110 points
    'symreg': dict(knob='candidates (2^size)', base=18, grow=lambda k: 17 + k.bit_length(), cuda='gpu/vendor-symreg.cu',
        bend=lambda k: [('def size() -> Nat:\n  18n', f'def size() -> Nat:\n  {17 + k.bit_length()}n')],
        patch=lambda k: [('uint32_t depth=18,points=110;', f'uint32_t depth={17 + k.bit_length()},points=110;'),
                         ('v>(i==2?18u:110u)', f'v>(i==2?{17 + k.bit_length()}u:110u)')],
        args=lambda k: [], max=2048),  # the CUDA tree array needs 12.9 GB at 2048x (24 GB card, ~3 GB resident worker)
    'terrain': dict(knob='relaxation sweeps per tile', base=5, grow=lambda k: 5 * k, cuda='gpu/vendor-terrain.cu',
        bend=lambda k: [('def epass() -> Nat:\n  5n', f'def epass() -> Nat:\n  Nat.mul(5n, {nat(k)})')],
        patch=lambda k: [('uint32_t depth=16,passes=5;', f'uint32_t depth=16,passes={5 * k};'),
                         ('v>(i==2?16u:5u)', f'v>(i==2?16u:{5 * k}u)')],
        args=lambda k: [], max=2048),
    # Library comparisons. Bend's 4 GB heap faults at 2^28 sort keys, 2^24 radix keys and 16x matmul rounds.
    'tree-bitonic': dict(knob='keys (2^depth)', base=23, grow=lambda k: depth(23, k), cuda='gpu/cub.cu', builder=cub_builder,
        bend=lambda k: [('bsort!(23n,', f'bsort!({depth(23, k)}n,')],
        patch=lambda k: [('if(depth>26 ||', 'if(depth>27 ||')],
        args=lambda k: ['sort', str(depth(23, k))], verify=lambda k: ['sort', str(depth(23, k)), 'verify'], max=16),
    'tree-radix': dict(knob='keys (2^depth)', base=22, grow=lambda k: depth(22, k), cuda='gpu/vendor-radix.cu', builder=cub_builder,
        bend=lambda k: [('gen!(22n, 0)', f'gen!({depth(22, k)}n, 0)')],
        patch=lambda k: [('unsigned depth=22;', f'unsigned depth={depth(22, k)};'), ('value>22)', f'value>{depth(22, k)})')],
        args=lambda k: [], max=2),
    'tree-matmul': dict(knob='rounds of 128x128 GEMMs', base=384, grow=lambda k: 384 * k, cuda='gpu/vendor-matmul.cu', builder=cublas_builder,
        bend=lambda k: [('def blog() -> Nat:\n  9n', f'def blog() -> Nat:\n  {depth(9, k)}n'),
                        ('def nchain() -> U32:\n  384', f'def nchain() -> U32:\n  {384 * k}')],
        patch=lambda k: [('unsigned depth=7,batches=384;', f'unsigned depth=7,batches={384 * k};'),
                         ('count>384)', f'count>{384 * k})')],
        args=lambda k: [], max=8),
    # Rodinia HotSpot on its largest input: 100k timesteps on the 1,024 x 1,024 grid, pyramid height 1 as in
    # the scorecard. Bend and CUDA each print every cell, checked against the scalar reference. The driver
    # caps steps at 1,000.
    'hotspot': dict(knob='timesteps on the 1,024 x 1,024 grid', base=100, grow=lambda k: 100 * k, cuda='gpu/hotspot-driver.cpp',
        builder=hotspot_builder, patch=lambda k: [('steps<1 || steps>1000', f'steps<1 || steps>{max(1000, 100 * k)}')],
        args=lambda k: [1024, 100 * k, 1, *HOTSPOT_INPUTS], verify=None, expected_bits=True, max=256),
    # Whole programs: one quote of 262,144k paths (2^30 is the path cap), one batch of 524,288k positions.
    # The conventional GPU work is each program's own timed compute region (quote ready, search done).
    'pricing': dict(knob='paths per request (2^depth)', base=18, grow=lambda k: 17 + k.bit_length(), prepare=pricing_prepare,
        check=pricing_check, agree=pricing_agree, cuda='gpu/pricing.cpp', max=4096),
    'game-search': dict(knob='positions per batch (2^depth)', base=19, grow=lambda k: 18 + k.bit_length(), prepare=game_prepare,
        check=game_check, folder=True, oracle=True, cuda='gpu/mnk.cpp', max=64),
    # cuDF's serial host input generation grows with the pairs, so its device share levels off near 40%:
    # the ratio settles without the share threshold. int32 string offsets overflow at 2^23 pairs.
    'editdist': dict(knob='string pairs (2^depth)', base=15, grow=lambda k: depth(15, k), cuda='gpu/vendor-editdist.cpp', builder=cudf_builder,
        bend=lambda k: [('def size.big() -> Nat:\n  15n', f'def size.big() -> Nat:\n  {depth(15, k)}n')],
        patch=lambda k: [('unsigned depth=15;', f'unsigned depth={depth(15, k)};'), ('value>15)', f'value>{depth(15, k)})')],
        args=lambda k: [], max=128, share=0.0),
}


def run_logged(command, log):
    """A build-time command, logged with a hash in place of large output."""
    result = execute(command, timeout=900)
    append(log, logged(result))
    if result['returncode']:
        raise RuntimeError(f'failed: {command[0]}\n{result["stderr"][-2000:]}')
    return result


def logged(result):
    """HotSpot prints every cell (about 10 MB): logs keep a hash of such output."""
    if len(result['stdout']) > 1 << 20:
        return dict(result, stdout='sha256:' + hashlib.sha256(result['stdout'].encode()).hexdigest())
    return result


def hotspot_port(folder, driver, k):
    """The harness's HotSpot contract at 100k steps: its scalar reference output, then its Bend port with
    the reference's coefficients and the 1,024^2 inputs (bend_bench.hotspot.generate, at any step count)."""
    (folder / 'gpu').mkdir()
    stage_rodinia(RODINIA, folder)  # the corrected OpenMP source, which the reference build includes
    reference, log = folder / 'reference', folder / 'build.jsonl'
    run_logged(['/usr/bin/g++', *FLAGS, '-fopenmp', f'-I{folder}/gpu', '-DHOTSPOT_REFERENCE', driver, '-o', reference], log)
    bits = run_logged([reference, 1024, 100 * k, 1, *HOTSPOT_INPUTS], log)['stdout']
    if len(bits.split()) != 1024 * 1024:
        raise RuntimeError('hotspot: scalar reference output incomplete')
    (folder / 'expected.bits').write_text(bits)
    values = run_logged([reference, 1024, 'coeff'], log)['stdout'].split()
    literal = lambda value: value if any(c in value for c in '.eE') else value + '.0'
    return replace((ASSETS / 'gpu/hotspot.bend').read_text(),
                   [('Coeff{0.0, 0.0, 0.0, 0.0}', 'Coeff{' + ', '.join(map(literal, values)) + '}'),
                    ('solve!(10n,', f'solve!(Nat.mul(100n, {nat(k)}),'), ('load_grid(6n, 6n,', 'load_grid(10n, 10n,'),
                    ('"temp.txt"', json.dumps(str(HOTSPOT_INPUTS[0]))), ('"power.txt"', json.dumps(str(HOTSPOT_INPUTS[1])))],
                   'hotspot: Bend')


def replace(text, pairs, what):
    for old, new in pairs:
        if text.count(old) != 1:
            raise ValueError(f'{what}: knob changed: {old!r}')
        text = text.replace(old, new)
    return text


def build(work, bend, name, k, spec):
    """Bend GPU and conventional GPU binaries at multiplier k; returns their commands."""
    folder = work / name / str(k)
    folder.mkdir(parents=True)
    program = spec.get('source', name)
    cuda = replace((ASSETS / spec['cuda']).read_text(), spec['patch'](k), f'{name}: conventional')
    cu = folder / Path(spec['cuda']).name
    if name == 'gameoflife':
        cuda = cuda.replace('#include "../upstream/bench/runtime/gameoflife/main.c"',
                            f'#include "{bend}/bench/runtime/gameoflife/main.c"')
    cu.write_text(cuda)
    if name == 'hotspot':
        source = hotspot_port(folder, cu, k)
    else:
        source = replace((bend / 'bench/runtime' / program / 'main.bend').read_text(), spec['bend'](k), f'{name}: Bend')
    (folder / 'main.bend').write_text(source)
    if 'serial' in spec:  # a patched serial reference beside the conventional source, which includes it first
        serial = bend / 'bench/runtime' / program / 'main.c'
        (folder / 'main.c').write_text(replace(serial.read_text(), spec['serial'](k), f'{name}: serial'))
    if program in ('nbody', 'raytrace', 'terrain'):  # the harness's device header: the serial arithmetic, marked __device__
        device = (bend / 'bench/runtime' / program / 'main.c').read_text().split('int main(void)')[0]
        device = re.sub(r'^#include[^\n]*\n', '', device, flags=re.M)
        device = re.sub(r'^static (?=(?:uint32_t|V2|Hs|float|Hit|void) \w+\()', '__device__ static ', device, flags=re.M)
        device = device.replace('static const Sph SP[NS]', '__device__ __constant__ const Sph SP[NS]')
        (folder / f'vendor-{program}-device.cuh').write_text('namespace gpu {\n' + device + '}\n')
    steps = [[str(ROOT.parent / 'bend2/tools/bun-linux-x64/bun'), str(bend / 'bend2/main.ts'), str(folder / 'main.bend'),
              '-o', str(folder / 'bend.c')],
             [CC, '-std=c11', *FLAGS, '-DBEND_CUDA=1', f'-I{CUDA}/include', f'-L{CUDA}/lib64', str(folder / 'bend.c'),
              '-lpthread', '-lm', '-lcuda', '-lnvrtc', f'-Wl,--disable-new-dtags,-rpath,{CUDA}/lib64', '-o', str(folder / 'bend-cuda')],
             [str(folder / 'bend-cuda'), '--gpu-build'],
             *spec.get('builder', cuda_builder)(folder, cu, bend, program)]
    for command in steps:
        result = execute(command, timeout=900)
        append(folder / 'build.jsonl', result)
        if result['returncode']:
            raise RuntimeError(f'{name} x{k}: build failed: {command[0]}\n{result["stderr"][-2000:]}')
    return folder, dict(bend=[str(folder / 'bend-cuda'), '--threads', '32', '--gpu', '4GB'],
                        cuda=[str(folder / 'cuda'), *spec['args'](k)])


def timed(command, config, log, env=None, **tags):
    while not gpu_clear():
        print('WAITING unapproved GPU process', flush=True)
        time.sleep(60)
    result = execute(['taskset', '-c', ','.join(map(str, range(32))), *command], env={**environment(), **(env or {})},
                     timeout=1800, measured=True, gpu_policy=config)
    append(log, dict(tags, **logged(result)))
    if result['returncode'] or result['timeout'] or result.get('contention_error'):
        raise RuntimeError(f'{tags}: failed: {result["stderr"][-500:]}')
    return result


def theil_sen(xs, ys):
    """Median slope over all pairs: a line fit that one outlying size cannot drag."""
    return statistics.median((ys[j] - ys[i]) / (xs[j] - xs[i]) for i in range(len(xs)) for j in range(i + 1, len(xs)))


def conventional_time(points, work=lambda k: k):
    """The conventional program's time at each size, rebuilt from its measured GPU time and a line through
    its host-side time (process minus GPU). The host side is constant for some programs and grows for
    others (cuDF generates its input on the host). Host load only adds time, so each size's host time is
    its fastest measured round, and the line is the Theil-Sen fit through those floors."""
    xs = [work(p['multiplier']) for p in points]
    floors = [p['cuda_host_floor'] for p in points]
    slope = theil_sen(xs, floors)
    fixed = statistics.median(h - slope * x for h, x in zip(floors, xs))
    return [fixed + slope * x + p['cuda_device_seconds'] for p, x in zip(points, xs)]


def settled(points, share, work=lambda k: k):
    """Stop once the marginal ratio holds within 3% when the newest size is dropped, and the conventional
    program's GPU work is at least `share` of its time, so its per-work cost is visible."""
    from scaling_fit import marginal_ratio  # numpy and scipy; imported here since scaling_fit imports this module
    if len(points) < 5 or points[-1]['cuda_device_share'] < share:
        return False
    return abs(marginal_ratio(points, work)[0] / marginal_ratio(points[:-1], work)[0] - 1) < 0.03


def sweep(out, bend, name, spec, config, args, rng, results):
    """Grow one workload; returns when it settles or reaches its largest valid size."""
    points, k, verify_seconds = [], args.start_multiplier, 0.0
    verify = spec.get('verify', lambda k: ['verify'])
    limit = min(args.max_multiplier, spec.get('max', args.max_multiplier))
    while k <= limit:
        if 'prepare' in spec:
            folder = out / name / str(k)
            folder.mkdir(parents=True)
            commands = spec['prepare'](folder, k)
            envs = {impl: env for impl, (_, env) in commands.items()}
            commands = {impl: command for impl, (command, _) in commands.items()}
        else:
            folder, commands = build(out, bend, name, k, spec)
            envs = {}
        log = folder / 'samples.jsonl'
        reference = None
        if 'prepare' in spec:
            whole_program(name, k, spec, folder, commands, envs, config, log, args, rng, points, results, out)
            if settled(points, spec.get('share', 0.5), spec.get('work', lambda k: k)):
                return
            k *= 2
            continue
        if verify and k <= spec.get('verify_until', args.verify_until) and verify_seconds * 2 <= args.verify_budget:
            check = timed([commands['cuda'][0], *verify(k)], config, log, phase='verify', implementation='cuda')
            if 'FULL_OUTPUT_VERIFIED' not in check['stderr']:
                raise RuntimeError(f'{name} x{k}: conventional verification incomplete')
            reference, verify_seconds = check['stdout'].strip(), check['end_to_end_seconds']
        checks = {impl: timed(commands[impl], config, log, phase='check', implementation=impl) for impl in ('cuda', 'bend')}
        outputs = {impl: check['stdout'].strip() for impl, check in checks.items()}
        if 'expected_bits' in spec:  # every cell against the scalar reference, with the harness's tolerance
            case = dict(expected_bits=str(folder / 'expected.bits'), contract=dict(size=1024))
            failed = [impl for impl, check in checks.items() if not correct(case, check)]
            if failed:
                raise RuntimeError(f'{name} x{k}: outside the reference tolerance: {failed}')
            reference = hashlib.sha256((folder / 'expected.bits').read_bytes()).hexdigest()
        elif outputs['bend'] != outputs['cuda'] or (reference is not None and reference != outputs['cuda']):
            raise RuntimeError(f'{name} x{k}: outputs disagree: {outputs} verify={reference}')
        times, device, host = {'bend': [], 'cuda': []}, [], []
        for phase, rounds in (('warmup', 1), ('measure', args.rounds)):
            for rep in range(rounds):
                order = ['bend', 'cuda']
                rng.shuffle(order)
                for impl in order:
                    r = timed(commands[impl], config, log, phase=phase, implementation=impl, rep=rep)
                    if r['stdout'].strip() != outputs[impl]:
                        raise RuntimeError(f'{name} x{k}: output changed between runs')
                    if phase == 'measure':
                        times[impl].append(r['end_to_end_seconds'])
                        if impl == 'cuda':
                            device.append(r.get('device_sequence_seconds'))
                            host.append(r['end_to_end_seconds'] - r['device_sequence_seconds'])
        point = dict(multiplier=k, knob=spec['knob'], value=spec['grow'](k),
                     checksum=reference if 'expected_bits' in spec else outputs['cuda'],
                     serial_verified=reference is not None,
                     bend_seconds=statistics.median(times['bend']), cuda_seconds=statistics.median(times['cuda']),
                     cuda_device_seconds=statistics.median(device), cuda_host_floor=min(host),
                     ratios=[b / c for b, c in zip(times['bend'], times['cuda'])])
        point['bend_over_cuda'] = point['bend_seconds'] / point['cuda_seconds']
        point['cuda_device_share'] = point['cuda_device_seconds'] / point['cuda_seconds']
        points.append(point)
        results[name] = points
        write_json(out / 'summary.json', results)
        print('POINT', name, json.dumps(point), flush=True)
        if settled(points, spec.get('share', 0.5), spec.get('work', lambda k: k)):
            return
        k *= 2


def whole_program(name, k, spec, folder, commands, envs, config, log, args, rng, points, results, out):
    """One size of a whole-program workload: outputs compared with spec['agree'], GPU work from spec['check']."""
    check = lambda result: spec['check'](result, k, folder) if spec.get('folder') else spec['check'](result, k)
    run = lambda impl, **tags: timed(commands[impl], config, log, env=envs.get(impl), implementation=impl, **tags)
    reference = None
    if 'reference' in commands and k <= spec.get('verify_until', args.verify_until):
        reference = check(run('reference', phase='verify'))[0]
    outputs = {impl: check(run(impl, phase='check'))[0] for impl in ('cuda', 'bend')}
    agree = spec.get('agree', lambda a, b: a == b)
    if not agree(outputs['bend'], outputs['cuda']) or (reference is not None and not agree(outputs['cuda'], reference)):
        raise RuntimeError(f'{name} x{k}: outputs disagree: {outputs} reference={reference}')
    times, device, host = {'bend': [], 'cuda': []}, [], []
    for phase, rounds in (('warmup', 1), ('measure', args.rounds)):
        for rep in range(rounds):
            order = ['bend', 'cuda']
            rng.shuffle(order)
            for impl in order:
                r = run(impl, phase=phase, rep=rep)
                output, work = check(r)
                if not agree(output, outputs[impl]):
                    raise RuntimeError(f'{name} x{k}: output changed between runs')
                if phase == 'measure':
                    times[impl].append(r['end_to_end_seconds'])
                    if impl == 'cuda':
                        device.append(work)
                        host.append(r['end_to_end_seconds'] - work)
    point = dict(multiplier=k, knob=spec['knob'], value=spec['grow'](k), checksum=outputs['cuda'],
                 serial_verified=reference is not None or spec.get('oracle', False),
                 bend_seconds=statistics.median(times['bend']), cuda_seconds=statistics.median(times['cuda']),
                 cuda_device_seconds=statistics.median(device), cuda_host_floor=min(host),
                 ratios=[b / c for b, c in zip(times['bend'], times['cuda'])])
    point['bend_over_cuda'] = point['bend_seconds'] / point['cuda_seconds']
    point['cuda_device_share'] = point['cuda_device_seconds'] / point['cuda_seconds']
    points.append(point)
    results[name] = points
    write_json(out / 'summary.json', results)
    print('POINT', name, json.dumps(point), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workloads', nargs='+', default=list(WORKLOADS))
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--max-multiplier', type=int, default=64)
    parser.add_argument('--start-multiplier', type=int, default=1, help='Continue a workload from this size')
    parser.add_argument('--verify-until', type=int, default=16, help='Largest multiplier checked against the serial C')
    parser.add_argument('--verify-budget', type=float, default=120.0, help='Seconds of predicted serial verification allowed per size')
    args = parser.parse_args()
    config = load_config(ROOT / 'scorecard-vendor.toml')
    bend = Path('/code/bend2/upstream')
    out = ROOT / 'runs' / time.strftime('startup-scaling-%Y%m%d-%H%M%S')
    out.mkdir()
    cccl = execute(['git', '-C', str(CCCL), 'rev-parse', 'HEAD'])['stdout'].strip()
    write_json(out / 'provenance.json', dict(bend=str(bend), script_sha256=hash_file(Path(__file__)), arguments=vars(args),
               sources={spec['cuda']: hash_file(ASSETS / spec['cuda']) for spec in WORKLOADS.values()},
               cccl_commit=cccl, cudf_lock_sha256=hash_file(ROOT / 'dependencies/cudf/uv.lock')))
    print('OUTPUT', out, flush=True)
    rng = random.Random(20260924)
    results = {}
    with exclusive(config):
        for name in args.workloads:
            try:
                sweep(out, bend, name, WORKLOADS[name], config, args, rng, results)
            except Exception as error:  # this workload stops growing; its points so far stand
                results[name + ':stopped'] = dict(error=repr(error)[-2000:])
                write_json(out / 'summary.json', results)
                print('STOPPED', name, repr(error)[-300:], flush=True)
    write_json(out / 'completed.json', dict(status='passed', workloads=list(results)))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
