#include <cuda_runtime.h>
#include <chrono>
#include <cstdio>
__global__ void spin() {
  unsigned long long begin=clock64();
  while(clock64()-begin < 200000000ULL) {}
}
int main() {
  auto begin=std::chrono::steady_clock::now();
  do {
    spin<<<64,64>>>();
    if(cudaDeviceSynchronize()!=cudaSuccess) return 2;
  } while(std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<3.0);
  puts("42");
}
