// Conventional parallel sort over the vendor's identical generated keys.
#include <algorithm>
#include <parallel/algorithm>
#include <vector>
#include <cstdint>
#include <cstdio>
#include <omp.h>

static uint32_t key(uint32_t i) {
  uint32_t x = (i + 1u) * 2654435761u;
  x ^= x << 13; x ^= x >> 17; x ^= x << 5;
  return x;
}

int main() {
  const unsigned n = 1u << (RADIX ? 22 : 23);
  std::vector<uint32_t> a(n);
  double start = omp_get_wtime();
  #pragma omp parallel for schedule(static)
  for (unsigned i = 0; i < n; i++) a[i] = key(i) & (RADIX ? 16777215u : ~0u);
  __gnu_parallel::sort(a.begin(), a.end());
  uint32_t lo = a.front(), hi = a.back(), result;
  if (RADIX) {
    a.erase(std::unique(a.begin(), a.end()), a.end());
    uint32_t sum = 0;
    #pragma omp parallel for reduction(+:sum) schedule(static)
    for (unsigned i = 0; i < a.size(); i++) sum += a[i];
    result = ((sum + uint32_t(a.size()) * 2654435761u) ^ (hi + lo * 340573321u)) + 2246822519u;
  } else {
    std::vector<uint32_t> b(n / 2);
    for (unsigned width = n; width > 1; width /= 2) {
      #pragma omp parallel for schedule(static) if(width > 1024)
      for (unsigned i = 0; i < width / 2; i++) b[i] = a[2*i] * 2654435761u + a[2*i+1];
      a.swap(b);
    }
    result = ((a[0] * 2654435761u) ^ (hi + lo * 340573321u)) + 2246822519u;
  }
  fprintf(stderr, "EVAL_COMPUTE_SECONDS=%.9f\n", omp_get_wtime() - start);
  printf("%u\n", result);
}
