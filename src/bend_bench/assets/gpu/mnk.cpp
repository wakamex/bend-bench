// Exact alpha-beta comparator, with parallelism across independent positions.
// This is a locally authored control, not a published champion solver.
#include <chrono>
#include <cstdint>
#include <cstdio>
#ifdef __CUDACC__
#include <cuda_runtime.h>
#define ARRAY __device__ __constant__
#define SEARCH __device__
#define CUDA(call)                                                             \
  do {                                                                         \
    auto e = (call);                                                           \
    if (e != cudaSuccess) {                                                    \
      fprintf(stderr, "%s\n", cudaGetErrorString(e));                          \
      return 2;                                                                \
    }                                                                          \
  } while (0)
#else
#define ARRAY
#define SEARCH
#endif
#include "mnk-data.h"
SEARCH bool won(uint32_t board) {
  for (uint32_t m : masks)
    if ((board & m) == m)
      return true;
  return false;
}
SEARCH int solve(uint32_t me, uint32_t other, int left, int alpha, int beta) {
  if (won(other))
    return -1;
  if (!left)
    return 0;
  int best = -1;
  uint32_t free = ((1u << cells) - 1) & ~(me | other);
  while (free) {
    uint32_t bit = free & -free;
    free -= bit;
    int value = -solve(other, me | bit, left - 1, -beta, -alpha);
    if (value > best)
      best = value;
    if (best > alpha)
      alpha = best;
    if (alpha >= beta)
      break;
  }
  return best;
}
#ifdef __CUDACC__
__global__ void children(int *out) {
  int position = blockIdx.x, move = threadIdx.x;
  uint32_t me = positions[position][0], other = positions[position][1],
           bit = 1u << move;
  int value = -1;
  if (move < cells && !((me | other) & bit))
    value = -solve(other, me | bit, empty - 1, -2, 2);
  out[position * 32 + move] = value;
}
__global__ void combine(int *children, int *out) {
  int position = threadIdx.x, best = -1;
  for (int j = 0; j < 32; ++j)
    if (children[position * 32 + j] > best)
      best = children[position * 32 + j];
  out[position] = 1 + best;
}
#endif
int main() {
  int out[16];
#ifdef __CUDACC__
  int *d, *scores;
  CUDA(cudaDeviceSetLimit(cudaLimitStackSize, 32768));
  CUDA(cudaMalloc(&d, sizeof(out)));
  CUDA(cudaMalloc(&scores, 16 * 32 * sizeof(int)));
  cudaEvent_t a, b;
  CUDA(cudaEventCreate(&a));
  CUDA(cudaEventCreate(&b));
  CUDA(cudaEventRecord(a));
  children<<<16, 32>>>(scores);
  CUDA(cudaGetLastError());
  combine<<<1, 16>>>(scores, d);
  CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(b));
  CUDA(cudaEventSynchronize(b));
  float ms;
  CUDA(cudaEventElapsedTime(&ms, a, b));
  fprintf(stderr, "EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n", ms / 1000.0);
  CUDA(cudaMemcpy(out, d, sizeof(out), cudaMemcpyDeviceToHost));
  CUDA(cudaFree(d));
  CUDA(cudaFree(scores));
  CUDA(cudaEventDestroy(a));
  CUDA(cudaEventDestroy(b));
#else
  auto start = std::chrono::steady_clock::now();
#pragma omp parallel for schedule(dynamic, 1)
  for (int i = 0; i < 16; ++i)
    out[i] = 1 + solve(positions[i][0], positions[i][1], empty, -2, 2);
  fprintf(
      stderr, "EVAL_COMPUTE_SECONDS=%.9f\n",
      std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
          .count());
#endif
  for (int v : out)
    printf("%d\n", v);
}
