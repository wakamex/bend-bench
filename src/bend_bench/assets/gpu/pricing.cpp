// Matching arithmetic control, locally authored; not a tuned finance-library
// baseline.
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#ifdef __CUDACC__
#include <cub/device/device_reduce.cuh>
#include <cuda_runtime.h>
#define HD __host__ __device__
#define CUDA(call)                                                             \
  do {                                                                         \
    auto e = (call);                                                           \
    if (e != cudaSuccess) {                                                    \
      fprintf(stderr, "%s\n", cudaGetErrorString(e));                          \
      exit(2);                                                                 \
    }                                                                          \
  } while (0)
#else
#define HD
#endif
HD uint32_t hash32(uint32_t x) {
  x = (x ^ (x >> 16)) * 2246822507u;
  x = (x ^ (x >> 13)) * 3266489909u;
  return x ^ (x >> 16);
}
HD uint32_t rng(uint32_t x) {
  uint32_t a = 16807 * (x % 127773), b = 2836 * (x / 127773);
  return a > b ? a - b : 2147483647u - b + a;
}
HD float uniform(uint32_t x) { return (float(x >> 8) + 0.5f) * 0x1p-23f; }
HD float path(uint32_t i, int steps, float drift, float vol) {
  uint32_t state = 1 + hash32(i + 1) % 2147483646u;
  float spot = 100, total = 0;
  for (int t = 0; t < steps; ++t) {
    uint32_t a = rng(state), b = rng(a);
    state = b;
    float z =
        sqrtf(-2.0f * logf(uniform(a))) * cosf(6.283185307179586f * uniform(b));
    spot = spot * expf(drift + vol * z);
    total = total + spot;
  }
  return 0.951229424500714f * fmaxf(0, total / float(steps) - 100.0f);
}
#ifdef __CUDACC__
__global__ void paths(float *out, int n, int steps, float drift, float vol) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n)
    out[i] = path(i, steps, drift, vol);
}
#endif
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  int n = atoi(argv[1]), steps = atoi(argv[2]);
  if (n <= 0 || steps <= 0)
    return 2;
  float drift = float(0.03 / steps), vol = float(0.2 / sqrt(double(steps)));
  std::vector<float> out(n);
  float mean;
#ifdef __CUDACC__
  float *d;
  CUDA(cudaMalloc(&d, n * sizeof(float)));
  float *sum;
  CUDA(cudaMalloc(&sum, sizeof(float)));
  size_t bytes = 0;
  CUDA(cub::DeviceReduce::Sum(nullptr, bytes, d, sum, n));
  void *scratch;
  CUDA(cudaMalloc(&scratch, bytes));
  cudaEvent_t a, b;
  CUDA(cudaEventCreate(&a));
  CUDA(cudaEventCreate(&b));
  CUDA(cudaEventRecord(a));
  paths<<<(n + 255) / 256, 256>>>(d, n, steps, drift, vol);
  CUDA(cudaGetLastError());
  CUDA(cub::DeviceReduce::Sum(scratch, bytes, d, sum, n));
  CUDA(cudaEventRecord(b));
  CUDA(cudaEventSynchronize(b));
  float ms;
  CUDA(cudaEventElapsedTime(&ms, a, b));
  fprintf(stderr, "EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n", ms / 1000.0);
  CUDA(cudaMemcpy(out.data(), d, n * sizeof(float), cudaMemcpyDeviceToHost));
  CUDA(cudaMemcpy(&mean, sum, sizeof(float), cudaMemcpyDeviceToHost));
  mean /= n;
  CUDA(cudaFree(sum));
  CUDA(cudaFree(scratch));
  CUDA(cudaFree(d));
  CUDA(cudaEventDestroy(a));
  CUDA(cudaEventDestroy(b));
#else
  auto start = std::chrono::steady_clock::now();
  double sum = 0;
#pragma omp parallel for schedule(static) reduction(+ : sum)
  for (int i = 0; i < n; ++i) {
    out[i] = path(i, steps, drift, vol);
    sum += out[i];
  }
  mean = float(sum / n);
  fprintf(
      stderr, "EVAL_COMPUTE_SECONDS=%.9f\n",
      std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
          .count());
#endif
  uint32_t mean_bits;
  memcpy(&mean_bits, &mean, 4);
  printf("%u\n", mean_bits);
  for (float v : out) {
    uint32_t bits;
    memcpy(&bits, &v, 4);
    printf("%u\n", bits);
  }
}
