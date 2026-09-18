"""Emit simple loop-parallel C twins; retain vendor arithmetic and checksums."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
bodies = {
    "mandelbrot": """Hs total = {0};
  #pragma omp parallel
  {
    Hs local = {0};
    #pragma omp for schedule(static)
    for (uint32_t i = 0; i < (1u << 18); i++)
      local = hzip(local, hchunk(64, i * 64, its(), 0, 0, 0, 0, 0, 0, 0, 0));
    #pragma omp critical
    total = hzip(total, local);
  }
  Lut lut = cdf(total);
  uint32_t sum = 0;
  #pragma omp parallel for reduction(+:sum) schedule(static)
  for (uint32_t i = 0; i < (1u << 24); i++)
    sum += rpix(i, its(), lut.k0, lut.k1, lut.k2, lut.k3, lut.k4, lut.k5, lut.k6, lut.k7);
  uint32_t result = lut.k0;
  uint32_t ks[] = {lut.k1, lut.k2, lut.k3, lut.k4, lut.k5, lut.k6, lut.k7};
  for (unsigned k = 0; k < 7; k++) result = result * 2654435761u + ks[k];
  result = result * 2654435761u + sum;""",
    "symreg": """unsigned n = 1u << SIZE;
  Sel *a = malloc(n * sizeof(Sel)), *b = malloc(n * sizeof(Sel));
  if (!a || !b) return 2;
  #pragma omp parallel for schedule(dynamic, 64)
  for (unsigned i = 0; i < n; i++) {
    uint32_t seed = 42;
    for (int bit = SIZE - 1; bit >= 0; bit--)
      seed = (i >> bit) & 1 ? seed * 214013u + 3 : seed * 1664525u + 1;
    a[i] = candidate_evaluate(word_prng(seed), PTS);
  }
  for (unsigned width = n; width > 1; width /= 2) {
    #pragma omp parallel for schedule(static) if(width > 1024)
    for (unsigned i = 0; i < width / 2; i++) b[i] = winner_pick(a[2*i], a[2*i+1]);
    Sel *tmp = a; a = b; b = tmp;
  }
  uint32_t result = run_finish(ROUNDS, PTS, a[0]);
  free(a); free(b);""",
    "merkle": """unsigned n = 1u << SIZE;
  uint32_t *tree = malloc(2 * n * sizeof(uint32_t));
  uint32_t *audit = malloc(2 * n * sizeof(uint32_t));
  if (!tree || !audit) return 2;
  #pragma omp parallel for schedule(static)
  for (unsigned i = 0; i < n; i++) tree[n+i] = audit[n+i] = leaf_hash(i);
  for (unsigned width = n / 2; width; width /= 2) {
    #pragma omp parallel for schedule(static) if(width > 1024)
    for (unsigned i = width; i < 2 * width; i++) tree[i] = hash_join(tree[2*i], tree[2*i+1]);
  }
  for (unsigned width = n / 2; width; width /= 2) {
    #pragma omp parallel for schedule(static) if(width > 1024)
    for (unsigned i = width; i < 2 * width; i++) {
      uint32_t h = hash_join(audit[2*i], audit[2*i+1]);
      audit[i] = h + (h ^ tree[i]);
    }
  }
  uint32_t proof = leaf_hash(PROBE);
  for (unsigned i = n + PROBE; i > 1; i /= 2)
    proof = i & 1 ? hash_join(tree[i-1], proof) : hash_join(proof, tree[i+1]);
  uint32_t result = hash_join(audit[1], proof);
  free(tree); free(audit);""",
    "hashmap": """uint32_t result = 0;
  #pragma omp parallel for reduction(+:result) schedule(static)
  for (uint32_t i = 0; i < (1u << TABLES); i++) result += table_run(i, KEYS);""",
    "editdist": """uint32_t result = 0;
  #pragma omp parallel for reduction(+:result) schedule(static)
  for (uint32_t i = 0; i < (1u << DEPTH); i++) result += pair_run(i);""",
    "lexer": """uint32_t result = 0;
  #pragma omp parallel for reduction(+:result) schedule(static)
  for (uint32_t i = 0; i < (1u << DEPTH); i++) {
    char buf[128];
    result += lex(buf, gen(seed(i), buf));
  }""",
    "terrain": """uint32_t result = 0;
  #pragma omp parallel for reduction(+:result) schedule(static)
  for (uint32_t i = 0; i < (1u << 16); i++) result += tile_run(i, 5);""",
    "tree-matmul": """uint32_t result = 0;
  #pragma omp parallel for reduction(+:result) schedule(static)
  for (uint32_t i = 0; i < 384; i++) result += batch_leaf(i, 384, 7);""",
    "raytrace": """uint32_t result = 0;
  uint32_t h = 1u << ROWS;
  float hw = WIDTH / 2, hh = h / 2;
  #pragma omp parallel for reduction(+:result) schedule(dynamic, 1)
  for (uint32_t y = 0; y < h; y++)
    for (uint32_t x = 0; x < WIDTH; x++) result += pixel_render(x, y, hw, hh);""",
    "queens": """uint32_t sols = 0, nodes = 0;
  uint32_t full = (1u << SIZE) - 1;
  uint32_t n4 = SIZE * SIZE * SIZE * SIZE;
  uint32_t bound = LIMIT < n4 ? LIMIT : n4;
  #pragma omp parallel for reduction(+:sols,nodes) schedule(dynamic, 64)
  for (uint32_t i = 0; i < (1u << DEPTH); i++) {
    Stats s = pfx(i, SIZE, full, bound);
    sols += s.sols; nodes += s.nodes;
  }
  uint32_t result = (sols * 2654435761u) ^ nodes;""",
    "kmeans": """uint32_t result = 0;
  #pragma omp parallel reduction(+:result)
  {
    Arena h = {0};
    #pragma omp for schedule(static)
    for (uint32_t i = 0; i < 64; i++) result += rst(&h, i, size());
    free(h.at);
  }""",
    "nbody": """Hs total = {0};
  #pragma omp parallel
  {
    Hs local = {0};
    #pragma omp for schedule(static)
    for (uint32_t i = 0; i < (1u << SY); i++)
      local = hzip(local, chunk(8, i * 8, ST, 0, 0, 0, 0, 0, 0, 0, 0, 0));
    #pragma omp critical
    total = hzip(total, local);
  }
  uint32_t result = run_fin(total);""",
}
for name, body in bodies.items():
    include = f"../upstream/bench/runtime/{name}/main.c"
    if name in ("hashmap", "tree-matmul", "symreg"):
        source = (ROOT / include).read_text()
        marker, private = {"hashmap": ("static Table tab;", "tab"),
            "tree-matmul": ("static size_t pool_cap = 0;", "pool_free, pool_block, pool_used, pool_cap"),
            "symreg": ("static uint32_t expr_arena_len;", "expr_arena, expr_arena_len")}[name]
        assert source.count(marker) == 1
        source = source.replace(marker, marker + f"\n#pragma omp threadprivate({private})")
        include = f"vendor-{name}.c"
        (ROOT / include).write_text(source)
    (ROOT / (name + "-omp.c")).write_text(f'''// Vendor leaf arithmetic, parallelized over independent inputs.
#include <omp.h>
#include <stdlib.h>
#define main vendor_main
#include "{include}"
#undef main

int main(void) {{
  double start = omp_get_wtime();
  {body}
  fprintf(stderr, "EVAL_COMPUTE_SECONDS=%.9f\\n", omp_get_wtime() - start);
  printf("%u\\n", result);
  return 0;
}}
''')
