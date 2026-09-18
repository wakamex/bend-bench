// Batched vendor mazes, not a parallel traversal of one graph.
#include <omp.h>
#define main vendor_main
#include "../upstream/bench/runtime/bfs/main.c"
#undef main

int main(void) {
  uint32_t result = 0;
  double start = omp_get_wtime();
  #pragma omp parallel for reduction(+:result) schedule(dynamic, 64)
  for (uint32_t i = 0; i < (1u << DEPTH); i++) result += maze_run(i);
  fprintf(stderr, "EVAL_COMPUTE_SECONDS=%.9f\n", omp_get_wtime() - start);
  printf("%u\n", result);
  return 0;
}
