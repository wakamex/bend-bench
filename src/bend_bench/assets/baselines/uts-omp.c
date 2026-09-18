// Conventional OpenMP tasks with a depth cutoff and no tasks for leaves.
// SHA-1 and RNG state transitions come directly from the pinned BOTS source.
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <omp.h>
#include "../bots/common/bots.h"
#include "../bots/omp-tasks/uts/brg_sha1.h"

bots_verbose_mode_t bots_verbose_mode = BOTS_VERBOSE_NONE;
static int branching, granularity, cutoff;
static double probability;
typedef struct { unsigned char bytes[20]; } State;

static int children(State *s) {
  return rng_rand(s->bytes) / 2147483648.0 < probability ? branching : 0;
}

static uint64_t sequential(State state, int n) {
  uint64_t count = 1;
  for (int i = 0; i < n; i++) {
    State child;
    for (int j = 0; j < granularity; j++) rng_spawn(state.bytes, child.bytes, i);
    int k = children(&child);
    count += k ? sequential(child, k) : 1;
  }
  return count;
}

static uint64_t parallel(State state, int n, int depth) {
  if (depth >= cutoff) return sequential(state, n);
  uint64_t counts[n], count = 1;
  for (int i = 0; i < n; i++) {
    State child;
    for (int j = 0; j < granularity; j++) rng_spawn(state.bytes, child.bytes, i);
    int k = children(&child);
    if (!k) counts[i] = 1;
    else {
      #pragma omp task firstprivate(child, k, depth, i) shared(counts)
      counts[i] = parallel(child, k, depth + 1);
    }
  }
  #pragma omp taskwait
  for (int i = 0; i < n; i++) count += counts[i];
  return count;
}

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  FILE *f = fopen(argv[1], "r");
  double root_branch;
  int seed, expected_depth;
  unsigned long long expected, leaves;
  if (!f || fscanf(f, "%lf %lf %d %d %d %llu %d %llu", &root_branch, &probability,
                   &branching, &seed, &granularity, &expected, &expected_depth, &leaves) != 8) return 2;
  fclose(f);
  cutoff = atoi(argv[2]);
  if (cutoff < 0 || granularity < 1 || branching < 0 || branching > 100) return 2;
  State root;
  rng_init(root.bytes, seed);
  uint64_t result = 0;
  double start = omp_get_wtime();
  #pragma omp parallel
  #pragma omp single
  result = parallel(root, (int)floor(root_branch), 0);
  fprintf(stderr, "EVAL_COMPUTE_SECONDS=%.9f\n", omp_get_wtime() - start);
  printf("%llu\n", (unsigned long long)result);
  return result == expected ? 0 : 1;
}
