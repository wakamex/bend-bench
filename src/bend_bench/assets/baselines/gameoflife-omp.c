// Same leaf computation and ordered checksum tree as the pinned vendor source.
#include <stdlib.h>
#include <omp.h>
#define main vendor_main
#include "../upstream/bench/runtime/gameoflife/main.c"
#undef main

int main(int argc, char **argv) {
  unsigned depth = argc > 1 ? (unsigned)atoi(argv[1]) : 18;
  if (depth > 24) return 2;
  unsigned n = 1u << depth;
  Census *a = malloc(n * sizeof(*a));
  Census *b = malloc(n * sizeof(*b));
  if (!a || !b) return 2;
  double start = omp_get_wtime();
  #pragma omp parallel for schedule(static)
  for (unsigned i = 0; i < n; i++)
    a[i] = chunk_run(64, i * 64, 32, 0, 0, 0, 0);
  for (unsigned width = n; width > 1; width /= 2) {
    #pragma omp parallel for schedule(static) if(width > 1024)
    for (unsigned i = 0; i < width / 2; i++)
      b[i] = census_zip(a[2 * i], a[2 * i + 1]);
    Census *tmp = a; a = b; b = tmp;
  }
  uint32_t result = census_fin(a[0]);
  fprintf(stderr, "EVAL_COMPUTE_SECONDS=%.9f\n", omp_get_wtime() - start);
  printf("%u\n", result);
  free(a); free(b);
  return 0;
}
