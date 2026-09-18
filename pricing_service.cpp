// Appended to the preserved pricing path implementation by pricing_sustained.py.
struct Moments { float sum, square; };
struct Add {
  HD Moments operator()(Moments a, Moments b) const {
    return {a.sum + b.sum, a.square + b.square};
  }
};
#ifdef __CUDACC__
__global__ void simulate(Moments *out, float *payoffs, int n, int steps,
                         float drift, float vol, uint32_t offset) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) {
    float x = path(uint32_t(i) + offset, steps, drift, vol);
    out[i] = {x, x * x};
#if AUDIT
    payoffs[i] = x;
#endif
  }
}
#endif
int main(int argc, char **argv) {
  if (argc != 3) return 2;
  const int n = atoi(argv[1]), steps = atoi(argv[2]);
  if (n < 2 || steps < 1) return 2;
  const float drift = float(0.03 / steps), vol = float(0.2 / sqrt(double(steps)));
  std::vector<float> payoffs(AUDIT ? n : 0);
#ifdef __CUDACC__
  Moments *device, *result;
  float *values = nullptr;
  CUDA(cudaMalloc(&device, n * sizeof(Moments)));
  CUDA(cudaMalloc(&result, sizeof(Moments)));
#if AUDIT
  CUDA(cudaMalloc(&values, n * sizeof(float)));
#endif
  size_t bytes = 0;
  CUDA(cub::DeviceReduce::Reduce(nullptr, bytes, device, result, n, Add{}, Moments{0, 0}));
  void *scratch;
  CUDA(cudaMalloc(&scratch, bytes));
#endif
  puts("READY"); fflush(stdout);
  for (int rep = 0; rep < BATCHES; ++rep) {
    uint32_t offset = uint32_t(rep) * uint32_t(n);
    auto start = std::chrono::steady_clock::now();
    double sum = 0, square = 0;
#ifdef __CUDACC__
    simulate<<<(n + 255) / 256, 256>>>(device, values, n, steps, drift, vol, offset);
    CUDA(cudaGetLastError());
    CUDA(cub::DeviceReduce::Reduce(scratch, bytes, device, result, n, Add{}, Moments{0, 0}));
    Moments host;
    CUDA(cudaMemcpy(&host, result, sizeof(host), cudaMemcpyDeviceToHost));
    sum = host.sum; square = host.square;
#else
#pragma omp parallel for schedule(static) reduction(+:sum,square)
    for (int i = 0; i < n; ++i) {
      float x = path(uint32_t(i) + offset, steps, drift, vol);
      sum += x; square += double(x) * x;
#if AUDIT
      payoffs[i] = x;
#endif
    }
#endif
    float mean = float(sum / n);
    float se = float(sqrt(fmax(0.0, (square - sum * (sum / n)) / (n - 1)) / n));
    auto ready = std::chrono::steady_clock::now();
    uint32_t a, b;
    memcpy(&a, &mean, 4); memcpy(&b, &se, 4);
    printf("RESULT %u %u %d\n", a, b, n); fflush(stdout);
#if AUDIT
#ifdef __CUDACC__
    CUDA(cudaMemcpy(payoffs.data(), values, n * sizeof(float), cudaMemcpyDeviceToHost));
#endif
    for (float x : payoffs) {
      uint32_t bits; memcpy(&bits, &x, 4);
      printf("VALUE %u\n", bits);
    }
#endif
    auto done = std::chrono::steady_clock::now();
    fprintf(stderr, "PRICE_NS %lld %lld %lld\n",
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(start.time_since_epoch()).count(),
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(ready.time_since_epoch()).count(),
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(done.time_since_epoch()).count());
  }
#ifdef __CUDACC__
  CUDA(cudaFree(device)); CUDA(cudaFree(result)); CUDA(cudaFree(scratch));
#if AUDIT
  CUDA(cudaFree(values));
#endif
#endif
}
