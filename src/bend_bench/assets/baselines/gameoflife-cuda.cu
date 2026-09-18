#include <cuda_runtime.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
// Reuse the exact vendor arithmetic on both host and device.
#define main vendor_main
#define static static __host__ __device__
#include "../upstream/bench/runtime/gameoflife/main.c"
#undef static
#undef main

#define CUDA(call) do { cudaError_t e = (call); if (e != cudaSuccess) { \
  fprintf(stderr, "%s: %s\n", #call, cudaGetErrorString(e)); exit(2); } } while (0)

__global__ void leaves(Census *out, unsigned n) {
  unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  Census c = {0, 0, 0, 0};
  for (int p = 63; p >= 0; --p) {
    uint32_t board = ((i * 64 + p) * 2654435761u) & 65535u;
    for (unsigned g = 0; g < 32; g++) board = board_step(board);
    Cls cls = board_classify(board);
    c.pop += board_popcount(board);
    c.still += cls == CLS_STILL;
    c.osc += cls == CLS_OSC;
    c.mix = c.mix * 2654435761u ^ board;
  }
  out[i] = c;
}

__global__ void reduce(Census *out, const Census *in, unsigned n) {
  unsigned i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) out[i] = census_zip(in[2 * i], in[2 * i + 1]);
}

int main(int argc, char **argv) {
  unsigned depth = argc > 1 ? (unsigned)atoi(argv[1]) : 18;
  if (depth > 24) return 2;
  unsigned n = 1u << depth;
  Census *a, *b, answer;
  CUDA(cudaMalloc(&a, n * sizeof(Census)));
  CUDA(cudaMalloc(&b, n * sizeof(Census)));
  cudaEvent_t begin, end;
  CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  leaves<<<(n + 255) / 256, 256>>>(a, n);
  CUDA(cudaGetLastError());
  for (unsigned width = n / 2; width; width /= 2) {
    reduce<<<(width + 255) / 256, 256>>>(b, a, width);
    CUDA(cudaGetLastError());
    Census *tmp = a; a = b; b = tmp;
  }
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms;
  CUDA(cudaEventElapsedTime(&ms, begin, end));
  CUDA(cudaMemcpy(&answer, a, sizeof(answer), cudaMemcpyDeviceToHost));
  printf("%u\n", census_fin(answer));
  // Event interval covers kernel sequence and device-side gaps, excluding initialization/copy.
  fprintf(stderr, "EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n", ms / 1000.0);
  CUDA(cudaFree(a)); CUDA(cudaFree(b));
  CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
  return 0;
}
